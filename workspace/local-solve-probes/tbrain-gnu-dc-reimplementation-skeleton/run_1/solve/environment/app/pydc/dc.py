"""pydc: a GNU dc 1.4.1 replacement in pure Python.

Usage: python3 /app/pydc/dc.py [OPTION] [FILE]...

Numbers are modelled on the bc_num type of GNU bc's number.c (sign flag,
magnitude, scale) and every arithmetic routine mirrors the scale and
truncation rules of the corresponding libbc function.
"""

import os
import re
import sys

try:
    sys.set_int_max_str_digits(0)
except AttributeError:  # pragma: no cover
    pass

PROG = "dc"
LONG_MAX = (1 << 63) - 1

_P10 = [1]


def p10(n):
    if n < len(_P10):
        return _P10[n]
    if n < 4096:
        while len(_P10) <= n:
            _P10.append(_P10[-1] * 10)
        return _P10[n]
    return 10 ** n


def err(msg):
    try:
        sys.stderr.write("%s: %s\n" % (PROG, msg))
    except Exception:
        pass


# ---------------------------------------------------------------------------
# bc_num emulation
# ---------------------------------------------------------------------------

class Num(object):
    __slots__ = ("neg", "mag", "scale")

    def __init__(self, neg, mag, scale):
        self.neg = neg
        self.mag = mag
        self.scale = scale


ZERO = Num(False, 0, 0)
ONE = Num(False, 1, 0)
TWO = Num(False, 2, 0)
TEN = Num(False, 10, 0)


def int2num(i):
    if i < 0:
        return Num(True, -i, 0)
    return Num(False, i, 0)


def is_zero(n):
    return n.mag == 0


def int_part(n):
    if n.scale:
        return n.mag // p10(n.scale)
    return n.mag


def n_len(n):
    ip = int_part(n)
    if ip == 0:
        return 1
    return len(str(ip))


def _align(a, b):
    sa = a.scale
    sb = b.scale
    if sa == sb:
        return a.mag, b.mag, sa
    if sa > sb:
        return a.mag, b.mag * p10(sa - sb), sa
    return a.mag * p10(sb - sa), b.mag, sb


def _rescale(mag, frm, to):
    if to >= frm:
        return mag * p10(to - frm)
    return mag // p10(frm - to)


def bc_add(a, b, scale_min=0):
    A, B, s = _align(a, b)
    rs = max(s, scale_min)
    if rs != s:
        A *= p10(rs - s)
        B *= p10(rs - s)
    if a.neg == b.neg:
        return Num(a.neg, A + B, rs)
    if A == B:
        return Num(False, 0, rs)
    if A > B:
        return Num(a.neg, A - B, rs)
    return Num(b.neg, B - A, rs)


def bc_sub(a, b, scale_min=0):
    A, B, s = _align(a, b)
    rs = max(s, scale_min)
    if rs != s:
        A *= p10(rs - s)
        B *= p10(rs - s)
    if a.neg != b.neg:
        return Num(a.neg, A + B, rs)
    if A == B:
        return Num(False, 0, rs)
    if A > B:
        return Num(a.neg, A - B, rs)
    return Num(not b.neg, B - A, rs)


def bc_compare(a, b):
    if a.neg != b.neg:
        return -1 if a.neg else 1
    A, B, _ = _align(a, b)
    if A == B:
        return 0
    r = 1 if A > B else -1
    return -r if a.neg else r


def bc_multiply(a, b, scale):
    full = a.scale + b.scale
    ps = min(full, max(scale, a.scale, b.scale))
    m = a.mag * b.mag
    if ps != full:
        m //= p10(full - ps)
    neg = a.neg != b.neg
    if m == 0:
        neg = False
    return Num(neg, m, ps)


