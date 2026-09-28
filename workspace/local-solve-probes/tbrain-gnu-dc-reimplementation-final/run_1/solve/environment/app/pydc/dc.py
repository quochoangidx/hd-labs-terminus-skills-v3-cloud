"""pydc: a GNU dc 1.4.1 replacement in pure Python.

Usage: python3 /app/pydc/dc.py [OPTION] [FILE]...
"""

import os
import sys

try:
    sys.set_int_max_str_digits(0)
except AttributeError:  # pragma: no cover
    pass

EOF = -1
LINE_LEN = 70
HEXDIGITS = "0123456789ABCDEF"
WS = b" \t\n"


# ---------------------------------------------------------------------------
# Numbers (modelled on GNU bc's number.c: sign, magnitude, scale)
# ---------------------------------------------------------------------------

class Num(object):
    __slots__ = ("neg", "mag", "scale")

    def __init__(self, neg, mag, scale):
        self.neg = neg
        self.mag = mag
        self.scale = scale


def P10(n):
    return 10 ** n


def mk_int(v):
    if v < 0:
        return Num(True, -v, 0)
    return Num(False, v, 0)


ZERO = Num(False, 0, 0)
ONE = Num(False, 1, 0)
TWO = Num(False, 2, 0)


def is_zero(n):
    return n.mag == 0


def rescale(n, s):
    """Magnitude of n expressed with s fraction digits (truncating)."""
    if s >= n.scale:
        return n.mag * P10(s - n.scale)
    return n.mag // P10(n.scale - s)


def bc_add(a, b, scale_min=0):
    rs = max(scale_min, a.scale, b.scale)
    am = a.mag * P10(rs - a.scale)
    bm = b.mag * P10(rs - b.scale)
    if a.neg == b.neg:
        return Num(a.neg, am + bm, rs)
    if am == bm:
        return Num(False, 0, rs)
    if am > bm:
        return Num(a.neg, am - bm, rs)
    return Num(b.neg, bm - am, rs)


def bc_sub(a, b, scale_min=0):
    return bc_add(a, Num(not b.neg, b.mag, b.scale), scale_min)


def bc_mul(a, b, scale):
    full = a.scale + b.scale
    ps = min(full, max(scale, a.scale, b.scale))
    m = a.mag * b.mag
    if full > ps:
        m //= P10(full - ps)
    neg = a.neg != b.neg
    if m == 0:
        neg = False
    return Num(neg, m, ps)


def bc_div(a, b, scale):
    if b.mag == 0:
        return None
    num = a.mag * P10(b.scale + scale)
    den = b.mag * P10(a.scale)
    q = num // den
    neg = a.neg != b.neg
    if q == 0:
        neg = False
    return Num(neg, q, scale)


def bc_divmod(a, b, scale):
    if b.mag == 0:
        return None
    rscale = max(a.scale, b.scale + scale)
    q = bc_div(a, b, scale)
    t = bc_mul(q, b, rscale)
    r = bc_sub(a, t, rscale)
    return q, r


def bc_mod(a, b, scale):
    res = bc_divmod(a, b, scale)
    if res is None:
        return None
    return res[1]


def bc_compare(a, b):
    if a.neg != b.neg:
        return 1 if not a.neg else -1
    s = max(a.scale, b.scale)
    am = a.mag * P10(s - a.scale)
    bm = b.mag * P10(s - b.scale)
    if am == bm:
        return 0
    r = 1 if am > bm else -1
    return -r if a.neg else r


def num2long(n):
    ip = n.mag // P10(n.scale)
    if ip >= (1 << 63):
        ip = 0
    return -ip if n.neg else ip


def n_len(n):
    ip = n.mag // P10(n.scale)
    return len(str(ip)) if ip else 1


