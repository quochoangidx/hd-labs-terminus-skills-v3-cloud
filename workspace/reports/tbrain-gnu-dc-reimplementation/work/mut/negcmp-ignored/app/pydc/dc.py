"""pydc: a GNU dc 1.4.1 replacement in pure Python.

Usage: python3 /app/pydc/dc.py [OPTION] [FILE]...
"""

import os
import sys

if hasattr(sys, "set_int_max_str_digits"):
    sys.set_int_max_str_digits(0)

EOF = -1
LONG_MAX = 2 ** 63 - 1
REF_STR = "0123456789ABCDEF"

# dc_func results
OKAY, EATONE, EVALREG, EVALTOS, QUIT, INT, STR, SYSTEM, COMMENT, NEGCMP, EOF_ERROR = range(11)
SUCCESS, FAIL = 0, 1


def err(msg):
    sys.stderr.write("dc: " + msg + "\n")


# --------------------------------------------------------------------------- numbers

class Num:
    """A bc number: sign, magnitude digits and scale; value = sign * mag / 10**scale."""

    __slots__ = ("neg", "mag", "scale")

    def __init__(self, mag=0, scale=0, neg=False):
        self.mag, self.scale, self.neg = mag, scale, neg

    @property
    def n_len(self):
        ip = self.mag // 10 ** self.scale
        return len(str(ip)) if ip else 1

    def digits(self):
        """The n_len + n_scale digit characters of the number."""
        ip, fp = divmod(self.mag, 10 ** self.scale)
        s = str(ip) if ip else "0"
        if self.scale:
            s += str(fp).rjust(self.scale, "0")
        return s

    def is_zero(self):
        return self.mag == 0

    def signed(self, s):
        """Signed integer value scaled to s fraction digits (s >= self.scale)."""
        v = self.mag * 10 ** (s - self.scale)
        return -v if self.neg else v


def ZERO():
    return Num(0, 0)


def ONE():
    return Num(1, 0)


def int2num(v):
    return Num(abs(v), 0, v < 0)


def mag_cmp(a, b):
    s = max(a.scale, b.scale)
    x, y = a.mag * 10 ** (s - a.scale), b.mag * 10 ** (s - b.scale)
    return (x > y) - (x < y)


def num_compare(a, b):
    if a.neg != b.neg:
        return 1 if not a.neg else -1
    c = mag_cmp(a, b)
    return -c if a.neg else c


def _do_add(a, b, scale_min):
    s = max(a.scale, b.scale)
    mag = a.mag * 10 ** (s - a.scale) + b.mag * 10 ** (s - b.scale)
    rs = max(s, scale_min)
    return Num(mag * 10 ** (rs - s), rs)


def _do_sub(a, b, scale_min):
    s = max(a.scale, b.scale)
    mag = a.mag * 10 ** (s - a.scale) - b.mag * 10 ** (s - b.scale)
    rs = max(s, scale_min)
    return Num(mag * 10 ** (rs - s), rs)


def num_add(a, b, scale_min=0):
    if a.neg == b.neg:
        r = _do_add(a, b, scale_min)
        r.neg = a.neg
        return r
    c = mag_cmp(a, b)
    if c < 0:
        r = _do_sub(b, a, scale_min)
        r.neg = b.neg
        return r
    if c == 0:
        return Num(0, max(scale_min, a.scale, b.scale))
    r = _do_sub(a, b, scale_min)
    r.neg = a.neg
    return r


def num_sub(a, b, scale_min=0):
    if a.neg != b.neg:
        r = _do_add(a, b, scale_min)
        r.neg = a.neg
        return r
    c = mag_cmp(a, b)
    if c < 0:
        r = _do_sub(b, a, scale_min)
        r.neg = not b.neg
        return r
    if c == 0:
        return Num(0, max(scale_min, a.scale, b.scale))
    r = _do_sub(a, b, scale_min)
    r.neg = a.neg
    return r