def bc_divide(a, b, scale):
    """Return quotient or None on divide by zero."""
    if b.mag == 0:
        return None
    if b.scale == 0 and b.mag == 1:
        return Num(a.neg != b.neg, _rescale(a.mag, a.scale, scale), scale)
    # value = (a.mag / 10^sa) / (b.mag / 10^sb), truncated to `scale` digits
    num = a.mag * p10(b.scale + scale)
    den = b.mag * p10(a.scale)
    q = num // den
    neg = a.neg != b.neg
    if q == 0:
        neg = False
    return Num(neg, q, scale)


def bc_divmod(a, b, scale):
    """Return (quotient, remainder) or None."""
    if b.mag == 0:
        return None
    rscale = max(a.scale, b.scale + scale)
    q = bc_divide(a, b, scale)
    t = bc_multiply(q, b, rscale)
    r = bc_sub(a, t, rscale)
    return q, r


def bc_modulo(a, b, scale):
    r = bc_divmod(a, b, scale)
    if r is None:
        return None
    return r[1]


def num2long(n):
    ip = int_part(n)
    if ip > LONG_MAX:
        return 0
    return -ip if n.neg else ip


def num2int(n):
    r = num2long(n)
    if r == 0 and n.mag != 0:
        err("value overflows simple integer; punting...")
        r = -1
    r &= 0xFFFFFFFF
    if r >= 0x80000000:
        r -= 0x100000000
    return r


