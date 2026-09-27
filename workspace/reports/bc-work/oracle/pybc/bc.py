"""pybc: a GNU bc 1.07.1 replacement in pure Python.

Usage: python3 /app/pybc/bc.py < program
"""

import sys

LINE_LENGTH = 70
DIGITS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"


class Quit(Exception):
    pass


class Halt(Exception):
    pass


class ReturnValue(Exception):
    def __init__(self, value):
        self.value = value


class Break(Exception):
    pass


class Continue(Exception):
    pass


# ------------------------------------------------------------------ numbers

class Num:
    """value = n / 10**s, truncated arithmetic as bc does it."""

    __slots__ = ("n", "s")

    def __init__(self, n=0, s=0):
        self.n, self.s = n, s

    def rescale(self, s):
        if s == self.s:
            return Num(self.n, s)
        if s > self.s:
            return Num(self.n * 10 ** (s - self.s), s)
        d = 10 ** (self.s - s)
        q = abs(self.n) // d
        return Num(q if self.n >= 0 else -q, s)

    def is_zero(self):
        return self.n == 0

    def int_value(self):
        q = abs(self.n) // 10 ** self.s
        return q if self.n >= 0 else -q

    def cmp(self, other):
        s = max(self.s, other.s)
        a, b = self.rescale(s).n, other.rescale(s).n
        return (a > b) - (a < b)


def num_add(a, b):
    s = max(a.s, b.s)
    return Num(a.rescale(s).n + b.rescale(s).n, s)


def num_sub(a, b):
    s = max(a.s, b.s)
    return Num(a.rescale(s).n - b.rescale(s).n, s)


def num_mul(a, b, scale):
    full = Num(a.n * b.n, a.s + b.s)
    return full.rescale(min(a.s + b.s, max(scale, a.s, b.s)))


def num_div(a, b, scale):
    # truncated quotient to `scale` digits
    num = a.n * 10 ** (scale + b.s)
    den = b.n * 10 ** a.s
    q = abs(num) // abs(den)
    if (num < 0) != (den < 0):
        q = -q
    return Num(q, scale)


def num_mod(a, b, scale):
    q = num_div(a, b, scale)
    prod = Num(q.n * b.n, q.s + b.s)
    rs = max(scale + b.s, a.s)
    diff = num_sub(a.rescale(max(a.s, prod.s)), prod)
    return diff.rescale(rs)


def num_pow(a, b, scale):
    e = b.int_value()
    if e == 0:
        return Num(1, 0)
    if e < 0:
        exact = Num(a.n ** -e, a.s * -e)
        return num_div(Num(1, 0), exact, scale)
    rscale = min(a.s * e, max(scale, a.s))
    full = Num(a.n ** e, a.s * e)
    return full.rescale(rscale)


def num_sqrt(a, scale):
    if a.n == 0:
        return Num(0, 0)
    if a.cmp(Num(1, 0)) == 0:
        return Num(1, 0)
    rs = max(scale, a.s)
    # floor(sqrt(a * 10**(2*rs))) with a = n/10**s
    x = a.n * 10 ** (2 * rs - a.s) if 2 * rs >= a.s else a.n // 10 ** (a.s - 2 * rs)
    r = isqrt(x)
    return Num(r, rs)