def bc_raise(a, b, scale):
    if b.scale != 0:
        warn("runtime warning: non-zero scale in exponent")
    e = num2long(b)
    if e == 0 and (b.mag // P10(b.scale)) != 0:
        err("exponent too large in raise")
        return None
    if e == 0:
        return Num(False, 1, 0)
    if e < 0:
        neg_e = True
        e = -e
        rscale = scale
    else:
        neg_e = False
        rscale = min(a.scale * e, max(scale, a.scale))
    m = a.mag ** e
    s = a.scale * e
    if m == 0:
        rneg = a.neg if e == 1 else False
    else:
        rneg = a.neg and (e & 1) == 1
    temp = Num(rneg, m, s)
    if neg_e:
        r = bc_div(ONE, temp, rscale)
        if r is None:
            return Num(False, 0, 0)
        return r
    if temp.scale > rscale:
        temp = Num(temp.neg, temp.mag // P10(temp.scale - rscale), rscale)
    return temp


def bc_raisemod(base, expo, mod, scale):
    if mod.mag == 0:
        return None
    if expo.neg:
        return None
    power = base
    exponent = expo
    temp = ONE
    if exponent.scale != 0:
        exponent = bc_div(exponent, ONE, 0)
    rscale = max(scale, base.scale)
    if bc_compare(mod, ONE) == 0:
        return Num(False, 0, scale)
    while exponent.mag != 0:
        exponent, parity = bc_divmod(exponent, TWO, 0)
        if parity.mag != 0:
            temp = bc_mul(temp, power, rscale)
            temp = bc_mod(temp, mod, scale)
        power = bc_mul(power, power, rscale)
        power = bc_mod(power, mod, scale)
    return temp


def is_near_zero(n, scale):
    if scale > n.scale:
        scale = n.scale
    v = n.mag // P10(n.scale - scale)
    return v == 0 or v == 1


def bc_sqrt(n, scale):
    c = bc_compare(n, ZERO)
    if c < 0:
        return None
    if c == 0:
        return Num(False, 0, 0)
    c = bc_compare(n, ONE)
    if c == 0:
        return Num(False, 1, 0)
    rscale = max(scale, n.scale)
    point5 = Num(False, 5, 1)
    if c < 0:
        guess = ONE
        cscale = n.scale
    else:
        guess = Num(False, P10(n_len(n) // 2), 0)
        cscale = 3
    while True:
        guess1 = guess
        guess = bc_div(n, guess, cscale)
        guess = bc_add(guess, guess1, 0)
        guess = bc_mul(guess, point5, cscale)
        diff = bc_sub(guess, guess1, cscale + 1)
        if is_near_zero(diff, cscale):
            if cscale < rscale + 1:
                cscale = min(cscale * 3, rscale + 1)
            else:
                break
    return bc_div(guess, ONE, rscale)


def num2int(n):
    ip = n.mag // P10(n.scale)
    if ip == 0 and n.mag != 0:
        return -1
    if ip >= (1 << 31):
        return -1
    return -ip if n.neg else ip


def num_digits(n):
    if n.mag == 0:
        return 1
    return len(str(n.mag))


def num_to_str(n, obase):
    out = []
    if n.neg:
        out.append("-")
    if n.mag == 0:
        out.append("0")
        return "".join(out)
    p = P10(n.scale)
    ip, fp = divmod(n.mag, p)
    if obase == 10:
        if ip:
            out.append(str(ip))
        if n.scale > 0:
            out.append(".")
            out.append(str(fp).zfill(n.scale))
        return "".join(out)
    digits = []
    while ip:
        ip, d = divmod(ip, obase)
        digits.append(d)
    digits.reverse()
    w = len(str(obase - 1))
    if obase <= 16:
        out.append("".join(HEXDIGITS[d] for d in digits))
    else:
        for d in digits:
            out.append(" " + str(d).zfill(w))
    if n.scale > 0:
        out.append(".")
        t = 1
        first = True
        while t < p:
            fp *= obase
            d, fp = divmod(fp, p)
            if obase <= 16:
                out.append(HEXDIGITS[d])
            else:
                out.append(("" if first else " ") + str(d).zfill(w))
                first = False
            t *= obase
    return "".join(out)


def split_lines(s):
    n = LINE_LEN - 1
    if len(s) <= n:
        return s
    parts = [s[i:i + n] for i in range(0, len(s), n)]
    return "\\\n".join(parts)


# ---------------------------------------------------------------------------
# Diagnostics
# ---------------------------------------------------------------------------

def err(msg):
    try:
        sys.stdout.flush()
        sys.stderr.write("dc: %s\n" % msg)
        sys.stderr.flush()
    except Exception:
        pass


def warn(msg):
    err(msg)


# ---------------------------------------------------------------------------
# Input sources
# ---------------------------------------------------------------------------

class StdinStream(object):
    def __init__(self):
        self.data = None
        self.pos = 0
        self.pushback = []

    def _load(self):
        if self.data is None:
            try:
                self.data = sys.stdin.buffer.read()
            except Exception:
                self.data = b""

    def getc(self):
        if self.pushback:
            return self.pushback.pop()
        self._load()
        p = self.pos
        if p < len(self.data):
            self.pos = p + 1
            return self.data[p]
        return EOF

    def ungetc(self, c):
        if c != EOF:
            self.pushback.append(c)

    def readline(self):
        buf = bytearray()
        while True:
            c = self.getc()
            if c == EOF or c == 10:
                break
            buf.append(c)
        return bytes(buf)


class StrReader(object):
    __slots__ = ("data", "pos", "levels")

    def __init__(self, data, levels):
        self.data = data
        self.pos = 0
        self.levels = levels

    def getcmd(self):
        p = self.pos
        if p < len(self.data):
            self.pos = p + 1
            return self.data[p]
        return EOF

    def getc(self):
        p = self.pos
        if p < len(self.data):
            self.pos = p + 1
            return self.data[p]
        self.pos = p + 1
        return EOF

    def ungetc(self, c):
        self.pos -= 1

    def at_end(self):
        d = self.data
        p = self.pos
        n = len(d)
        while p < n:
            if d[p] not in WS:
                return False
            p += 1
        return True


class StdinTopReader(object):
    """Top-level reader of commands from standard input, mimicking the
    one-character lookahead GNU dc keeps while reading a file."""

    def __init__(self, dc):
        self.dc = dc
        self.levels = 0
        self.pending = None

    def getcmd(self):
        S = self.dc.stdin
        if self.pending is not None:
            c = self.pending
            self.pending = None
        else:
            c = S.getc()
        if c == EOF:
            self.dc.lookahead = EOF
            return EOF
        peek = S.getc()
        self.pending = peek
        self.dc.lookahead = peek
        return c

    def getc(self):
        if self.pending is not None:
            c = self.pending
            self.pending = None
            return c
        return self.dc.stdin.getc()

    def ungetc(self, c):
        self.pending = c

    def at_end(self):
        return False


class Quit(Exception):
    pass


# ---------------------------------------------------------------------------
# Interpreter
# ---------------------------------------------------------------------------

class DC(object):
    def __init__(self):
        self.stack = []
        self.regs = {}
        self.scale = 0
        self.ibase = 10
        self.obase = 10
        self.frames = []
        self.depth = 0
        self.stdin = StdinStream()
        self.lookahead = EOF
        self.out = sys.stdout.buffer

    # -- output ----------------------------------------------------------
    def write(self, b):
        self.out.write(b)

    def print_value(self, v, newline):
        if isinstance(v, Num):
            s = split_lines(num_to_str(v, self.obase))
            if newline:
                s += "\n"
            self.write(s.encode("ascii"))
        else:
            if newline:
                self.write(v + b"\n")
            else:
                self.write(v)

    # -- registers -------------------------------------------------------
    def reg_stack(self, r):
        st = self.regs.get(r)
        if st is None:
            st = []
            self.regs[r] = st
        return st

    # -- macros ----------------------------------------------------------
    def exec_macro(self, s):
        frames = self.frames
        cur = frames[-1]
        levels = 1
        if cur.levels > 0 and cur.at_end():
            frames.pop()
            self.depth -= cur.levels
            levels += cur.levels
        frames.append(StrReader(s, levels))
        self.depth += levels

    def unwind(self, m):
        frames = self.frames
        while m > 0 and frames and frames[-1].levels > 0:
            f = frames.pop()
            self.depth -= f.levels
            m -= f.levels

    def run(self, reader):
        self.frames = [reader]
        self.depth = 0
        frames = self.frames
        while frames:
            r = frames[-1]
            c = r.getcmd()
            if c == EOF:
                frames.pop()
                self.depth -= r.levels
                continue
            self.dispatch(c, r)

    # -- helpers ---------------------------------------------------------
    def pop(self):
        if not self.stack:
            err("stack empty")
            return None
        return self.stack.pop()

    def binop(self, f):
        st = self.stack
        if len(st) < 2:
            err("stack empty")
            return
        a = st[-2]
        b = st[-1]
        if not (isinstance(a, Num) and isinstance(b, Num)):
            err("non-numeric value")
            return
        r = f(a, b)
        if r is None:
            return
        del st[-2:]
        if isinstance(r, tuple):
            st.append(r[0])
            st.append(r[1])
        else:
            st.append(r)

    def op_div(self, a, b):
        r = bc_div(a, b, self.scale)
        if r is None:
            err("divide by zero")
        return r

    def op_mod(self, a, b):
        r = bc_mod(a, b, self.scale)
        if r is None:
            err("remainder by zero")
        return r

    def op_divmod(self, a, b):
        r = bc_divmod(a, b, self.scale)
        if r is None:
            err("divide by zero")
        return r

    def op_pow(self, a, b):
        return bc_raise(a, b, self.scale)

    def parse_number(self, c, r):
        ibase = self.ibase
        neg = False
        if c == 95:  # '_'
            neg = True
            c = r.getc()
        ip = 0
        while True:
            if 48 <= c <= 57:
                d = c - 48
            elif 65 <= c <= 70:
                d = c - 55
            else:
                break
            ip = ip * ibase + d
            c = r.getc()
        if c == 46:  # '.'
            build = 0
            div = 1
            n = 0
            while True:
                c = r.getc()
                if 48 <= c <= 57:
                    d = c - 48
                elif 65 <= c <= 70:
                    d = c - 55
                else:
                    break
                build = build * ibase + d
                div *= ibase
                n += 1
            fm = (build * P10(n)) // div
            mag = ip * P10(n) + fm
            scale = n
        else:
            mag = ip
            scale = 0
        r.ungetc(c)
        if mag == 0:
            neg = False
        self.stack.append(Num(neg, mag, scale))

    def cond(self, op, negate, reg):
        if reg == EOF:
            err("unexpected end of input")
            return
        st = self.stack
        if len(st) < 2:
            err("stack empty")
            return
        top = st[-1]
        sec = st[-2]
        if not (isinstance(top, Num) and isinstance(sec, Num)):
            err("non-numeric value")
            return
        del st[-2:]
        c = bc_compare(top, sec)
        if op == 60:
            res = c < 0
        elif op == 61:
            res = c == 0
        else:
            res = c > 0
        if negate:
            res = not res
        if res:
            v = self.reg_value(reg)
            if isinstance(v, Num):
                st.append(v)
            else:
                self.exec_macro(v)

    def reg_value(self, reg):
        rs = self.regs.get(reg)
        if not rs or rs[-1][0] is None:
            return ZERO
        return rs[-1][0]

    # -- command dispatch ------------------------------------------------
    def dispatch(self, c, r):
        st = self.stack
        if c == 32 or c == 9 or c == 10:
            return
        if (48 <= c <= 57) or (65 <= c <= 70) or c == 95 or c == 46:
            self.parse_number(c, r)
            return
        if c == 91:  # '['
            depth = 1
            buf = bytearray()
            while True:
                ch = r.getc()
                if ch == EOF:
                    break
                if ch == 93:
                    depth -= 1
                    if depth == 0:
                        break
                elif ch == 91:
                    depth += 1
                buf.append(ch)
            st.append(bytes(buf))
            return
        if c == 35:  # '#'
            while True:
                ch = r.getc()
                if ch == EOF or ch == 10:
                    break
            return
        if c == 112:  # p
            if not st:
                err("stack empty")
                return
            self.print_value(st[-1], True)
            return
        if c == 110:  # n
            v = self.pop()
            if v is not None:
                self.print_value(v, False)
            return
        if c == 80:  # P
            v = self.pop()
            if v is None:
                return
            if isinstance(v, Num):
                ip = v.mag // P10(v.scale)
                bs = bytearray()
                while True:
                    ip, d = divmod(ip, 256)
                    bs.append(d)
                    if ip == 0:
                        break
                bs.reverse()
                self.write(bytes(bs))
            else:
                self.write(v)
            return
        if c == 102:  # f
            for v in reversed(st):
                self.print_value(v, True)
            return
        if c == 43:  # +
            self.binop(lambda a, b: bc_add(a, b, 0))
            return
        if c == 45:  # -
            self.binop(lambda a, b: bc_sub(a, b, 0))
            return
        if c == 42:  # *
            self.binop(lambda a, b: bc_mul(a, b, self.scale))
            return
        if c == 47:  # /
            self.binop(self.op_div)
            return
        if c == 37:  # %
            self.binop(self.op_mod)
            return
        if c == 126:  # ~
            self.binop(self.op_divmod)
            return
        if c == 94:  # ^
            self.binop(self.op_pow)
            return
        if c == 124:  # |
            if len(st) < 3:
                err("stack empty")
                return
            a, b, m = st[-3], st[-2], st[-1]
            if not (isinstance(a, Num) and isinstance(b, Num) and isinstance(m, Num)):
                err("non-numeric value")
                return
            res = bc_raisemod(a, b, m, self.scale)
            if res is None:
                if m.mag == 0:
                    err("remainder by zero")
                else:
                    err("negative exponent")
                return
            del st[-3:]
            st.append(res)
            return
        if c == 118:  # v
            v = self.pop()
            if v is None:
                return
            if not isinstance(v, Num):
                err("square root of nonnumeric attempted")
                return
            res = bc_sqrt(v, self.scale)
            if res is None:
                err("square root of negative number")
                return
            st.append(res)
            return
        if c == 99:  # c
            del st[:]
            return
        if c == 100:  # d
            if not st:
                err("stack empty")
                return
            st.append(st[-1])
            return
        if c == 114:  # r
            if len(st) >= 2:
                st[-1], st[-2] = st[-2], st[-1]
            else:
                err("stack empty")
            return
        if c == 82:  # R
            v = self.pop()
            if v is None:
                return
            n = num2int(v) if isinstance(v, Num) else 0
            k = abs(n)
            if k < 2 or not st:
                return
            k = min(k, len(st))
            if k < 2:
                return
            sub = st[-k:]
            if n > 0:
                st[-k:] = sub[1:] + sub[:1]
            else:
                st[-k:] = sub[-1:] + sub[:-1]
            return
        if c == 105:  # i
            v = self.pop()
            if v is None:
                return
            n = num2int(v) if isinstance(v, Num) else -1
            if 2 <= n <= 16:
                self.ibase = n
            else:
                err("input base must be a number between 2 and 16 (inclusive)")
            return
        if c == 111:  # o
            v = self.pop()
            if v is None:
                return
            n = num2int(v) if isinstance(v, Num) else -1
            if n >= 2:
                self.obase = n
            else:
                err("output base must be a number greater than 1")
            return
        if c == 107:  # k
            v = self.pop()
            if v is None:
                return
            n = num2int(v) if isinstance(v, Num) else -1
            if n >= 0:
                self.scale = n
            else:
                err("scale must be a nonnegative number")
            return
        if c == 73:  # I
            st.append(mk_int(self.ibase))
            return
        if c == 79:  # O
            st.append(mk_int(self.obase))
            return
        if c == 75:  # K
            st.append(mk_int(self.scale))
            return
        if c == 122:  # z
            st.append(mk_int(len(st)))
            return
        if c == 90:  # Z
            v = self.pop()
            if v is None:
                return
            if isinstance(v, Num):
                st.append(mk_int(num_digits(v)))
            else:
                st.append(mk_int(len(v)))
            return
        if c == 88:  # X
            v = self.pop()
            if v is None:
                return
            if isinstance(v, Num):
                st.append(mk_int(v.scale))
            else:
                st.append(ZERO)
            return
        if c == 97:  # a
            v = self.pop()
            if v is None:
                return
            if isinstance(v, Num):
                n = num2int(v)
                st.append(bytes([n & 0xFF]))
            else:
                st.append(v[:1])
            return
        if c == 120:  # x
            v = self.pop()
            if v is None:
                return
            if isinstance(v, Num):
                st.append(v)
            else:
                self.exec_macro(v)
            return
        if c == 63:  # ?
            if self.lookahead != EOF:
                self.stdin.ungetc(self.lookahead)
                self.lookahead = EOF
            line = self.stdin.readline()
            self.exec_macro(line)
            return
        if c == 113:  # q
            if self.depth <= 1:
                raise Quit()
            self.unwind(2)
            return
        if c == 81:  # Q
            v = self.pop()
            if v is None:
                return
            n = num2int(v) if isinstance(v, Num) else -1
            if n <= 0:
                err("Q command requires a number >= 1")
                return
            self.unwind(n)
            return
        if c == 60 or c == 61 or c == 62:  # < = >
            reg = r.getc()
            self.cond(c, False, reg)
            return
        if c == 33:  # !
            ch = r.getc()
            if ch == 60 or ch == 61 or ch == 62:
                reg = r.getc()
                self.cond(ch, True, reg)
                return
            # shell command: not supported; skip the rest of the line
            while ch != EOF and ch != 10:
                ch = r.getc()
            return
        if c in (115, 83, 108, 76, 58, 59):  # s S l L : ;
            reg = r.getc()
            if reg == EOF:
                err("unexpected end of input")
                return
            self.reg_cmd(c, reg)
            return
        err("'%s' (%#o) unimplemented" % (chr(c), c))

    def reg_cmd(self, c, reg):
        st = self.stack
        if c == 115:  # s
            v = self.pop()
            if v is None:
                return
            rs = self.reg_stack(reg)
            if rs:
                rs[-1][0] = v
            else:
                rs.append([v, None])
            return
        if c == 83:  # S
            v = self.pop()
            if v is None:
                return
            self.reg_stack(reg).append([v, None])
            return
        if c == 108:  # l
            st.append(self.reg_value(reg))
            return
        if c == 76:  # L
            rs = self.regs.get(reg)
            if not rs:
                err("stack register '%s' (%#o) is empty" % (chr(reg), reg))
                return
            ent = rs.pop()
            v = ent[0]
            st.append(ZERO if v is None else v)
            return
        if c == 58:  # :
            v = self.pop()
            if v is None:
                return
            idx = num2int(v) if isinstance(v, Num) else -1
            val = self.pop()
            if val is None:
                return
            if idx < 0:
                err("array index must be a nonnegative integer")
                return
            rs = self.reg_stack(reg)
            if not rs:
                rs.append([None, None])
            ent = rs[-1]
            if ent[1] is None:
                ent[1] = {}
            ent[1][idx] = val
            return
        if c == 59:  # ;
            v = self.pop()
            if v is None:
                return
            idx = num2int(v) if isinstance(v, Num) else -1
            if idx < 0:
                err("array index must be a nonnegative integer")
                return
            rs = self.regs.get(reg)
            val = ZERO
            if rs and rs[-1][1] is not None:
                val = rs[-1][1].get(idx, ZERO)
            st.append(val)
            return


def main(argv):
    exprs = []
    files = []
    i = 0
    n = len(argv)
    only_files = False
    while i < n:
        a = argv[i]
        if only_files or a == "-" or not a.startswith("-"):
            files.append(a)
            i += 1
            continue
        if a == "--":
            only_files = True
            i += 1
            continue
        if a == "-e" or a == "-f":
            if i + 1 >= n:
                err("option requires an argument -- '%s'" % a[1])
                return 1
            exprs.append((a[1], argv[i + 1]))
            i += 2
            continue
        if a.startswith("-e") or a.startswith("-f"):
            exprs.append((a[1], a[2:]))
            i += 1
            continue
        if a.startswith("--expression="):
            exprs.append(("e", a[len("--expression="):]))
            i += 1
            continue
        if a.startswith("--file="):
            exprs.append(("f", a[len("--file="):]))
            i += 1
            continue
        err("invalid option -- '%s'" % a)
        i += 1

    dc = DC()
    sources = list(exprs) + [("f", f) for f in files]
    if not sources:
        sources = [("f", "-")]
    try:
        for kind, arg in sources:
            if kind == "e":
                dc.run(StrReader(os.fsencode(arg), 0))
            else:
                if arg == "-":
                    dc.run(StdinTopReader(dc))
                else:
                    try:
                        with open(arg, "rb") as fh:
                            data = fh.read()
                    except (IOError, OSError):
                        err("Could not open file %s" % arg)
                        continue
                    dc.run(StrReader(data, 0))
    except Quit:
        pass
    try:
        sys.stdout.flush()
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