def bc_raise(base, expo, scale):
    if expo.scale != 0:
        err("warning: non-zero scale in exponent")
    e = num2long(expo)
    if e == 0 and int_part(expo) != 0:
        err("exponent too large in raise")
    if e == 0:
        return Num(False, 1, 0)
    if e < 0:
        neg = True
        e = -e
        rscale = scale
    else:
        neg = False
        rscale = min(base.scale * e, max(scale, base.scale))
    power = base
    pwrscale = base.scale
    while (e & 1) == 0:
        pwrscale = 2 * pwrscale
        power = bc_multiply(power, power, pwrscale)
        e >>= 1
    temp = power
    calcscale = pwrscale
    e >>= 1
    while e > 0:
        pwrscale = 2 * pwrscale
        power = bc_multiply(power, power, pwrscale)
        if e & 1:
            calcscale = pwrscale + calcscale
            temp = bc_multiply(temp, power, calcscale)
        e >>= 1
    if neg:
        r = bc_divide(ONE, temp, rscale)
        if r is None:
            return Num(False, 0, 0)
        return r
    if temp.scale > rscale:
        temp = Num(temp.neg, temp.mag // p10(temp.scale - rscale), rscale)
    return temp


def bc_is_near_zero(n, scale):
    if scale > n.scale:
        scale = n.scale
    t = n.mag // p10(n.scale - scale)
    return t == 0 or t == 1


def bc_sqrt(num, scale):
    c = bc_compare(num, ZERO)
    if c < 0:
        return None
    if c == 0:
        return Num(False, 0, 0)
    c = bc_compare(num, ONE)
    if c == 0:
        return Num(False, 1, 0)
    rscale = max(scale, num.scale)
    point5 = Num(False, 5, 1)
    if c < 0:
        guess = ONE
        cscale = num.scale
    else:
        g1 = int2num(n_len(num))
        g1 = bc_multiply(g1, point5, 0)
        g1 = Num(g1.neg, g1.mag // p10(g1.scale), 0)
        guess = bc_raise(TEN, g1, 0)
        cscale = 3
    while True:
        guess1 = guess
        guess = bc_divide(num, guess, cscale)
        guess = bc_add(guess, guess1)
        guess = bc_multiply(guess, point5, cscale)
        diff = bc_sub(guess, guess1, cscale + 1)
        if bc_is_near_zero(diff, cscale):
            if cscale < rscale + 1:
                cscale = min(cscale * 3, rscale + 1)
            else:
                break
    return bc_divide(guess, ONE, rscale)


def bc_raisemod(base, expo, mod, scale):
    if mod.mag == 0:
        return None
    if expo.neg:
        return None
    power = base
    exponent = expo
    modulus = mod
    temp = ONE
    if power.scale != 0:
        err("warning: non-zero scale in base")
    if exponent.scale != 0:
        err("warning: non-zero scale in exponent")
        exponent = bc_divide(exponent, ONE, 0)
    if modulus.scale != 0:
        err("warning: non-zero scale in modulus")
    rscale = max(scale, power.scale)
    while exponent.mag != 0:
        exponent, parity = bc_divmod(exponent, TWO, 0)
        if parity.mag != 0:
            temp = bc_multiply(temp, power, rscale)
            temp = bc_modulo(temp, modulus, scale)
        power = bc_multiply(power, power, rscale)
        power = bc_modulo(power, modulus, scale)
    return temp


# ---------------------------------------------------------------------------
# output formatting
# ---------------------------------------------------------------------------

REF_STR = "0123456789ABCDEF"


def _int_digits(ip, base):
    if ip == 0:
        return []
    if base == 16:
        return [int(ch, 16) for ch in format(ip, "x")]
    if base == 8:
        return [int(ch) for ch in format(ip, "o")]
    if base == 2:
        return [int(ch) for ch in format(ip, "b")]
    ds = []
    while ip:
        ip, d = divmod(ip, base)
        ds.append(d)
    ds.reverse()
    return ds


def num_to_str(n, base):
    parts = []
    if n.neg:
        parts.append("-")
    if n.mag == 0:
        parts.append("0")
        return "".join(parts)
    s = n.scale
    if base == 10:
        if s:
            ip, fp = divmod(n.mag, p10(s))
        else:
            ip, fp = n.mag, 0
        if ip:
            parts.append(str(ip))
        if s:
            parts.append(".")
            parts.append(str(fp).zfill(s))
        return "".join(parts)
    lim = p10(s)
    ip, frac = divmod(n.mag, lim)
    width = len(str(base - 1))
    for d in _int_digits(ip, base):
        if base <= 16:
            parts.append(REF_STR[d])
        else:
            parts.append(" " + str(d).zfill(width))
    if s > 0:
        parts.append(".")
        t = 1
        first = True
        while t < lim:
            frac *= base
            d = frac // lim
            frac -= d * lim
            if base <= 16:
                parts.append(REF_STR[d])
            else:
                parts.append(("" if first else " ") + str(d).zfill(width))
                first = False
            t *= base
    return "".join(parts)


def get_line_len():
    v = os.environ.get("DC_LINE_LENGTH")
    if v is None:
        return 70
    m = re.match(r"^[ \t\n\v\f\r]*([+-]?[0-9]+)$", v)
    if not m:
        return 70
    try:
        n = int(m.group(1))
    except ValueError:
        return 70
    if n == 0:
        return 0
    if n < 2 or n > 0x7FFFFFFF:
        return 70
    return n


LINE_LEN = get_line_len()


def split_lines(s):
    L = LINE_LEN
    if L == 0 or len(s) < L:
        return s
    step = L - 1
    chunks = [s[i:i + step] for i in range(0, len(s), step)]
    return "\\\n".join(chunks)


# ---------------------------------------------------------------------------
# interpreter
# ---------------------------------------------------------------------------

class Stream(object):
    __slots__ = ("data", "pos")

    def __init__(self, data):
        self.data = data
        self.pos = 0


class Frame(object):
    __slots__ = ("st", "levels", "nc", "top")

    def __init__(self, st, levels, top=False):
        self.st = st
        self.levels = levels
        self.nc = 0
        self.top = top


class Quit(Exception):
    pass


SPACES = (32, 9, 10, 11, 12, 13)
DIGIT_VAL = {}
for _i, _ch in enumerate(b"0123456789"):
    DIGIT_VAL[_ch] = _i
for _i, _ch in enumerate(b"ABCDEF"):
    DIGIT_VAL[_ch] = 10 + _i
NUM_START = set(DIGIT_VAL) | {ord("_"), ord(".")}


class DC(object):
    def __init__(self):
        self.stack = []
        self.regs = {}
        self.ibase = 10
        self.obase = 10
        self.scale = 0
        self.out = []
        self.stdin_stream = None
        self.frames = None

    # -- helpers -----------------------------------------------------------
    def get_stdin(self):
        if self.stdin_stream is None:
            try:
                data = sys.stdin.buffer.read()
            except Exception:
                data = b""
            self.stdin_stream = Stream(data)
        return self.stdin_stream

    def write(self, b):
        self.out.append(b)

    def flush(self):
        if self.out:
            data = b"".join(self.out)
            self.out = []
            try:
                sys.stdout.buffer.write(data)
                sys.stdout.buffer.flush()
            except Exception:
                pass

    def pop(self):
        if self.stack:
            return self.stack.pop()
        err("stack empty")
        return None

    def print_val(self, v, newline):
        if isinstance(v, Num):
            s = split_lines(num_to_str(v, self.obase))
            b = s.encode("latin-1")
        else:
            b = v
        if newline:
            b = b + b"\n"
        self.write(b)

    # -- number and string readers ----------------------------------------
    def read_number(self, st):
        data = st.data
        n = len(data)
        i = st.pos

        def get():
            nonlocal i
            if i < n:
                c = data[i]
                i += 1
                return c
            i = n + 1
            return -1

        base = self.ibase
        c = get()
        neg = False
        while c in SPACES:
            c = get()
        if c == 95 or c == 45:  # '_' or '-'
            neg = True
            c = get()
        elif c == 43:
            c = get()
        while c in SPACES:
            c = get()
        result = 0
        dv = DIGIT_VAL
        while c in dv:
            result = result * base + dv[c]
            c = get()
        decimal = 0
        frac = 0
        if c == 46:
            build = 0
            divisor = 1
            while True:
                c = get()
                if c in dv:
                    build = build * base + dv[c]
                    divisor *= base
                    decimal += 1
                else:
                    break
            frac = build * p10(decimal) // divisor
        mag = result * p10(decimal) + frac
        if c == -1:
            st.pos = n
        else:
            st.pos = i - 1
        if neg and mag != 0:
            return Num(True, mag, decimal)
        return Num(False, mag, decimal)

    @staticmethod
    def read_string(st):
        data = st.data
        n = len(data)
        i = st.pos
        depth = 1
        start = i
        while i < n:
            c = data[i]
            if c == 93:
                depth -= 1
                if depth == 0:
                    st.pos = i + 1
                    return data[start:i]
            elif c == 91:
                depth += 1
            i += 1
        st.pos = n
        return data[start:n]

    # -- stack ops -----------------------------------------------------------
    def binop(self, fn):
        b = self.pop()
        if b is None:
            return
        a = self.pop()
        if a is None:
            self.stack.append(b)
            return
        if isinstance(a, Num) and isinstance(b, Num):
            r = fn(a, b)
            if r is None:
                self.stack.append(a)
                self.stack.append(b)
            else:
                self.stack.append(r)
        else:
            err("non-numeric value")
            self.stack.append(a)
            self.stack.append(b)

    def cmpop(self):
        b = self.pop()
        if b is None:
            return 0
        a = self.pop()
        if a is None:
            self.stack.append(b)
            return 0
        if not (isinstance(a, Num) and isinstance(b, Num)):
            err("non-numeric value")
            self.stack.append(a)
            self.stack.append(b)
            return 0
        return bc_compare(b, a)

    def rotate(self, n):
        st = self.stack
        if n == 0 or not st:
            return
        if n > 0:
            k = min(n, len(st))
            if k <= 1:
                return
            v = st.pop(-k)
            st.append(v)
        else:
            k = min(-n, len(st))
            if k <= 1:
                return
            v = st.pop()
            st.insert(len(st) - k + 1, v)

    # -- macro execution -----------------------------------------------------
    def exec_value(self, v):
        if isinstance(v, Num):
            self.stack.append(v)
            return
        frames = self.frames
        f = frames[-1]
        if not f.top:
            st = f.st
            data = st.data
            n = len(data)
            i = st.pos
            while i < n and data[i] in (32, 9, 10, 35):
                if data[i] == 35:
                    i += 1
                    while i < n:
                        i += 1
                        if data[i - 1] == 10:
                            break
                else:
                    i += 1
            st.pos = i
            if i >= n:
                f.st = Stream(v)
                f.levels += 1
                f.nc = 0
                return
        frames.append(Frame(Stream(v), 1))

    def depth(self):
        return sum(fr.levels for fr in self.frames)

    def unwind(self, u):
        frames = self.frames
        while u > 0 and len(frames) > 1:
            u -= frames.pop().levels

    # -- main loop -------------------------------------------------------------
    def run(self, stream):
        saved = self.frames
        self.frames = frames = [Frame(stream, 0, True)]
        try:
            self._loop(frames)
        finally:
            self.frames = saved

    def _loop(self, frames):
        stack = self.stack
        regs = self.regs
        while True:
            f = frames[-1]
            st = f.st
            data = st.data
            pos = st.pos
            if pos >= len(data):
                if len(frames) == 1:
                    return
                frames.pop()
                continue
            c = data[pos]
            st.pos = pos + 1
            negcmp = f.nc
            f.nc = 0

            if c == 32 or c == 10 or c == 9:
                continue
            if c in NUM_START:
                st.pos = pos
                stack.append(self.read_number(st))
                continue
            if c == 91:  # [
                stack.append(self.read_string(st))
                continue

            # commands that take a register name
            if c in REG_CMDS:
                if st.pos >= len(data):
                    err("unexpected EOF")
                    st.pos = len(data)
                    continue
                r = data[st.pos]
                st.pos += 1
                self.reg_cmd(c, r, negcmp)
                continue

            if c == 35:  # '#'
                i = data.find(b"\n", st.pos)
                st.pos = len(data) if i < 0 else i + 1
                continue
            if c == 33:  # '!'
                if st.pos < len(data) and data[st.pos] in (60, 61, 62):
                    f.nc = 1
                    continue
                # system command: not supported; skip the rest of the line
                i = data.find(b"\n", st.pos)
                st.pos = len(data) if i < 0 else i + 1
                continue

            h = SIMPLE.get(c)
            if h is not None:
                h(self)
                continue
            if c == 120:  # x
                v = self.pop()
                if v is not None:
                    self.exec_value(v)
                continue
            if c == 63:  # ?
                sst = self.get_stdin()
                sd = sst.data
                i = sd.find(b"\n", sst.pos)
                if i < 0:
                    line = sd[sst.pos:]
                    sst.pos = len(sd)
                else:
                    line = sd[sst.pos:i]
                    sst.pos = i + 1
                self.exec_value(line)
                continue
            if c == 113:  # q
                if self.depth() <= 1:
                    raise Quit()
                self.unwind(2)
                continue
            if c == 81:  # Q
                v = self.pop()
                if v is None:
                    continue
                if not isinstance(v, Num):
                    err("Q command requires a number >= 1")
                    continue
                n = num2int(v)
                if n <= 0:
                    err("Q command requires a number >= 1")
                    continue
                if n > self.depth():
                    self.unwind(1 << 62)
                    err("Q command argument exceeded string execution depth")
                else:
                    self.unwind(n)
                continue
            err("%04o unimplemented" % c)

    def reg_cmd(self, c, r, negcmp):
        stack = self.stack
        regs = self.regs
        if c == 115:  # s
            v = self.pop()
            if v is None:
                return
            lst = regs.get(r)
            if not lst:
                regs[r] = [[v, {}]]
            else:
                lst[-1][0] = v
        elif c == 108:  # l
            lst = regs.get(r)
            if not lst or lst[-1][0] is None:
                err("register '%c' (0%o) is empty" % (r, r))
                return
            stack.append(lst[-1][0])
        elif c == 83:  # S
            v = self.pop()
            if v is None:
                return
            regs.setdefault(r, []).append([v, {}])
        elif c == 76:  # L
            lst = regs.get(r)
            if not lst or lst[-1][0] is None:
                err("stack register '%c' (0%o) is empty" % (r, r))
                return
            stack.append(lst.pop()[0])
        elif c == 58:  # :
            v = self.pop()
            if v is None:
                return
            idx = -1
            if isinstance(v, Num):
                idx = num2int(v)
            val = self.pop()
            if val is None:
                return
            if idx < 0:
                err("array index must be a nonnegative integer")
                return
            lst = regs.get(r)
            if not lst:
                lst = regs[r] = [[None, {}]]
            lst[-1][1][idx] = val
        elif c == 59:  # ;
            v = self.pop()
            if v is None:
                return
            idx = -1
            if isinstance(v, Num):
                idx = num2int(v)
            if idx < 0:
                err("array index must be a nonnegative integer")
                return
            lst = regs.get(r)
            if lst:
                stack.append(lst[-1][1].get(idx, ZERO))
            else:
                stack.append(ZERO)
        else:
            cmp = self.cmpop()
            if c == 60:
                cond = cmp < 0
            elif c == 61:
                cond = cmp == 0
            else:
                cond = cmp > 0
            if negcmp:
                cond = not cond
            if cond:
                lst = regs.get(r)
                if not lst or lst[-1][0] is None:
                    err("register '%c' (0%o) is empty" % (r, r))
                    return
                self.exec_value(lst[-1][0])


REG_CMDS = set(b"slSL:;<=>")


# -- simple commands -----------------------------------------------------------

def c_p(dc):
    if not dc.stack:
        err("stack empty")
        return
    dc.print_val(dc.stack[-1], True)


def c_n(dc):
    v = dc.pop()
    if v is not None:
        dc.print_val(v, False)


def c_P(dc):
    v = dc.pop()
    if v is None:
        return
    if isinstance(v, Num):
        ip = int_part(v)
        if ip == 0:
            dc.write(b"\x00")
        else:
            dc.write(ip.to_bytes((ip.bit_length() + 7) // 8, "big"))
    else:
        dc.write(v)


def c_f(dc):
    for v in reversed(dc.stack):
        dc.print_val(v, True)


def c_add(dc):
    dc.binop(lambda a, b: bc_add(a, b))


def c_sub(dc):
    dc.binop(lambda a, b: bc_sub(a, b))


def c_mul(dc):
    k = dc.scale
    dc.binop(lambda a, b: bc_multiply(a, b, k))


def c_div(dc):
    k = dc.scale

    def op(a, b):
        r = bc_divide(a, b, k)
        if r is None:
            err("divide by zero")
        return r
    dc.binop(op)


def c_rem(dc):
    k = dc.scale

    def op(a, b):
        r = bc_modulo(a, b, k)
        if r is None:
            err("remainder by zero")
        return r
    dc.binop(op)


def c_divrem(dc):
    b = dc.pop()
    if b is None:
        return
    a = dc.pop()
    if a is None:
        dc.stack.append(b)
        return
    if isinstance(a, Num) and isinstance(b, Num):
        r = bc_divmod(a, b, dc.scale)
        if r is None:
            err("divide by zero")
            dc.stack.append(a)
            dc.stack.append(b)
        else:
            dc.stack.append(r[0])
            dc.stack.append(r[1])
    else:
        err("non-numeric value")
        dc.stack.append(a)
        dc.stack.append(b)


def c_exp(dc):
    k = dc.scale
    dc.binop(lambda a, b: bc_raise(a, b, k))


def c_modexp(dc):
    st = dc.stack
    c = dc.pop()
    if c is None:
        return
    b = dc.pop()
    if b is None:
        st.append(c)
        return
    a = dc.pop()
    if a is None:
        st.append(b)
        st.append(c)
        return
    if isinstance(a, Num) and isinstance(b, Num) and isinstance(c, Num):
        r = bc_raisemod(a, b, c, dc.scale)
        if r is None:
            if c.mag == 0:
                err("remainder by zero")
            st.append(a)
            st.append(b)
            st.append(c)
        else:
            st.append(r)
    else:
        err("non-numeric value")
        st.append(a)
        st.append(b)
        st.append(c)


def c_sqrt(dc):
    v = dc.pop()
    if v is None:
        return
    if not isinstance(v, Num):
        err("square root of nonnumeric attempted")
        dc.stack.append(v)
        return
    r = bc_sqrt(v, dc.scale)
    if r is None:
        err("square root of negative number")
        dc.stack.append(v)
    else:
        dc.stack.append(r)


def c_clear(dc):
    del dc.stack[:]


def c_dup(dc):
    if not dc.stack:
        err("stack empty")
        return
    dc.stack.append(dc.stack[-1])


def c_swap(dc):
    v = dc.pop()
    if v is None:
        return
    if dc.stack:
        w = dc.stack.pop()
        dc.stack.append(v)
        dc.stack.append(w)
    else:
        err("stack empty")
        dc.stack.append(v)


def c_rot(dc):
    v = dc.pop()
    if v is None:
        return
    if not isinstance(v, Num):
        err("non-numeric value")
        return
    dc.rotate(num2int(v))


def c_ibase(dc):
    v = dc.pop()
    if v is None:
        return
    t = 0
    if isinstance(v, Num):
        t = num2int(v)
    if not (2 <= t <= 16):
        err("input base must be a number between 2 and 16 (inclusive)")
    else:
        dc.ibase = t


def c_obase(dc):
    v = dc.pop()
    if v is None:
        return
    t = 0
    if isinstance(v, Num):
        t = num2int(v)
    if not (2 <= t):
        err("output base must be a number greater than 1")
    else:
        dc.obase = t


def c_scale(dc):
    v = dc.pop()
    if v is None:
        return
    t = -1
    if isinstance(v, Num):
        t = num2int(v)
    if t < 0:
        err("scale must be a nonnegative number")
    else:
        dc.scale = t


def c_I(dc):
    dc.stack.append(int2num(dc.ibase))


def c_O(dc):
    dc.stack.append(int2num(dc.obase))


def c_K(dc):
    dc.stack.append(int2num(dc.scale))


def c_a(dc):
    v = dc.pop()
    if v is None:
        return
    if isinstance(v, Num):
        dc.stack.append(bytes([num2int(v) & 0xFF]))
    else:
        dc.stack.append(v[:1] if v else b"\x00")


def c_Z(dc):
    v = dc.pop()
    if v is None:
        return
    if isinstance(v, Num):
        n = len(str(v.mag)) if v.mag else 1
    else:
        n = len(v)
    dc.stack.append(int2num(n))


def c_X(dc):
    v = dc.pop()
    if v is None:
        return
    if isinstance(v, Num):
        dc.stack.append(int2num(v.scale))
    else:
        dc.stack.append(ZERO)


def c_z(dc):
    dc.stack.append(int2num(len(dc.stack)))


SIMPLE = {
    ord("p"): c_p,
    ord("n"): c_n,
    ord("P"): c_P,
    ord("f"): c_f,
    ord("+"): c_add,
    ord("-"): c_sub,
    ord("*"): c_mul,
    ord("/"): c_div,
    ord("%"): c_rem,
    ord("~"): c_divrem,
    ord("^"): c_exp,
    ord("|"): c_modexp,
    ord("v"): c_sqrt,
    ord("c"): c_clear,
    ord("d"): c_dup,
    ord("r"): c_swap,
    ord("R"): c_rot,
    ord("i"): c_ibase,
    ord("o"): c_obase,
    ord("k"): c_scale,
    ord("I"): c_I,
    ord("O"): c_O,
    ord("K"): c_K,
    ord("a"): c_a,
    ord("Z"): c_Z,
    ord("X"): c_X,
    ord("z"): c_z,
}


# ---------------------------------------------------------------------------
# command line
# ---------------------------------------------------------------------------

USAGE = (
    "Usage: %s [OPTION] [file ...]\n"
    "  -e, --expression=EXPR    evaluate expression\n"
    "  -f, --file=FILE          evaluate contents of file\n"
    "  -h, --help               display this help and exit\n"
    "  -V, --version            output version information and exit\n"
    "\n"
    "Email bug reports to:  bug-dc@gnu.org .\n"
)

VERSION = (
    "dc (GNU bc 1.07.1) 1.4.1\n"
    "\n"
    "Copyright 1994, 1997, 1998, 2000, 2001, 2003-2006, 2008, 2010, 2012-2017 "
    "Free Software Foundation, Inc.\n"
    "This is free software; see the source for copying conditions.  There is NO\n"
    "warranty; not even for MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE,\n"
    "to the extent permitted by law.\n"
)

LONGOPTS = [("expression", True, "e"), ("file", True, "f"),
            ("help", False, "h"), ("version", False, "V")]


class Exit(Exception):
    def __init__(self, code):
        Exception.__init__(self)
        self.code = code


def to_bytes_arg(s):
    try:
        return os.fsencode(s)
    except Exception:
        return s.encode("utf-8", "surrogateescape")


def main(argv):
    dc = DC()
    state = {"did_eval": False}

    def usage_fail():
        sys.stderr.write(USAGE % PROG)
        raise Exit(1)

    def do_opt(ch, arg):
        if ch == "e":
            dc.run(Stream(to_bytes_arg(arg)))
            state["did_eval"] = True
        elif ch == "f":
            try_file(arg)
            state["did_eval"] = True
        elif ch == "h":
            dc.write((USAGE % PROG).encode())
            raise Exit(0)
        elif ch == "V":
            dc.write(VERSION.encode())
            raise Exit(0)

    def try_file(name):
        if name == "-":
            dc.run(dc.get_stdin())
            return
        try:
            with open(name, "rb") as fh:
                data = fh.read()
        except (IOError, OSError):
            err("Could not open file %s" % name)
            raise Exit(1)
        dc.run(Stream(data))

    try:
        try:
            files = []
            i = 0
            n = len(argv)
            while i < n:
                a = argv[i]
                if a == "--":
                    files.extend(argv[i + 1:])
                    break
                if a.startswith("--"):
                    body = a[2:]
                    if "=" in body:
                        name, val = body.split("=", 1)
                        has_val = True
                    else:
                        name, val, has_val = body, None, False
                    exact = [o for o in LONGOPTS if o[0] == name]
                    cands = exact or [o for o in LONGOPTS if o[0].startswith(name)]
                    if len(cands) != 1:
                        if cands:
                            err("option '--%s' is ambiguous" % name)
                        else:
                            err("unrecognized option '--%s'" % name)
                        usage_fail()
                    oname, needs, ch = cands[0]
                    if needs:
                        if not has_val:
                            if i + 1 >= n:
                                err("option '--%s' requires an argument" % oname)
                                usage_fail()
                            i += 1
                            val = argv[i]
                        do_opt(ch, val)
                    else:
                        if has_val:
                            err("option '--%s' doesn't allow an argument" % oname)
                            usage_fail()
                        do_opt(ch, None)
                    i += 1
                    continue
                if a.startswith("-") and a != "-":
                    j = 1
                    while j < len(a):
                        ch = a[j]
                        if ch in "hV":
                            do_opt(ch, None)
                            j += 1
                        elif ch in "ef":
                            rest = a[j + 1:]
                            if rest:
                                val = rest
                            else:
                                if i + 1 >= n:
                                    err("option requires an argument -- '%s'" % ch)
                                    usage_fail()
                                i += 1
                                val = argv[i]
                            do_opt(ch, val)
                            break
                        else:
                            err("invalid option -- '%s'" % ch)
                            usage_fail()
                    i += 1
                    continue
                files.append(a)
                i += 1

            for name in files:
                try_file(name)
                state["did_eval"] = True
            if not state["did_eval"]:
                dc.run(dc.get_stdin())
        except Quit:
            pass
        code = 0
    except Exit as e:
        code = e.code
    dc.flush()
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
