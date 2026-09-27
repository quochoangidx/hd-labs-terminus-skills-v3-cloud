"""pybc: a GNU bc 1.07.1 replacement in pure Python.

Usage: python3 /app/pybc/bc.py < program
"""

import sys
import threading

if hasattr(sys, "set_int_max_str_digits"):
    sys.set_int_max_str_digits(0)

INT_MAX = 2147483647
LONG_MAX = 9223372036854775807
DIM_MAX = 16777215
LINE_SIZE = 70


# ---------------------------------------------------------------------------
# Numbers: value = v / 10**s, v a signed Python int, s the bc scale.
# ---------------------------------------------------------------------------

class Num(object):
    __slots__ = ("v", "s")

    def __init__(self, v, s):
        self.v = v
        self.s = s


ZERO = Num(0, 0)
ONE = Num(1, 0)
POINT5 = Num(5, 1)

_P10 = [10 ** i for i in range(512)]


def p10(n):
    if n < 512:
        return _P10[n]
    return 10 ** n


class BcError(Exception):
    pass


class QuitExc(Exception):
    pass


class HaltExc(Exception):
    pass


def trunc(v, d):
    """Drop d decimal digits from v, truncating toward zero."""
    if d <= 0:
        return v
    if v >= 0:
        return v // p10(d)
    return -((-v) // p10(d))


def add(a, b):
    if a.s == b.s:
        return Num(a.v + b.v, a.s)
    if a.s > b.s:
        return Num(a.v + b.v * p10(a.s - b.s), a.s)
    return Num(a.v * p10(b.s - a.s) + b.v, b.s)


def sub(a, b):
    if a.s == b.s:
        return Num(a.v - b.v, a.s)
    if a.s > b.s:
        return Num(a.v - b.v * p10(a.s - b.s), a.s)
    return Num(a.v * p10(b.s - a.s) - b.v, b.s)


def cmp(a, b):
    if a.s == b.s:
        x, y = a.v, b.v
    elif a.s > b.s:
        x, y = a.v, b.v * p10(a.s - b.s)
    else:
        x, y = a.v * p10(b.s - a.s), b.v
    return (x > y) - (x < y)


def mul(a, b, scale):
    full = a.s + b.s
    ps = max(scale, a.s, b.s)
    if ps > full:
        ps = full
    return Num(trunc(a.v * b.v, full - ps), ps)


def div(a, b, scale):
    if b.v == 0:
        raise BcError("Divide by zero")
    e = scale + b.s - a.s
    av = a.v if a.v >= 0 else -a.v
    bv = b.v if b.v >= 0 else -b.v
    if e >= 0:
        q = (av * p10(e)) // bv
    else:
        q = av // (bv * p10(-e))
    if (a.v < 0) != (b.v < 0):
        q = -q
    return Num(q, scale)


def mod(a, b, scale):
    if b.v == 0:
        raise BcError("Modulo by zero")
    q = div(a, b, scale)
    rs = max(a.s, b.s + scale)
    p = mul(q, b, rs)
    r = sub(a, p)
    if r.s < rs:
        r = Num(r.v * p10(rs - r.s), rs)
    return r


def int_part(x):
    """Signed integer part (truncated toward zero)."""
    return trunc(x.v, x.s)


def num2long(x):
    ip = int_part(x)
    if ip > LONG_MAX or ip < -LONG_MAX:
        return 0
    return ip


def power(a, b, scale):
    if b.s != 0:
        sys.stderr.write("Runtime warning: non-zero scale in exponent\n")
    e = num2long(b)
    if e == 0:
        if int_part(b) != 0:
            raise BcError("exponent too large in raise")
        return ONE
    if e < 0:
        neg = True
        e = -e
        rscale = scale
    else:
        neg = False
        rscale = min(a.s * e, max(scale, a.s))
    v = a.v ** e
    s = a.s * e
    if neg:
        return div(ONE, Num(v, s), rscale)
    if s > rscale:
        return Num(trunc(v, s - rscale), rscale)
    return Num(v, s)


def n_len(x):
    a = x.v if x.v >= 0 else -x.v
    ip = a // p10(x.s) if x.s else a
    if ip == 0:
        return 1
    return len(str(ip))


def is_near_zero(x, scale):
    if scale > x.s:
        scale = x.s
    a = x.v if x.v >= 0 else -x.v
    m = a // p10(x.s - scale)
    return m <= 1


def bsqrt(x, scale):
    c = cmp(x, ZERO)
    if c < 0:
        raise BcError("Square root of a negative number")
    if c == 0:
        return ZERO
    c1 = cmp(x, ONE)
    if c1 == 0:
        return ONE
    rscale = max(scale, x.s)
    if c1 < 0:
        guess = ONE
        cscale = x.s
    else:
        e = n_len(x) // 2
        guess = Num(p10(e), 0)
        cscale = 3
    while True:
        guess1 = guess
        guess = div(x, guess, cscale)
        guess = add(guess, guess1)
        guess = mul(guess, POINT5, cscale)
        diff = sub(guess, guess1)
        if is_near_zero(diff, cscale):
            if cscale < rscale + 1:
                cscale = min(cscale * 3, rscale + 1)
            else:
                break
    return div(guess, ONE, rscale)


def blength(x):
    a = x.v if x.v >= 0 else -x.v
    ip = a // p10(x.s) if x.s else a
    if ip == 0 and x.s != 0:
        return x.s
    return n_len(x) + x.s


# ---------------------------------------------------------------------------
# Interpreter state and output
# ---------------------------------------------------------------------------

class State(object):
    pass


S = State()
S.scale = 0
S.ibase = 10
S.obase = 10
S.last = ZERO

VARS = {}
ARRS = {}
FUNCS = {}

OUT = []
_col = [0]


def flush_out():
    if OUT:
        data = "".join(OUT)
        del OUT[:]
        sys.stdout.buffer.write(data.encode("latin-1", "replace"))
        sys.stdout.buffer.flush()


def emit(t):
    col = _col[0]
    first = True
    for seg in t.split("\n"):
        if not first:
            OUT.append("\n")
            col = 0
        first = False
        i = 0
        n = len(seg)
        while i < n:
            room = 68 - col
            if room <= 0:
                OUT.append("\\\n")
                col = 0
                room = 68
            j = i + room
            if j > n:
                j = n
            OUT.append(seg[i:j])
            col += j - i
            i = j
    _col[0] = col
    if len(OUT) > 4096:
        flush_out()


HEXD = "0123456789ABCDEF"


def to_base(n, b):
    """Digits (most significant first) of n > 0 in base b."""
    if n < b:
        return [n]
    pows = [b]
    while pows[-1] * pows[-1] <= n:
        pows.append(pows[-1] * pows[-1])

    def rec(m, i):
        if i == 0:
            q, r = divmod(m, b)
            return [q, r]
        hi, lo = divmod(m, pows[i])
        return rec(hi, i - 1) + rec(lo, i - 1)

    k = len(pows) - 1
    ds = rec(n, k)
    z = 0
    while z < len(ds) - 1 and ds[z] == 0:
        z += 1
    return ds[z:]


def fmt(x):
    v = x.v
    if v == 0:
        return "0"
    sign = "-" if v < 0 else ""
    a = -v if v < 0 else v
    s = x.s
    b = S.obase
    if b == 10:
        ds = str(a)
        if s == 0:
            return sign + ds
        if len(ds) <= s:
            return sign + "." + ds.rjust(s, "0")
        return sign + ds[:-s] + "." + ds[-s:]
    sc = p10(s)
    ip, fp = divmod(a, sc)
    out = [sign]
    w = len(str(b - 1))
    if ip:
        if b == 16:
            out.append(format(ip, "X"))
        elif b == 8:
            out.append(format(ip, "o"))
        elif b == 2:
            out.append(format(ip, "b"))
        else:
            digs = to_base(ip, b)
            if b <= 16:
                out.append("".join([HEXD[d] for d in digs]))
            else:
                out.append("".join([" " + str(d).zfill(w) for d in digs]))
    if s > 0:
        out.append(".")
        t = 1
        first = True
        while t < sc:
            fp *= b
            d, fp = divmod(fp, sc)
            if b <= 16:
                out.append(HEXD[d])
            else:
                out.append(("" if first else " ") + str(d).zfill(w))
                first = False
            t *= b
    return "".join(out)


def print_num(x, newline):
    emit(fmt(x) + ("\n" if newline else ""))
    S.last = x


def set_scale(v):
    if v.v < 0:
        S.scale = 0
        return
    ip = int_part(v)
    S.scale = INT_MAX if ip > INT_MAX else ip


def set_ibase(v):
    if v.v < 0:
        S.ibase = 2
        return
    ip = int_part(v)
    if ip < 2:
        S.ibase = 2
    elif ip > 36:
        S.ibase = 36
    else:
        S.ibase = ip


def set_obase(v):
    if v.v < 0:
        S.obase = 2
        return
    ip = int_part(v)
    if ip < 2:
        S.obase = 2
    elif ip > INT_MAX:
        S.obase = INT_MAX
    else:
        S.obase = ip


def digit_val(c):
    if c <= "9":
        return ord(c) - 48
    return ord(c) - 55


def convert_const(ipart, fpart, base):
    build = 0
    if ipart:
        ds = [digit_val(c) for c in ipart]
        if len(ds) == 1:
            build = ds[0]
        else:
            bm = base - 1
            for d in ds:
                if d > bm:
                    d = bm
                build = build * base + d
    if fpart:
        bm = base - 1
        r = 0
        for c in fpart:
            d = digit_val(c)
            if d > bm:
                d = bm
            r = r * base + d
        fs = len(fpart)
        frac = (r * p10(fs)) // (base ** fs)
        return Num(build * p10(fs) + frac, fs)
    return Num(build, 0)


# ---------------------------------------------------------------------------
# Lexer
# ---------------------------------------------------------------------------

KEYWORDS = {
    "auto", "break", "continue", "define", "else", "for", "halt", "ibase",
    "if", "last", "length", "limits", "obase", "print", "quit", "read",
    "return", "scale", "sqrt", "warranty", "while", "void",
}

TWO_OPS = {
    "++": "INCDEC", "--": "INCDEC",
    "+=": "ASSIGN", "-=": "ASSIGN", "*=": "ASSIGN", "/=": "ASSIGN",
    "%=": "ASSIGN", "^=": "ASSIGN",
    "==": "REL", "<=": "REL", ">=": "REL", "!=": "REL",
    "&&": "&&", "||": "||",
}

ONE_OPS = {
    "+": "+", "-": "-", "*": "*", "/": "/", "%": "%", "^": "^",
    "<": "REL", ">": "REL", "=": "ASSIGN", "!": "!",
    "(": "(", ")": ")", "[": "[", "]": "]", "{": "{", "}": "}",
    ",": ",", ";": ";",
}


def is_digit_char(c):
    return ("0" <= c <= "9") or ("A" <= c <= "Z")


def lex(src):
    toks = []
    i = 0
    n = len(src)
    ap = toks.append
    while i < n:
        c = src[i]
        if c == " " or c == "\t":
            i += 1
            continue
        if c == "\n":
            ap(("NL", None))
            i += 1
            continue
        if c == "\\":
            if i + 1 < n and src[i + 1] == "\n":
                i += 2
                continue
            ap(("ERR", "illegal character: \\"))
            i += 1
            continue
        if c == "#":
            j = src.find("\n", i)
            i = n if j < 0 else j
            continue
        if c == "/" and i + 1 < n and src[i + 1] == "*":
            j = src.find("*/", i + 2)
            if j < 0:
                ap(("ERR", "unterminated comment"))
                i = n
            else:
                i = j + 2
            continue
        if c == '"':
            j = src.find('"', i + 1)
            if j < 0:
                ap(("ERR", "unterminated string"))
                i = n
            else:
                ap(("STR", src[i + 1:j]))
                i = j + 1
            continue
        if is_digit_char(c) or (c == "." and i + 1 < n and is_digit_char(src[i + 1])):
            buf = []
            j = i
            while j < n:
                ch = src[j]
                if is_digit_char(ch):
                    buf.append(ch)
                    j += 1
                elif ch == "\\" and j + 1 < n and src[j + 1] == "\n":
                    j += 2
                else:
                    break
            if j < n and src[j] == ".":
                buf.append(".")
                j += 1
                while j < n:
                    ch = src[j]
                    if is_digit_char(ch):
                        buf.append(ch)
                        j += 1
                    elif ch == "\\" and j + 1 < n and src[j + 1] == "\n":
                        j += 2
                    else:
                        break
            text = "".join(buf)
            if text.endswith("."):
                text = text[:-1]
            k = 0
            while k < len(text) and text[k] == "0":
                k += 1
            if k == len(text):
                k -= 1
            text = text[k:]
            if "." in text:
                ip, fp = text.split(".", 1)
            else:
                ip, fp = text, ""
            ap(("NUM", (ip, fp)))
            i = j
            continue
        if "a" <= c <= "z":
            j = i + 1
            while j < n and (("a" <= src[j] <= "z") or ("0" <= src[j] <= "9") or src[j] == "_"):
                j += 1
            w = src[i:j]
            if w in KEYWORDS:
                ap((w, w))
            else:
                ap(("NAME", w))
            i = j
            continue
        if c == ".":
            ap(("last", "last"))
            i += 1
            continue
        two = src[i:i + 2]
        if two in TWO_OPS:
            ap((TWO_OPS[two], two))
            i += 2
            continue
        if c in ONE_OPS:
            ap((ONE_OPS[c], c))
            i += 1
            continue
        ap(("ERR", "illegal character: %r" % c))
        i += 1
    ap(("EOF", None))
    return toks


# ---------------------------------------------------------------------------
# Parser / compiler to closures
# ---------------------------------------------------------------------------

class ParseError(Exception):
    pass


BREAK = object()
CONTINUE = object()


class Ret(object):
    __slots__ = ("v",)

    def __init__(self, v):
        self.v = v


class Func(object):
    __slots__ = ("name", "params", "autos", "body", "void")


BINOPS = {
    "||": 1, "&&": 2, "REL": 4, "+": 6, "-": 6,
    "*": 7, "/": 7, "%": 7, "^": 8,
}


def run_list(stmts):
    for s in stmts:
        r = s()
        if r is not None:
            return r
    return None


def array_index(x, name):
    i = num2long(x)
    if i < 0 or i > DIM_MAX:
        raise BcError("Array %s subscript out of bounds." % name)
    return i


class LValue(object):
    """locate() -> loc ; load(loc) ; store(loc, v) ; plain getter."""
    __slots__ = ("locate", "load", "store", "get")


def lv_var(name):
    st = VARS.setdefault(name, [ZERO])
    lv = LValue()

    def locate():
        return None

    def load(loc):
        return st[-1]

    def store(loc, v):
        st[-1] = v

    def get():
        return st[-1]
    lv.locate, lv.load, lv.store, lv.get = locate, load, store, get
    return lv


def lv_arr(name, idxfn):
    st = ARRS.setdefault(name, [{}])
    lv = LValue()

    def locate():
        i = array_index(idxfn(), name)
        return (st[-1], i)

    def load(loc):
        return loc[0].get(loc[1], ZERO)

    def store(loc, v):
        loc[0][loc[1]] = v

    def get():
        i = array_index(idxfn(), name)
        return st[-1].get(i, ZERO)
    lv.locate, lv.load, lv.store, lv.get = locate, load, store, get
    return lv


def lv_special(which):
    lv = LValue()

    def locate():
        return None
    if which == "scale":
        def get():
            return Num(S.scale, 0)
        setter = set_scale
    elif which == "ibase":
        def get():
            return Num(S.ibase, 0)
        setter = set_ibase
    elif which == "obase":
        def get():
            return Num(S.obase, 0)
        setter = set_obase
    else:
        def get():
            return S.last

        def setter(v):
            S.last = v

    def load(loc):
        return get()

    def store(loc, v):
        setter(v)
    lv.locate, lv.load, lv.store, lv.get = locate, load, store, get
    return lv


def arith(op):
    if op == "+":
        return lambda a, b: add(a, b)
    if op == "-":
        return lambda a, b: sub(a, b)
    if op == "*":
        return lambda a, b: mul(a, b, S.scale)
    if op == "/":
        return lambda a, b: div(a, b, S.scale)
    if op == "%":
        return lambda a, b: mod(a, b, S.scale)
    if op == "^":
        return lambda a, b: power(a, b, S.scale)
    raise ValueError(op)


LIMITS_TEXT = (
    "BC_BASE_MAX     = 2147483647\n"
    "BC_DIM_MAX      = 16777215\n"
    "BC_SCALE_MAX    = 2147483647\n"
    "BC_STRING_MAX   = 2147483647\n"
    "MAX Exponent    = 9223372036854775807\n"
    "Number of vars  = 32767\n"
)


def process_escapes(s):
    out = []
    i = 0
    n = len(s)
    while i < n:
        c = s[i]
        if c != "\\":
            out.append(c)
            i += 1
            continue
        i += 1
        if i >= n:
            break
        c = s[i]
        i += 1
        if c == "a":
            out.append("\x07")
        elif c == "b":
            out.append("\b")
        elif c == "f":
            out.append("\f")
        elif c == "n":
            out.append("\n")
        elif c == "q":
            out.append('"')
        elif c == "r":
            out.append("\r")
        elif c == "t":
            out.append("\t")
        elif c == "\\":
            out.append("\\")
    return "".join(out)


class Parser(object):
    def __init__(self, toks):
        self.toks = toks
        self.pos = 0
        self.had_error = False
        self.in_func = False
        self.void = False
        self.loop = 0

    # token helpers ---------------------------------------------------------
    def peek(self):
        t = self.toks[self.pos]
        while t[0] == "ERR":
            sys.stderr.write("(standard_in): %s\n" % t[1])
            self.had_error = True
            self.pos += 1
            t = self.toks[self.pos]
        return t

    def peek2(self):
        self.peek()
        p = self.pos + 1
        while self.toks[p][0] == "ERR":
            p += 1
        return self.toks[p]

    def next(self):
        t = self.peek()
        if t[0] != "EOF":
            self.pos += 1
        return t

    def expect(self, typ):
        t = self.next()
        if t[0] != typ:
            raise ParseError("syntax error: expected %s" % typ)
        return t

    def skip_nl(self):
        while self.peek()[0] == "NL":
            self.next()

    # top level -------------------------------------------------------------
    def run(self):
        while True:
            t = self.peek()
            if t[0] == "EOF":
                return
            self.had_error = False
            try:
                if t[0] == "define":
                    self.parse_define()
                    continue
                stmts = []
                while True:
                    t = self.peek()
                    if t[0] == "NL":
                        self.next()
                        break
                    if t[0] == "EOF":
                        break
                    if t[0] == ";":
                        self.next()
                        continue
                    stmts.append(self.statement())
                    t = self.peek()
                    if t[0] not in (";", "NL", "EOF"):
                        raise ParseError("syntax error")
            except ParseError as e:
                sys.stderr.write("(standard_in): %s\n" % e)
                self.in_func = False
                self.void = False
                self.loop = 0
                # skip to end of line
                while True:
                    t = self.next()
                    if t[0] in ("NL", "EOF"):
                        break
                continue
            if self.had_error:
                continue
            execute(stmts)

    # functions -------------------------------------------------------------
    def define_list(self):
        items = []
        while True:
            t = self.next()
            if t[0] == "*":
                name = self.expect("NAME")[1]
                self.expect("[")
                self.expect("]")
                items.append(("r", name))
            elif t[0] == "NAME":
                if self.peek()[0] == "[":
                    self.next()
                    self.expect("]")
                    items.append(("a", t[1]))
                else:
                    items.append(("v", t[1]))
            else:
                raise ParseError("syntax error in parameter list")
            if self.peek()[0] == ",":
                self.next()
                continue
            return items

    def parse_define(self):
        self.next()
        void = False
        if self.peek()[0] == "void":
            self.next()
            void = True
        name = self.expect("NAME")[1]
        self.expect("(")
        params = []
        if self.peek()[0] != ")":
            params = self.define_list()
        self.expect(")")
        self.skip_nl()
        self.expect("{")
        self.skip_nl()
        autos = []
        if self.peek()[0] == "auto":
            self.next()
            autos = self.define_list()
            t = self.next()
            if t[0] not in (";", "NL"):
                raise ParseError("syntax error after auto list")
        self.in_func = True
        self.void = void
        self.loop = 0
        try:
            body = self.stmt_list()
        finally:
            self.in_func = False
            self.void = False
        if self.had_error:
            FUNCS.pop(name, None)
            return
        f = Func()
        f.name = name
        f.void = void
        f.params = []
        for kind, pname in params:
            if kind == "v":
                f.params.append((kind, VARS.setdefault(pname, [ZERO])))
            else:
                f.params.append((kind, ARRS.setdefault(pname, [{}])))
        f.autos = []
        for kind, aname in autos:
            if kind == "v":
                f.autos.append(("v", VARS.setdefault(aname, [ZERO])))
            else:
                f.autos.append(("a", ARRS.setdefault(aname, [{}])))
        f.body = body
        FUNCS[name] = f

    # statements ------------------------------------------------------------
    def stmt_list(self):
        """Parse statements up to and including the closing brace."""
        stmts = []
        while True:
            t = self.peek()
            if t[0] in (";", "NL"):
                self.next()
                continue
            if t[0] == "}":
                self.next()
                return stmts
            if t[0] == "EOF":
                raise ParseError("syntax error: unexpected end of file")
            stmts.append(self.statement())
            t = self.peek()
            if t[0] not in (";", "NL", "}"):
                raise ParseError("syntax error")

    def statement(self):
        t = self.peek()
        k = t[0]
        if k == "{":
            self.next()
            stmts = self.stmt_list()

            def block():
                for s in stmts:
                    r = s()
                    if r is not None:
                        return r
                return None
            return block
        if k == "if":
            self.next()
            self.expect("(")
            cond = self.expr(0)[0]
            self.expect(")")
            self.skip_nl()
            s1 = self.statement()
            s2 = None
            if self.peek()[0] == "else":
                self.next()
                self.skip_nl()
                s2 = self.statement()
            if s2 is None:
                def if_():
                    if cond().v != 0:
                        return s1()
                    return None
            else:
                def if_():
                    if cond().v != 0:
                        return s1()
                    return s2()
            return if_
        if k == "while":
            self.next()
            self.expect("(")
            cond = self.expr(0)[0]
            self.expect(")")
            self.skip_nl()
            self.loop += 1
            try:
                body = self.statement()
            finally:
                self.loop -= 1

            def while_():
                while cond().v != 0:
                    r = body()
                    if r is not None:
                        if r is BREAK:
                            break
                        if r is CONTINUE:
                            continue
                        return r
                return None
            return while_
        if k == "for":
            self.next()
            self.expect("(")
            init = cond = inc = None
            if self.peek()[0] != ";":
                init = self.expr(0)[0]
            self.expect(";")
            if self.peek()[0] != ";":
                cond = self.expr(0)[0]
            self.expect(";")
            if self.peek()[0] != ")":
                inc = self.expr(0)[0]
            self.expect(")")
            self.skip_nl()
            self.loop += 1
            try:
                body = self.statement()
            finally:
                self.loop -= 1

            def for_():
                if init is not None:
                    init()
                while True:
                    if cond is not None and cond().v == 0:
                        break
                    r = body()
                    if r is not None:
                        if r is BREAK:
                            break
                        if r is not CONTINUE:
                            return r
                    if inc is not None:
                        inc()
                return None
            return for_
        if k == "print":
            self.next()
            items = []
            while True:
                if self.peek()[0] == "STR":
                    items.append((True, process_escapes(self.next()[1])))
                else:
                    items.append((False, self.expr(0)[0]))
                if self.peek()[0] == ",":
                    self.next()
                    continue
                break

            def print_():
                for is_str, x in items:
                    if is_str:
                        emit(x)
                    else:
                        print_num(x(), False)
                return None
            return print_
        if k == "STR":
            self.next()
            text = t[1]

            def str_():
                emit(text)
                return None
            return str_
        if k == "break":
            self.next()
            if self.loop <= 0:
                raise ParseError("Break outside a for/while")
            return lambda: BREAK
        if k == "continue":
            self.next()
            if self.loop <= 0:
                raise ParseError("Continue outside a for")
            return lambda: CONTINUE
        if k == "halt":
            self.next()

            def halt_():
                raise HaltExc()
            return halt_
        if k == "quit":
            raise QuitExc()
        if k == "return":
            self.next()
            if not self.in_func:
                raise ParseError("return outside a function")
            if self.peek()[0] in (";", "NL", "}", "EOF", "else"):
                if self.void:
                    return lambda: Ret(None)
                return lambda: Ret(ZERO)
            if self.void:
                raise ParseError("return expression in a void function")
            e = self.expr(0)[0]
            return lambda: Ret(e())
        if k == "limits":
            self.next()
            emit(LIMITS_TEXT)
            return lambda: None
        if k == "warranty":
            self.next()
            return lambda: None
        # expression statement
        fn, kind = self.expr(0)
        if kind == "assign":
            def estmt():
                fn()
                return None
        else:
            def estmt():
                v = fn()
                if v is not None:
                    print_num(v, True)
                return None
        return estmt

    # expressions -----------------------------------------------------------
    def expr(self, minp):
        left, kind = self.unary()
        while True:
            t = self.peek()
            p = BINOPS.get(t[0])
            if p is None or p < minp:
                break
            self.next()
            if t[0] == "^":
                right = self.expr(p)[0]
            else:
                right = self.expr(p + 1)[0]
            left = self.make_bin(t, left, right)
            kind = "other"
        return left, kind

    def make_bin(self, t, l, r):
        typ, op = t
        if typ == "+":
            return lambda: add(l(), r())
        if typ == "-":
            return lambda: sub(l(), r())
        if typ == "*":
            return lambda: mul(l(), r(), S.scale)
        if typ == "/":
            return lambda: div(l(), r(), S.scale)
        if typ == "%":
            return lambda: mod(l(), r(), S.scale)
        if typ == "^":
            return lambda: power(l(), r(), S.scale)
        if typ == "&&":
            return lambda: ONE if (l().v != 0 and r().v != 0) else ZERO
        if typ == "||":
            return lambda: ONE if (l().v != 0 or r().v != 0) else ZERO
        if op == "<":
            return lambda: ONE if cmp(l(), r()) < 0 else ZERO
        if op == ">":
            return lambda: ONE if cmp(l(), r()) > 0 else ZERO
        if op == "<=":
            return lambda: ONE if cmp(l(), r()) <= 0 else ZERO
        if op == ">=":
            return lambda: ONE if cmp(l(), r()) >= 0 else ZERO
        if op == "==":
            return lambda: ONE if cmp(l(), r()) == 0 else ZERO
        if op == "!=":
            return lambda: ONE if cmp(l(), r()) != 0 else ZERO
        raise ParseError("syntax error")

    def named(self):
        """Parse a named expression; return LValue or None if not one."""
        t = self.peek()
        k = t[0]
        if k == "NAME":
            nt = self.peek2()
            if nt[0] == "(":
                return None
            self.next()
            if nt[0] == "[":
                self.next()
                idx = self.expr(0)[0]
                self.expect("]")
                return lv_arr(t[1], idx)
            return lv_var(t[1])
        if k in ("ibase", "obase", "last"):
            self.next()
            return lv_special(k)
        if k == "scale":
            if self.peek2()[0] == "(":
                return None
            self.next()
            return lv_special("scale")
        return None

    def unary(self):
        t = self.peek()
        k = t[0]
        if k == "!":
            self.next()
            e = self.expr(4)[0]
            return (lambda: ONE if e().v == 0 else ZERO), "other"
        if k == "-":
            self.next()
            e = self.expr(10)[0]

            def neg_():
                x = e()
                return Num(-x.v, x.s)
            return neg_, "other"
        if k == "INCDEC":
            self.next()
            lv = self.named()
            if lv is None:
                raise ParseError("syntax error: ++/-- needs a variable")
            f = add if t[1] == "++" else sub
            locate, load, store = lv.locate, lv.load, lv.store

            def pre_():
                loc = locate()
                v = f(load(loc), ONE)
                store(loc, v)
                return v
            return pre_, "other"
        if k == "(":
            self.next()
            e = self.expr(0)[0]
            self.expect(")")
            return e, "other"
        if k == "NUM":
            self.next()
            return self.make_const(t[1]), "other"
        if k in ("length", "sqrt") or (k == "scale" and self.peek2()[0] == "("):
            self.next()
            self.expect("(")
            e = self.expr(0)[0]
            self.expect(")")
            if k == "length":
                return (lambda: Num(blength(e()), 0)), "other"
            if k == "sqrt":
                return (lambda: bsqrt(e(), S.scale)), "other"
            return (lambda: Num(e().s, 0)), "other"
        if k == "read":
            self.next()
            self.expect("(")
            self.expect(")")

            def read_():
                raise BcError("read() is not supported")
            return read_, "other"
        if k == "NAME" and self.peek2()[0] == "(":
            return self.call(), "call"
        lv = self.named()
        if lv is None:
            raise ParseError("syntax error")
        nt = self.peek()
        if nt[0] == "ASSIGN":
            self.next()
            rhs = self.expr(5)[0]
            locate, load, store = lv.locate, lv.load, lv.store
            if nt[1] == "=":
                def assign_():
                    loc = locate()
                    v = rhs()
                    store(loc, v)
                    return v
            else:
                op = arith(nt[1][0])

                def assign_():
                    loc = locate()
                    old = load(loc)
                    v = op(old, rhs())
                    store(loc, v)
                    return v
            return assign_, "assign"
        if nt[0] == "INCDEC":
            self.next()
            f = add if nt[1] == "++" else sub
            locate, load, store = lv.locate, lv.load, lv.store

            def post_():
                loc = locate()
                old = load(loc)
                store(loc, f(old, ONE))
                return old
            return post_, "other"
        return lv.get, "other"

    def make_const(self, parts):
        ipart, fpart = parts
        simple = all("0" <= c <= "9" for c in ipart + fpart)
        cache = {}
        if simple:
            v10 = Num(int(ipart + fpart) if (ipart + fpart) else 0, len(fpart))
        else:
            v10 = convert_const(ipart, fpart, 10)
        cache[10] = v10

        def const():
            b = S.ibase
            if b == 10:
                return v10
            r = cache.get(b)
            if r is None:
                r = convert_const(ipart, fpart, b)
                cache[b] = r
            return r
        return const

    def call(self):
        name = self.next()[1]
        self.expect("(")
        args = []
        if self.peek()[0] != ")":
            while True:
                t = self.peek()
                if t[0] == "NAME" and self.peek2()[0] == "[":
                    # could be array arg NAME[] or element NAME[expr]
                    save = self.pos
                    self.next()
                    self.next()
                    if self.peek()[0] == "]":
                        self.next()
                        args.append(("a", ARRS.setdefault(t[1], [{}]), t[1]))
                    else:
                        self.pos = save
                        args.append(("v", self.expr(0)[0], None))
                else:
                    args.append(("v", self.expr(0)[0], None))
                if self.peek()[0] == ",":
                    self.next()
                    continue
                break
        self.expect(")")
        nargs = len(args)

        def call_():
            f = FUNCS.get(name)
            if f is None:
                raise BcError("Function %s not defined." % name)
            vals = []
            for kind, x, _ in args:
                if kind == "v":
                    vals.append(x())
                else:
                    vals.append(None)
            params = f.params
            if len(params) != nargs:
                raise BcError("Parameter number mismatch")
            for (pk, _), (ak, _, _) in zip(params, args):
                if (pk == "v") != (ak == "v"):
                    raise BcError("Parameter type mismatch")
            pushed = []
            try:
                for (pk, st), (ak, x, _), val in zip(params, args, vals):
                    if pk == "v":
                        st.append(val)
                    elif pk == "a":
                        st.append(dict(x[-1]))
                    else:
                        st.append(x[-1])
                    pushed.append(st)
                for ak, st in f.autos:
                    if ak == "v":
                        st.append(ZERO)
                    else:
                        st.append({})
                    pushed.append(st)
                for s in f.body:
                    r = s()
                    if r is not None:
                        if r.__class__ is Ret:
                            return r.v
                        break
                return None if f.void else ZERO
            finally:
                for st in pushed:
                    st.pop()
        return call_


def execute(stmts):
    try:
        for s in stmts:
            s()
    except BcError as e:
        sys.stderr.write("Runtime error: %s\n" % e)
    except RecursionError:
        sys.stderr.write("Runtime error: recursion too deep\n")
    except (TypeError, AttributeError):
        sys.stderr.write("Runtime error: void function used in an expression\n")


RESULT = [0]


def real_main():
    try:
        data = sys.stdin.buffer.read().decode("latin-1")
        toks = lex(data)
        Parser(toks).run()
    except (QuitExc, HaltExc):
        pass
    finally:
        flush_out()
    RESULT[0] = 0


def main():
    sys.setrecursionlimit(1000000)
    threading.stack_size(512 * 1024 * 1024)
    t = threading.Thread(target=real_main)
    t.start()
    t.join()
    try:
        sys.stdout.flush()
    except Exception:
        pass
    return RESULT[0]


if __name__ == "__main__":
    sys.exit(main())