def num_mul(a, b, scale):
    full = a.scale + b.scale
    ps = min(full, max(scale, a.scale, b.scale))
    mag = (a.mag * b.mag) // 10 ** (full - ps)
    return Num(mag, ps, (a.neg != b.neg) and mag != 0)


def num_div(a, b, scale):
    """Truncated quotient with `scale` fraction digits, or None on division by zero."""
    if b.is_zero():
        return None
    num = a.mag * 10 ** (scale + b.scale)
    den = b.mag * 10 ** a.scale
    q = num // den
    return Num(q, scale, (a.neg != b.neg) and q != 0)


def num_divmod(a, b, scale):
    if b.is_zero():
        return None
    rscale = max(a.scale, b.scale + scale)
    q = num_div(a, b, scale)
    t = num_mul(q, b, rscale)
    return q, num_sub(a, t, rscale)


def num2long(n):
    val = 0
    ip = n.digits()[:n.n_len]
    i = len(ip)
    k = 0
    while i > 0 and val <= LONG_MAX // 10:
        val = val * 10 + int(ip[k])
        k += 1
        i -= 1
    if i > 0 or val > LONG_MAX:
        val = 0
    return -val if n.neg else val


def num_raise(a, b, scale):
    if b.scale:
        err("Runtime warning: non-zero scale in exponent")
    e = num2long(b)
    if e == 0 and (b.n_len > 1 or b.digits()[0] != "0"):
        err("Runtime error: exponent too large in raise")
    if e == 0:
        return ONE()
    if e < 0:
        neg, ue, rscale = True, -e, scale
    else:
        neg, ue = False, e
        rscale = min(a.scale * ue, max(scale, a.scale))
    power = Num(a.mag, a.scale, a.neg)
    pwrscale = a.scale
    while ue & 1 == 0:
        pwrscale <<= 1
        power = num_mul(power, power, pwrscale)
        ue >>= 1
    temp = Num(power.mag, power.scale, power.neg)
    calcscale = pwrscale
    ue >>= 1
    while ue > 0:
        pwrscale <<= 1
        power = num_mul(power, power, pwrscale)
        if ue & 1:
            calcscale = pwrscale + calcscale
            temp = num_mul(temp, power, calcscale)
        ue >>= 1
    if neg:
        # a failed division leaves the zero the result was initialised to
        r = num_div(ONE(), temp, rscale)
        return r if r is not None else ZERO()
    if temp.scale > rscale:
        # the scale is cut in place: the sign survives even if the value becomes zero
        temp = Num(temp.mag // 10 ** (temp.scale - rscale), rscale, temp.neg)
    return temp


def num_raisemod(base, expo, mod, scale):
    if mod.is_zero() or (expo.neg and not expo.is_zero()):
        return None
    if base.scale:
        err("Runtime warning: non-zero scale in base")
    exponent = Num(expo.mag, expo.scale, expo.neg)
    if exponent.scale:
        err("Runtime warning: non-zero scale in exponent")
        exponent = num_div(exponent, ONE(), 0)
    if mod.scale:
        err("Runtime warning: non-zero scale in modulus")
    power = Num(base.mag, base.scale, base.neg)
    temp = ONE()
    rscale = max(scale, base.scale)
    two = int2num(2)
    while not exponent.is_zero():
        exponent, parity = num_divmod(exponent, two, 0)
        if not parity.is_zero():
            temp = num_mul(temp, power, rscale)
            temp = num_divmod(temp, mod, scale)[1]
        power = num_mul(power, power, rscale)
        power = num_divmod(power, mod, scale)[1]
    return temp


def is_near_zero(n, scale):
    if scale > n.scale:
        scale = n.scale
    d = n.digits()[:n.n_len + scale]
    count = len(d)
    k = 0
    while count > 0 and d[k] == "0":
        k += 1
        count -= 1
    return count == 0 or (count == 1 and d[k] == "1")


def num_sqrt(n, scale):
    c = num_compare(n, ZERO())
    if c < 0:
        return None
    if c == 0:
        return ZERO()
    c = num_compare(n, ONE())
    if c == 0:
        return ONE()
    rscale = max(scale, n.scale)
    point5 = Num(5, 1)
    if c < 0:
        guess = ONE()
        cscale = n.scale
    else:
        g1 = num_mul(int2num(n.n_len), point5, 0)
        g1 = Num(g1.mag // 10 ** g1.scale, 0, g1.neg)
        guess = num_raise(int2num(10), g1, 0)
        cscale = 3
    while True:
        guess1 = guess
        guess = num_div(n, guess, cscale)
        guess = num_add(guess, guess1, 0)
        guess = num_mul(guess, point5, cscale)
        diff = num_sub(guess, guess1, cscale + 1)
        if is_near_zero(diff, cscale):
            if cscale < rscale + 1:
                cscale = min(cscale * 3, rscale + 1)
            else:
                break
    return num_div(guess, ONE(), rscale)


def num_numlen(n):
    d = n.digits()
    i = len(d)
    k = 0
    while 1 < i and d[k] == "0":
        i -= 1
        k += 1
    return i


def num2int(n):
    r = num2long(n)
    if (r == 0 and not n.is_zero()) or abs(r) >= 1 << 31:
        err("value overflows simple integer; punting...")
        r = -1
    return r


# --------------------------------------------------------------------------- data

class Str:
    __slots__ = ("s",)

    def __init__(self, s):
        self.s = s


class Entry:
    __slots__ = ("value", "array")

    def __init__(self, value=None):
        self.value = value
        self.array = None


class Stream:
    def __init__(self, data):
        self.data = data
        self.pos = 0
        self.back = []

    def getc(self):
        if self.back:
            return self.back.pop()
        if self.pos < len(self.data):
            c = self.data[self.pos]
            self.pos += 1
            return c
        return EOF

    def ungetc(self, c):
        if c != EOF:
            self.back.append(c)


class DC:
    def __init__(self, stdin_data):
        self.stack = []
        self.regs = {}
        self.ibase = 10
        self.obase = 10
        self.scale = 0
        self.unwind_depth = 0
        self.unwind_noexit = False
        self.stdin = Stream(stdin_data)
        self.stdin_lookahead = EOF
        self.out = []
        self.line_max = 70
        env = os.environ.get("DC_LINE_LENGTH")
        if env is not None:
            try:
                v = int(env.strip(), 0)
                self.line_max = 70 if v < 0 or v == 1 else v
            except ValueError:
                self.line_max = 70

    # ---- output
    def put(self, s):
        self.out.append(s)

    def out_num(self, n, obase):
        col = [0]
        buf = []
        lm = self.line_max

        def out_char(ch):
            col[0] += 1
            if col[0] >= lm and lm != 0:
                buf.append("\\\n")
                col[0] = 1
            buf.append(ch)

        if n.neg:
            out_char("-")
        if n.is_zero():
            out_char("0")
        elif obase == 10:
            d = n.digits()
            k = 0
            if n.n_len > 1 or d[0] != "0":
                for k in range(n.n_len):
                    out_char(d[k])
            if n.scale > 0:
                out_char(".")
                for ch in d[n.n_len:]:
                    out_char(ch)
        else:
            ip, fp = divmod(n.mag, 10 ** n.scale)
            width = len(str(obase - 1))
            digs = []
            while ip:
                ip, r = divmod(ip, obase)
                digs.append(r)
            for dgt in reversed(digs):
                if obase <= 16:
                    out_char(REF_STR[dgt])
                else:
                    out_char(" ")
                    for ch in str(dgt).rjust(width, "0"):
                        out_char(ch)
            if n.scale > 0:
                out_char(".")
                pre_space = False
                t = 1
                lim = 10 ** n.scale
                f = fp
                while t < lim:
                    f *= obase
                    dgt, f = divmod(f, 10 ** n.scale)
                    if obase <= 16:
                        out_char(REF_STR[dgt])
                    else:
                        if pre_space:
                            out_char(" ")
                        for ch in str(dgt).rjust(width, "0"):
                            out_char(ch)
                        pre_space = True
                    t *= obase
        self.put("".join(buf))

    def print_datum(self, v, newline):
        if isinstance(v, Num):
            self.out_num(v, self.obase)
        else:
            self.put(v.s)
        if newline:
            self.put("\n")

    def dump_num(self, n):
        v = n.mag // 10 ** n.scale
        bs = []
        while True:
            v, r = divmod(v, 256)
            bs.append(r)
            if v == 0:
                break
        self.put("".join(chr(b) for b in reversed(bs)))

    # ---- stack
    def push(self, v):
        self.stack.append(v)

    def pop(self):
        if not self.stack:
            err("stack empty")
            return None
        return self.stack.pop()

    def top(self):
        if not self.stack:
            err("stack empty")
            return None
        return self.stack[-1]

    def binop(self, op):
        if len(self.stack) < 2:
            err("stack empty")
            return
        if not isinstance(self.stack[-1], Num) or not isinstance(self.stack[-2], Num):
            err("non-numeric value")
            return
        b = self.stack.pop()
        a = self.stack.pop()
        r = op(a, b)
        if r is None:
            self.push(a)
            self.push(b)
        elif isinstance(r, tuple):
            self.push(r[0])
            self.push(r[1])
        else:
            self.push(r)

    def triop(self, op):
        if len(self.stack) < 3:
            err("stack empty")
            return
        if not all(isinstance(x, Num) for x in self.stack[-3:]):
            err("non-numeric value")
            return
        c = self.stack.pop()
        b = self.stack.pop()
        a = self.stack.pop()
        r = op(a, b, c)
        if r is None:
            self.push(a)
            self.push(b)
            self.push(c)
        else:
            self.push(r)

    def cmpop(self):
        if len(self.stack) < 2:
            err("stack empty")
            return 0
        if not isinstance(self.stack[-1], Num) or not isinstance(self.stack[-2], Num):
            err("non-numeric value")
            return 0
        b = self.stack.pop()
        a = self.stack.pop()
        return num_compare(b, a)

    def rotate(self, n):
        absn = abs(n)
        if not self.stack or absn < 2:
            return
        k = min(absn, len(self.stack))
        if k < 2:
            return
        seg = self.stack[-k:]
        if n > 0:
            # the k-th element from the top becomes the top
            seg = seg[1:] + [seg[0]]
        else:
            # the top element sinks to the k-th position
            seg = [seg[-1]] + seg[:-1]
        self.stack[-k:] = seg

    # ---- registers
    def reg(self, r):
        return self.regs.setdefault(ord(r) & 255 if isinstance(r, str) else r & 255, [])

    def register_get(self, r):
        st = self.reg(r)
        if not st:
            return True, ZERO()
        if st[-1].value is None:
            err("BUG: register exists but is uninitialized?")
            return False, None
        return True, st[-1].value

    def register_set(self, r, v):
        st = self.reg(r)
        if not st:
            st.append(Entry())
        st[-1].value = v

    def register_push(self, r, v):
        self.reg(r).append(Entry(v))

    def register_pop(self, r):
        st = self.reg(r)
        if not st or st[-1].value is None:
            err("stack register is empty")
            return None
        return st.pop().value

    def array_set(self, r, idx, v):
        st = self.reg(r)
        if not st:
            st.append(Entry())
        if st[-1].array is None:
            st[-1].array = {}
        st[-1].array[idx] = v

    def array_get(self, r, idx):
        st = self.reg(r)
        if not st or st[-1].array is None or idx not in st[-1].array:
            return ZERO()
        return st[-1].array[idx]

    # ---- one command
    def func(self, c, peekc, negcmp):
        if c in "_.0123456789ABCDEF":
            return INT
        if c in " \t\n":
            return OKAY
        if c in "+-*/%^":
            sc = self.scale
            ops = {"+": lambda a, b: num_add(a, b, 0), "-": lambda a, b: num_sub(a, b, 0),
                   "*": lambda a, b: num_mul(a, b, sc), "/": lambda a, b: self._div(a, b, sc),
                   "%": lambda a, b: self._rem(a, b, sc), "^": lambda a, b: num_raise(a, b, sc)}
            self.binop(ops[c])
            return OKAY
        if c == "~":
            sc = self.scale
            self.binop(lambda a, b: self._divrem(a, b, sc))
            return OKAY
        if c == "|":
            sc = self.scale
            self.triop(lambda a, b, m: self._modexp(a, b, m, sc))
            return OKAY
        if c in "<=>":
            if peekc == EOF:
                return EOF_ERROR
            r = self.cmpop()
            hold = {"<": r < 0, "=": r == 0, ">": r > 0}[c]
            return EVALREG if hold == (negcmp == 0) else EATONE
        if c == "?":
            if self.stdin_lookahead != EOF:
                self.stdin.ungetc(self.stdin_lookahead)
                self.stdin_lookahead = EOF
            self.push(Str(self.readstring(self.stdin, "\n", "\n")))
            return EVALTOS
        if c == "[":
            return STR
        if c == "!":
            if peekc in ("<", "=", ">"):
                return OKAY
            return SYSTEM
        if c == "#":
            return COMMENT
        if c == "a":
            d = self.pop()
            if d is not None:
                if isinstance(d, Num):
                    ch = chr(num2int(d) & 255)
                else:
                    ch = d.s[0] if d.s else "\0"
                self.push(Str(ch))
            return OKAY
        if c == "c":
            self.stack = []
            return OKAY
        if c == "d":
            d = self.top()
            if d is not None:
                self.push(d)
            return OKAY
        if c == "f":
            for v in reversed(self.stack):
                self.print_datum(v, True)
            return OKAY
        if c == "i":
            d = self.pop()
            if d is not None:
                t = num2int(d) if isinstance(d, Num) else 0
                if 2 <= t <= 16:
                    self.ibase = t
                else:
                    err("input base must be a number between 2 and 16 (inclusive)")
            return OKAY
        if c == "k":
            d = self.pop()
            if d is not None:
                t = num2int(d) if isinstance(d, Num) else -1
                if not t >= 0:
                    err("scale must be a nonnegative number")
                else:
                    self.scale = t
            return OKAY
        if c == "l":
            if peekc == EOF:
                return EOF_ERROR
            ok, v = self.register_get(peekc)
            if ok:
                self.push(v)
            return EATONE
        if c == "n":
            d = self.pop()
            if d is not None:
                self.print_datum(d, False)
            return OKAY
        if c == "o":
            d = self.pop()
            if d is not None:
                t = num2int(d) if isinstance(d, Num) else 0
                if not t > 1:
                    err("output base must be a number greater than 1")
                else:
                    self.obase = t
            return OKAY
        if c == "p":
            d = self.top()
            if d is not None:
                self.print_datum(d, True)
            return OKAY
        if c == "q":
            self.unwind_depth = 1
            self.unwind_noexit = False
            return QUIT
        if c == "r":
            self.rotate(2)
            return OKAY
        if c == "s":
            if peekc == EOF:
                return EOF_ERROR
            d = self.pop()
            if d is not None:
                self.register_set(peekc, d)
            return EATONE
        if c == "v":
            d = self.pop()
            if d is not None:
                if not isinstance(d, Num):
                    err("square root of nonnumeric attempted")
                else:
                    r = num_sqrt(d, self.scale)
                    if r is None:
                        err("square root of negative number")
                    else:
                        self.push(r)
            return OKAY
        if c == "x":
            return EVALTOS
        if c == "z":
            self.push(int2num(len(self.stack)))
            return OKAY
        if c == "I":
            self.push(int2num(self.ibase))
            return OKAY
        if c == "K":
            self.push(int2num(self.scale))
            return OKAY
        if c == "L":
            if peekc == EOF:
                return EOF_ERROR
            v = self.register_pop(peekc)
            if v is not None:
                self.push(v)
            return EATONE
        if c == "O":
            self.push(int2num(self.obase))
            return OKAY
        if c == "P":
            d = self.pop()
            if d is not None:
                if isinstance(d, Num):
                    self.dump_num(d)
                else:
                    self.put(d.s)
            return OKAY
        if c == "Q":
            d = self.pop()
            if d is not None:
                self.unwind_depth = 0
                self.unwind_noexit = True
                if isinstance(d, Num):
                    self.unwind_depth = num2int(d)
                self.unwind_depth -= 1
                if self.unwind_depth + 1 > 0:
                    return QUIT
                self.unwind_depth = 0
                err("Q command requires a number >= 1")
            return OKAY
        if c == "R":
            d = self.pop()
            if d is not None:
                self.rotate(num2int(d) if isinstance(d, Num) else 0)
            return OKAY
        if c == "S":
            if peekc == EOF:
                return EOF_ERROR
            d = self.pop()
            if d is not None:
                self.register_push(peekc, d)
            return EATONE
        if c == "X":
            d = self.pop()
            if d is not None:
                self.push(int2num(d.scale if isinstance(d, Num) else 0))
            return OKAY
        if c == "Z":
            d = self.pop()
            if d is not None:
                self.push(int2num(num_numlen(d) if isinstance(d, Num) else len(d.s)))
            return OKAY
        if c == ":":
            if peekc == EOF:
                return EOF_ERROR
            d = self.pop()
            if d is not None:
                t = num2int(d) if isinstance(d, Num) else -1
                v = self.pop()
                if v is not None:
                    if t < 0:
                        err("array index must be a nonnegative integer")
                    else:
                        self.array_set(peekc, t, v)
            return EATONE
        if c == ";":
            if peekc == EOF:
                return EOF_ERROR
            d = self.pop()
            if d is not None:
                t = num2int(d) if isinstance(d, Num) else -1
                if t < 0:
                    err("array index must be a nonnegative integer")
                else:
                    self.push(self.array_get(peekc, t))
            return EATONE
        o = ord(c)
        if 33 <= o <= 126:
            self.put("'%s' (0%o) unimplemented\n" % (c, o))
        else:
            self.put(("0%o" % o if o else "0") + " unimplemented\n")
        return OKAY

    def _div(self, a, b, sc):
        r = num_div(a, b, sc)
        if r is None:
            err("divide by zero")
        return r

    def _rem(self, a, b, sc):
        r = num_divmod(a, b, sc)
        if r is None:
            err("remainder by zero")
            return None
        return r[1]

    def _divrem(self, a, b, sc):
        r = num_divmod(a, b, sc)
        if r is None:
            err("divide by zero")
        return r

    def _modexp(self, a, b, m, sc):
        r = num_raisemod(a, b, m, sc)
        if r is None and m.is_zero():
            err("remainder by zero")
        return r

    # ---- reading
    def readstring(self, fp, ldelim, rdelim):
        depth = 1
        out = []
        while True:
            c = fp.getc()
            if c == EOF:
                break
            if c == rdelim:
                depth -= 1
                if depth < 1:
                    break
            elif c == ldelim:
                depth += 1
            out.append(c)
        return "".join(out)

    def getnum(self, getc):
        c = getc()
        while c != EOF and c.isspace():
            c = getc()
        negative = False
        if c in ("_", "-"):
            negative = True
            c = getc()
        elif c == "+":
            c = getc()
        while c != EOF and c.isspace():
            c = getc()
        base = self.ibase
        result = 0
        while c != EOF and (c.isdigit() or "A" <= c <= "F"):
            result = result * base + (int(c) if c.isdigit() else 10 + ord(c) - 65)
            c = getc()
        res = Num(result, 0)
        if c == ".":
            build = 0
            divisor = 1
            decimal = 0
            while True:
                c = getc()
                if c != EOF and (c.isdigit() or "A" <= c <= "F"):
                    build = build * base + (int(c) if c.isdigit() else 10 + ord(c) - 65)
                    divisor *= base
                    decimal += 1
                else:
                    break
            frac = num_div(Num(build, 0), Num(divisor, 0), decimal)
            res = num_add(res, frac, 0)
        if negative:
            res = num_sub(ZERO(), res, 0)
        return res, c

    # ---- evaluation of strings
    def evalstr(self, text):
        s = text
        i = 0
        end = len(s)
        next_negcmp = 0
        tail_depth = 1
        while i < end:
            c = s[i]
            i += 1
            peekc = s[i] if i < end else EOF
            negcmp = next_negcmp
            next_negcmp = 0
            st = self.func(c, peekc, negcmp)
            if st == OKAY:
                continue
            if st == EATONE:
                if peekc != EOF:
                    i += 1
                continue
            if st == EVALREG:
                i += 1
                ok, v = self.register_get(peekc)
                if not ok:
                    continue
                self.push(v)
                st = EVALTOS
            if st == EVALTOS:
                while i < end and s[i] in " \t\n#":
                    ch = s[i]
                    i += 1
                    if ch == "#":
                        j = s.find("\n", i)
                        i = end if j < 0 else j + 1
                d = self.pop()
                if d is None:
                    continue
                if isinstance(d, Num):
                    self.push(d)
                elif i == end:
                    s = d.s
                    i = 0
                    end = len(s)
                    tail_depth += 1
                elif self.evalstr(d.s) == QUIT:
                    if self.unwind_depth > 0:
                        self.unwind_depth -= 1
                        return QUIT
                    return OKAY
                continue
            if st == QUIT:
                if self.unwind_depth >= tail_depth:
                    self.unwind_depth -= tail_depth
                    return QUIT
                tail_depth -= self.unwind_depth
                continue
            if st == INT:
                pos = [i - 1]

                def getc():
                    if pos[0] >= end:
                        return EOF
                    ch = s[pos[0]]
                    pos[0] += 1
                    return ch
                num, ra = self.getnum(getc)
                self.push(num)
                i = pos[0]
                if ra != EOF:
                    i -= 1
                continue
            if st == STR:
                count = 1
                p = i
                while p < end and count > 0:
                    if s[p] == "]":
                        count -= 1
                    elif s[p] == "[":
                        count += 1
                    p += 1
                self.push(Str(s[i:p - 1] if count == 0 else s[i:p]))
                i = p
                continue
            if st == SYSTEM:
                j = s.find("\n", i)
                i = end if j < 0 else j + 1
                continue
            if st == COMMENT:
                j = s.find("\n", i)
                i = end if j < 0 else j + 1
                continue
            if st == NEGCMP:
                next_negcmp = 1
                continue
            if st == EOF_ERROR:
                err("unexpected EOS")
                return OKAY
        return OKAY

    def dc_evalstr(self, text):
        r = self.evalstr(text)
        if r == OKAY:
            return SUCCESS
        if r == QUIT:
            return SUCCESS if self.unwind_noexit else FAIL
        return FAIL

    # ---- evaluation of files
    def evalfile(self, fp):
        is_stdin = fp is self.stdin
        next_negcmp = 0
        self.stdin_lookahead = EOF
        c = fp.getc()
        while c != EOF:
            peekc = fp.getc()
            if is_stdin:
                self.stdin_lookahead = peekc
            negcmp = next_negcmp
            next_negcmp = 0
            st = self.func(c, peekc, negcmp)
            if st == OKAY:
                if self.stdin_lookahead != peekc and is_stdin:
                    peekc = fp.getc()
            elif st == EATONE:
                peekc = fp.getc()
            elif st in (EVALREG, EVALTOS):
                go = True
                if st == EVALREG:
                    rc = peekc
                    peekc = fp.getc()
                    self.stdin_lookahead = peekc
                    ok, v = self.register_get(rc)
                    if ok:
                        self.push(v)
                    else:
                        go = False
                if go:
                    if self.stdin_lookahead != peekc and is_stdin:
                        peekc = fp.getc()
                    d = self.pop()
                    if d is not None:
                        if isinstance(d, Num):
                            self.push(d)
                        elif self.evalstr(d.s) == QUIT:
                            if not self.unwind_noexit:
                                return FAIL
                            err("Q command argument exceeded string execution depth")
            elif st == QUIT:
                if not self.unwind_noexit:
                    return FAIL
                err("Q command argument exceeded string execution depth")
                if self.stdin_lookahead != peekc and is_stdin:
                    peekc = fp.getc()
            elif st == INT:
                pending = [c]
                fp.ungetc(peekc)

                def getc():
                    if pending:
                        return pending.pop()
                    return fp.getc()
                num, peekc = self.getnum(getc)
                self.push(num)
            elif st == STR:
                fp.ungetc(peekc)
                self.push(Str(self.readstring(fp, "[", "]")))
                peekc = fp.getc()
            elif st == SYSTEM:
                fp.ungetc(peekc)
                self.readstring(fp, "\n", "\n")
                peekc = fp.getc()
            elif st == COMMENT:
                while peekc != EOF and peekc != "\n":
                    peekc = fp.getc()
                if peekc != EOF:
                    peekc = fp.getc()
            elif st == NEGCMP:
                next_negcmp = 1
            elif st == EOF_ERROR:
                err("unexpected EOF")
                return FAIL
            c = peekc
        return SUCCESS


def main(argv):
    data = sys.stdin.buffer.read().decode("latin-1") if not sys.stdin.isatty() else ""
    dc = DC(data)
    code = 0
    did_eval = False
    files = []
    i = 0
    try:
        while i < len(argv):
            a = argv[i]
            if a == "--":
                files.extend(argv[i + 1:])
                break
            if a in ("-e", "--expression") or a.startswith("--expression=") or (a.startswith("-e") and len(a) > 2):
                if a.startswith("--expression="):
                    expr = a.split("=", 1)[1]
                elif a in ("-e", "--expression"):
                    i += 1
                    expr = argv[i] if i < len(argv) else ""
                else:
                    expr = a[2:]
                if dc.dc_evalstr(expr) != SUCCESS:
                    raise SystemExit(0)
                did_eval = True
            elif a in ("-f", "--file") or a.startswith("--file=") or (a.startswith("-f") and len(a) > 2):
                if a.startswith("--file="):
                    name = a.split("=", 1)[1]
                elif a in ("-f", "--file"):
                    i += 1
                    name = argv[i] if i < len(argv) else ""
                else:
                    name = a[2:]
                try_file(dc, name)
                did_eval = True
            elif a.startswith("-") and a != "-":
                sys.stderr.write("dc: invalid option\n")
                code = 1
                raise SystemExit(1)
            else:
                files.append(a)
            i += 1
        for name in files:
            try_file(dc, name)
            did_eval = True
        if not did_eval:
            if dc.evalfile(dc.stdin) != SUCCESS:
                code = 1
    except SystemExit as e:
        code = e.code if isinstance(e.code, int) else 0
    sys.stdout.buffer.write("".join(dc.out).encode("latin-1"))
    sys.stdout.flush()
    return code


def try_file(dc, name):
    if name == "-":
        fp = dc.stdin
    else:
        try:
            with open(name, "rb") as f:
                fp = Stream(f.read().decode("latin-1"))
        except OSError:
            sys.stderr.write("dc: Could not open file %s\n" % name)
            return
    if dc.evalfile(fp) != SUCCESS:
        raise SystemExit(1)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