def isqrt(x):
    if x < 0:
        raise ValueError("square root of negative number")
    if x == 0:
        return 0
    r = 1 << ((x.bit_length() + 1) // 2)
    while True:
        y = (r + x // r) // 2
        if y >= r:
            return r
        r = y


def num_length(a):
    digits = str(abs(a.n))
    if a.n == 0:
        return max(1, a.s) if a.s else 1
    intpart = abs(a.n) // 10 ** a.s
    if intpart == 0:
        return a.s
    return len(digits) if len(digits) > a.s else a.s


def to_string(a, obase):
    if a.n == 0:
        return "0"
    neg = a.n < 0
    n = abs(a.n)
    ip, fp = divmod(n, 10 ** a.s)
    if obase == 10:
        out = str(ip) if ip else ""
        if a.s:
            out += "." + str(fp).rjust(a.s, "0")
    else:
        width = len(str(obase - 1))
        digs = []
        x = ip
        while x:
            x, r = divmod(x, obase)
            digs.append(r)
        digs.reverse()
        if obase <= 16:
            out = "".join(DIGITS[d] for d in digs) if digs else ("" if a.s else "0")
        else:
            out = "".join(" " + str(d).rjust(width, "0") for d in digs) if digs else ("" if a.s else " " + "0" * width)
        if a.s:
            frac = Num(fp, a.s)
            fdigits = []
            # bc produces fraction digits until the precision reaches 10**-scale
            place = 1
            limit = 10 ** a.s
            f = fp
            while place < limit:
                f *= obase
                d, f = divmod(f, 10 ** a.s)
                fdigits.append(d)
                place *= obase
            if obase <= 16:
                out += "." + "".join(DIGITS[d] for d in fdigits)
            else:
                out += "." + "".join(" " + str(d).rjust(width, "0") for d in fdigits)
            del frac
    return ("-" if neg else "") + out


# ------------------------------------------------------------------ lexer

KEYWORDS = {"if", "else", "while", "for", "break", "continue", "define", "return", "auto",
            "quit", "halt", "print", "void", "length", "sqrt", "scale", "ibase", "obase",
            "last", "limits", "warranty", "read"}


class Token:
    __slots__ = ("kind", "value")

    def __init__(self, kind, value):
        self.kind, self.value = kind, value

    def __repr__(self):
        return f"{self.kind}:{self.value!r}"


def lex(src):
    toks = []
    i = 0
    n = len(src)
    ops3 = ()
    ops2 = ("<=", ">=", "==", "!=", "&&", "||", "++", "--", "+=", "-=", "*=", "/=", "%=", "^=")
    while i < n:
        c = src[i]
        if c == "\\" and i + 1 < n and src[i + 1] == "\n":
            i += 2
            continue
        if c in " \t\r":
            i += 1
            continue
        if c == "\n":
            toks.append(Token("nl", "\n"))
            i += 1
            continue
        if c == "#":
            while i < n and src[i] != "\n":
                i += 1
            continue
        if src.startswith("/*", i):
            j = src.find("*/", i + 2)
            i = n if j < 0 else j + 2
            continue
        if c == '"':
            j = src.find('"', i + 1)
            if j < 0:
                j = n
            toks.append(Token("str", src[i + 1:j]))
            i = j + 1
            continue
        if c.isdigit() or c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ" or (c == "." and i + 1 < n and (src[i + 1].isdigit() or src[i + 1] in "ABCDEFGHIJKLMNOPQRSTUVWXYZ")):
            j = i
            while j < n and (src[j].isdigit() or src[j] in "ABCDEFGHIJKLMNOPQRSTUVWXYZ" or (src[j] == "\\" and j + 1 < n and src[j + 1] == "\n")):
                j += 2 if src[j] == "\\" else 1
            if j < n and src[j] == ".":
                j += 1
                while j < n and (src[j].isdigit() or src[j] in "ABCDEFGHIJKLMNOPQRSTUVWXYZ" or (src[j] == "\\" and j + 1 < n and src[j + 1] == "\n")):
                    j += 2 if src[j] == "\\" else 1
            toks.append(Token("num", src[i:j].replace("\\\n", "")))
            i = j
            continue
        if c.islower() or c == "_":
            j = i
            while j < n and (src[j].islower() or src[j].isdigit() or src[j] == "_"):
                j += 1
            word = src[i:j]
            toks.append(Token("kw" if word in KEYWORDS else "name", word))
            i = j
            continue
        if src[i:i + 2] in ops2:
            toks.append(Token("op", src[i:i + 2]))
            i += 2
            continue
        if c == ".":
            toks.append(Token("name", "last"))
            i += 1
            continue
        toks.append(Token("op", c))
        i += 1
    del ops3
    toks.append(Token("eof", None))
    return toks


# ------------------------------------------------------------------ parser
# AST nodes are tuples.

class Parser:
    def __init__(self, toks):
        self.t = toks
        self.i = 0

    def peek(self, k=0):
        return self.t[self.i + k]

    def next(self):
        tok = self.t[self.i]
        self.i += 1
        return tok

    def accept(self, kind, value=None):
        tok = self.peek()
        if tok.kind == kind and (value is None or tok.value == value):
            self.i += 1
            return tok
        return None

    def expect(self, kind, value=None):
        tok = self.accept(kind, value)
        if tok is None:
            raise SyntaxError(f"expected {value or kind}, got {self.peek()}")
        return tok

    def skip_nl(self):
        while self.peek().kind == "nl":
            self.i += 1

    # program: sequence of top-level items; each item is yielded when its line completes
    def statement(self):
        tok = self.peek()
        if tok.kind == "op" and tok.value == "{":
            self.next()
            body = self.statement_list("}")
            self.expect("op", "}")
            return ("block", body)
        if tok.kind == "str":
            self.next()
            return ("string", tok.value)
        if tok.kind == "kw":
            w = tok.value
            if w == "if":
                self.next()
                self.expect("op", "(")
                cond = self.expr()
                self.expect("op", ")")
                self.skip_nl()
                then = self.statement()
                save = self.i
                self.skip_nl_semis()
                if self.accept("kw", "else"):
                    self.skip_nl()
                    other = self.statement()
                    return ("if", cond, then, other)
                self.i = save
                return ("if", cond, then, None)
            if w == "while":
                self.next()
                self.expect("op", "(")
                cond = self.expr()
                self.expect("op", ")")
                self.skip_nl()
                return ("while", cond, self.statement())
            if w == "for":
                self.next()
                self.expect("op", "(")
                e1 = None if self.peek().value == ";" else self.expr()
                self.expect("op", ";")
                e2 = None if self.peek().value == ";" else self.expr()
                self.expect("op", ";")
                e3 = None if self.peek().value == ")" else self.expr()
                self.expect("op", ")")
                self.skip_nl()
                return ("for", e1, e2, e3, self.statement())
            if w == "break":
                self.next()
                return ("break",)
            if w == "continue":
                self.next()
                return ("continue",)
            if w == "halt":
                self.next()
                return ("halt",)
            if w == "quit":
                raise Quit()
            if w == "return":
                self.next()
                if self.peek().kind in ("nl", "eof") or (self.peek().kind == "op" and self.peek().value in (";", "}")):
                    return ("return", None)
                return ("return", self.expr())
            if w == "print":
                self.next()
                items = [self.print_item()]
                while self.accept("op", ","):
                    items.append(self.print_item())
                return ("print", items)
            if w == "define":
                return self.define()
        e = self.expr()
        return ("expr", e)

    def skip_nl_semis(self):
        while self.peek().kind == "nl" or (self.peek().kind == "op" and self.peek().value == ";"):
            self.i += 1

    def print_item(self):
        tok = self.peek()
        if tok.kind == "str":
            self.next()
            return ("pstr", tok.value)
        return ("pexpr", self.expr())

    def statement_list(self, end):
        body = []
        while True:
            while self.peek().kind == "nl" or (self.peek().kind == "op" and self.peek().value == ";"):
                self.i += 1
            if self.peek().kind == "op" and self.peek().value == end:
                return body
            if self.peek().kind == "eof":
                raise SyntaxError("unexpected end")
            body.append(self.statement())

    def define(self):
        self.expect("kw", "define")
        void = bool(self.accept("kw", "void"))
        name = self.expect("name").value
        self.expect("op", "(")
        params = []
        if not self.accept("op", ")"):
            while True:
                byref = bool(self.accept("op", "*"))
                pname = self.expect("name").value
                if self.accept("op", "["):
                    self.expect("op", "]")
                    params.append(("array", pname, byref))
                else:
                    params.append(("var", pname, False))
                if self.accept("op", ")"):
                    break
                self.expect("op", ",")
        self.skip_nl()
        self.expect("op", "{")
        self.skip_nl()
        autos = []
        if self.accept("kw", "auto"):
            while True:
                aname = self.expect("name").value
                if self.accept("op", "["):
                    self.expect("op", "]")
                    autos.append(("array", aname))
                else:
                    autos.append(("var", aname))
                if not self.accept("op", ","):
                    break
            self.accept("op", ";")
        body = self.statement_list("}")
        self.expect("op", "}")
        return ("define", name, void, params, autos, body)

    # expressions, lowest precedence first
    def expr(self):
        return self.or_expr()

    def or_expr(self):
        left = self.and_expr()
        while self.accept("op", "||"):
            left = ("or", left, self.and_expr())
        return left

    def and_expr(self):
        left = self.not_expr()
        while self.accept("op", "&&"):
            left = ("and", left, self.not_expr())
        return left

    def not_expr(self):
        if self.accept("op", "!"):
            return ("not", self.not_expr())
        return self.rel_expr()

    def rel_expr(self):
        left = self.assign_expr()
        while self.peek().kind == "op" and self.peek().value in ("<", "<=", ">", ">=", "==", "!="):
            op = self.next().value
            left = ("rel", op, left, self.assign_expr())
        return left

    def assign_expr(self):
        start = self.i
        target = self.lvalue_try()
        if target is not None:
            tok = self.peek()
            if tok.kind == "op" and tok.value in ("=", "+=", "-=", "*=", "/=", "%=", "^="):
                self.next()
                value = self.assign_expr()
                return ("assign", tok.value, target, value)
        self.i = start
        return self.add_expr()

    def lvalue_try(self):
        tok = self.peek()
        if tok.kind == "name":
            self.next()
            if self.accept("op", "["):
                idx = self.expr()
                self.expect("op", "]")
                return ("elem", tok.value, idx)
            if self.peek().kind == "op" and self.peek().value == "(":
                return None
            return ("var", tok.value)
        if tok.kind == "kw" and tok.value in ("scale", "ibase", "obase", "last"):
            if self.peek(1).kind == "op" and self.peek(1).value == "(":
                return None
            self.next()
            return ("var", tok.value)
        return None

    def add_expr(self):
        left = self.mul_expr()
        while self.peek().kind == "op" and self.peek().value in ("+", "-"):
            op = self.next().value
            left = ("bin", op, left, self.mul_expr())
        return left

    def mul_expr(self):
        left = self.pow_expr()
        while self.peek().kind == "op" and self.peek().value in ("*", "/", "%"):
            op = self.next().value
            left = ("bin", op, left, self.pow_expr())
        return left

    def pow_expr(self):
        base = self.unary()
        if self.accept("op", "^"):
            return ("bin", "^", base, self.pow_expr())
        return base

    def unary(self):
        if self.accept("op", "-"):
            return ("neg", self.unary())
        return self.incdec()

    def incdec(self):
        if self.peek().kind == "op" and self.peek().value in ("++", "--"):
            op = self.next().value
            target = self.lvalue_try()
            return ("pre", op, target)
        prim = self.primary()
        if prim[0] in ("var", "elem") and self.peek().kind == "op" and self.peek().value in ("++", "--"):
            op = self.next().value
            return ("post", op, prim)
        return prim

    def primary(self):
        tok = self.next()
        if tok.kind == "num":
            return ("num", tok.value)
        if tok.kind == "op" and tok.value == "(":
            e = self.expr()
            self.expect("op", ")")
            return e
        if tok.kind == "kw" and tok.value in ("length", "sqrt", "scale") and self.peek().value == "(":
            self.expect("op", "(")
            e = self.expr()
            self.expect("op", ")")
            return ("func1", tok.value, e)
        if tok.kind == "kw" and tok.value in ("scale", "ibase", "obase", "last"):
            return ("var", tok.value)
        if tok.kind == "name":
            if self.accept("op", "("):
                args = []
                if not self.accept("op", ")"):
                    while True:
                        if self.peek().kind == "name" and self.peek(1).kind == "op" and self.peek(1).value == "[" and self.peek(2).kind == "op" and self.peek(2).value == "]":
                            nm = self.next().value
                            self.next()
                            self.next()
                            args.append(("arrayarg", nm))
                        else:
                            args.append(self.expr())
                        if self.accept("op", ")"):
                            break
                        self.expect("op", ",")
                return ("call", tok.value, args)
            if self.accept("op", "["):
                idx = self.expr()
                self.expect("op", "]")
                return ("elem", tok.value, idx)
            return ("var", tok.value)
        raise SyntaxError(f"unexpected {tok}")


# ------------------------------------------------------------------ interpreter

class Interp:
    def __init__(self, out):
        self.out = out
        self.col = 0
        self.vars = {}      # name -> stack of Num
        self.arrays = {}    # name -> stack of dict
        self.funcs = {}
        self.scale = 0
        self.ibase = 10
        self.obase = 10
        self.last = Num(0, 0)
        self.call_ibase = []

    # output: bc tracks the output column across everything on a line and splits
    # numbers with a backslash-newline once 68 characters are on the line
    def write(self, text):
        self.out.append(text)
        nl = text.rfind("\n")
        self.col = len(text) - nl - 1 if nl >= 0 else self.col + len(text)

    def print_num(self, value):
        s = to_string(value, self.obase)
        pieces = []
        for ch in s:
            if self.col >= LINE_LENGTH - 2:
                pieces.append("\\\n")
                self.col = 0
            pieces.append(ch)
            self.col += 1
        self.out.append("".join(pieces))

    # variables
    def get(self, name):
        if name == "scale":
            return Num(self.scale, 0)
        if name == "ibase":
            return Num(self.ibase, 0)
        if name == "obase":
            return Num(self.obase, 0)
        if name == "last":
            return self.last
        st = self.vars.get(name)
        return st[-1] if st else Num(0, 0)

    def set(self, name, value):
        if name == "scale":
            v = value.int_value()
            self.scale = max(0, v)
            return
        if name == "ibase":
            v = value.int_value()
            self.ibase = 2 if v < 2 else 36 if v > 36 else v
            return
        if name == "obase":
            v = value.int_value()
            self.obase = 2 if v < 2 else v
            return
        if name == "last":
            self.last = value
            return
        st = self.vars.setdefault(name, [Num(0, 0)])
        st[-1] = value

    def array(self, name):
        st = self.arrays.setdefault(name, [{}])
        return st[-1]

    def convert(self, text):
        base = self.call_ibase[-1] if self.call_ibase else self.ibase
        if "." in text:
            ip, fp = text.split(".", 1)
        else:
            ip, fp = text, ""
        if len(text) == 1:
            return Num(DIGITS.index(text), 0)
        val = 0
        for ch in ip:
            d = DIGITS.index(ch)
            if d >= base:
                d = base - 1
            val = val * base + d
        if not fp:
            return Num(val, 0)
        scale = len(fp)
        # fraction: sum d_i / base**i, truncated to `scale` decimal digits
        num = 0
        den = 1
        for ch in fp:
            d = DIGITS.index(ch)
            if d >= base:
                d = base - 1
            num = num * base + d
            den *= base
        frac = (num * 10 ** scale) // den
        return Num(val * 10 ** scale + frac, scale)

    # evaluation
    def ev(self, e):
        k = e[0]
        if k == "num":
            return self.convert(e[1])
        if k == "var":
            return self.get(e[1])
        if k == "elem":
            idx = self.ev(e[2]).int_value()
            return self.array(e[1]).get(idx, Num(0, 0))
        if k == "neg":
            v = self.ev(e[1])
            return Num(-v.n, v.s)
        if k == "bin":
            a = self.ev(e[2])
            b = self.ev(e[3])
            return self.binop(e[1], a, b)
        if k == "rel":
            a = self.ev(e[2])
            b = self.ev(e[3])
            c = a.cmp(b)
            r = {"<": c < 0, "<=": c <= 0, ">": c > 0, ">=": c >= 0, "==": c == 0, "!=": c != 0}[e[1]]
            return Num(1 if r else 0, 0)
        if k == "not":
            return Num(1 if self.ev(e[1]).is_zero() else 0, 0)
        if k == "and":
            if self.ev(e[1]).is_zero():
                return Num(0, 0)
            return Num(0 if self.ev(e[2]).is_zero() else 1, 0)
        if k == "or":
            if not self.ev(e[1]).is_zero():
                return Num(1, 0)
            return Num(0 if self.ev(e[2]).is_zero() else 1, 0)
        if k == "assign":
            op, target, value = e[1], e[2], e[3]
            if target[0] == "elem":
                idx = self.ev(target[2]).int_value()
                cur = self.array(target[1]).get(idx, Num(0, 0))
                v = self.ev(value)
                new = v if op == "=" else self.binop(op[0], cur, v)
                self.array(target[1])[idx] = new
                return new
            v = self.ev(value)
            new = v if op == "=" else self.binop(op[0], self.get(target[1]), v)
            self.set(target[1], new)
            return self.get(target[1]) if target[1] in ("scale", "ibase", "obase") else new
        if k in ("pre", "post"):
            target = e[2]
            one = Num(1, 0)
            if target[0] == "elem":
                idx = self.ev(target[2]).int_value()
                arr = self.array(target[1])
                cur = arr.get(idx, Num(0, 0))
                new = num_add(cur, one) if e[1] == "++" else num_sub(cur, one)
                arr[idx] = new
            else:
                cur = self.get(target[1])
                new = num_add(cur, one) if e[1] == "++" else num_sub(cur, one)
                self.set(target[1], new)
            return new if k == "pre" else cur
        if k == "func1":
            v = self.ev(e[2])
            if e[1] == "length":
                return Num(num_length(v), 0)
            if e[1] == "scale":
                return Num(v.s, 0)
            return num_sqrt(v, self.scale)
        if k == "call":
            return self.call(e[1], e[2])
        raise AssertionError(k)

    def binop(self, op, a, b):
        if op == "+":
            return num_add(a, b)
        if op == "-":
            return num_sub(a, b)
        if op == "*":
            return num_mul(a, b, self.scale)
        if op == "/":
            return num_div(a, b, self.scale)
        if op == "%":
            return num_mod(a, b, self.scale)
        if op == "^":
            return num_pow(a, b, self.scale)
        raise AssertionError(op)

    def call(self, name, args):
        f = self.funcs[name]
        _name, void, params, autos, body = f
        values = []
        for (kind, pname, byref), arg in zip(params, args):
            if kind == "array":
                src = self.array(arg[1])
                values.append(("array", pname, src if byref else dict(src)))
            else:
                values.append(("var", pname, self.ev(arg)))
        pushed = []
        for kind, pname, val in values:
            if kind == "array":
                self.arrays.setdefault(pname, [{}]).append(val)
                pushed.append(("array", pname))
            else:
                self.vars.setdefault(pname, [Num(0, 0)]).append(val)
                pushed.append(("var", pname))
        for kind, aname in autos:
            if kind == "array":
                self.arrays.setdefault(aname, [{}]).append({})
            else:
                self.vars.setdefault(aname, [Num(0, 0)]).append(Num(0, 0))
            pushed.append((kind, aname))
        self.call_ibase.append(self.ibase)
        result = Num(0, 0)
        try:
            self.run_list(body)
        except ReturnValue as r:
            result = r.value
        finally:
            self.call_ibase.pop()
            for kind, pname in reversed(pushed):
                (self.arrays if kind == "array" else self.vars)[pname].pop()
        return None if void else result

    def run_list(self, stmts):
        for s in stmts:
            self.run(s)

    def run(self, s):
        k = s[0]
        if k == "expr":
            e = s[1]
            if e[0] == "assign":
                self.ev(e)
                return
            v = self.ev(e)
            if v is None:
                return
            self.print_num(v)
            self.write("\n")
            self.last = v
        elif k == "string":
            self.write(s[1])
        elif k == "print":
            for kind, item in s[1]:
                if kind == "pstr":
                    self.write(print_escapes(item))
                else:
                    v = self.ev(item)
                    self.print_num(v)
                    self.last = v
        elif k == "block":
            self.run_list(s[1])
        elif k == "if":
            if not self.ev(s[1]).is_zero():
                self.run(s[2])
            elif s[3] is not None:
                self.run(s[3])
        elif k == "while":
            while not self.ev(s[1]).is_zero():
                try:
                    self.run(s[2])
                except Break:
                    break
                except Continue:
                    continue
        elif k == "for":
            _, e1, e2, e3, body = s
            if e1 is not None:
                self.ev(e1)
            while e2 is None or not self.ev(e2).is_zero():
                try:
                    self.run(body)
                except Break:
                    break
                except Continue:
                    pass
                if e3 is not None:
                    self.ev(e3)
        elif k == "break":
            raise Break()
        elif k == "continue":
            raise Continue()
        elif k == "halt":
            raise Halt()
        elif k == "return":
            raise ReturnValue(Num(0, 0) if s[1] is None else self.ev(s[1]))
        elif k == "define":
            _, name, void, params, autos, body = s
            self.funcs[name] = (name, void, params, autos, body)
        else:
            raise AssertionError(k)


def print_escapes(text):
    table = {"a": "\a", "b": "\b", "f": "\f", "n": "\n", "r": "\r", "q": '"', "t": "\t", "\\": "\\", "e": "\\"}
    out = []
    i = 0
    while i < len(text):
        c = text[i]
        if c == "\\" and i + 1 < len(text):
            out.append(table.get(text[i + 1], ""))
            i += 2
        else:
            out.append(c)
            i += 1
    return "".join(out)


def main():
    src = sys.stdin.buffer.read().decode("latin-1")
    out = []
    interp = Interp(out)
    toks = lex(src)
    # execute statement by statement, each complete line as soon as it is read
    p = Parser(toks)
    code = 0
    try:
        while True:
            p.skip_nl_semis()
            if p.peek().kind == "eof":
                break
            # parse every statement up to the end of this input line before running any
            line = []
            while True:
                line.append(p.statement())
                while p.peek().kind == "op" and p.peek().value == ";":
                    p.next()
                if p.peek().kind in ("nl", "eof"):
                    break
            for stmt in line:
                interp.run(stmt)
    except Quit:
        pass
    except Halt:
        pass
    sys.stdout.buffer.write("".join(out).encode("latin-1"))
    return code


if __name__ == "__main__":
    sys.exit(main())
