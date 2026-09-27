"""pybc: a GNU bc 1.07.1 replacement in pure Python.

Usage: python3 /app/pybc/bc.py < program
"""

import sys
import threading

try:
    sys.set_int_max_str_digits(0)
except AttributeError:  # pragma: no cover
    pass

# ---------------------------------------------------------------------------
# Numbers: (neg, mag, scale)  value = (-1)**neg * mag / 10**scale
# The sign flag is kept separately so that bc's "negative zero" is faithful.
# ---------------------------------------------------------------------------

ZERO = (False, 0, 0)
ONE = (False, 1, 0)
POINT5 = (False, 5, 1)
INT_MAX = 2147483647
LONG_MAX = 9223372036854775807
DIM_MAX = 16777215

_P10 = [10 ** i for i in range(512)]


def p10(n):
    if n < 512:
        return _P10[n]
    return 10 ** n


class BCRuntimeError(Exception):
    pass


class HaltProgram(Exception):
    pass


class QuitProgram(Exception):
    pass


class ParseError(Exception):
    def __init__(self, msg, pos):
        Exception.__init__(self, msg)
        self.pos = pos


def int2num(i):
    if i < 0:
        return (True, -i, 0)
    return (False, i, 0)


def num2long(x):
    """Integer part with sign (C bc_num2long, without overflow handling)."""
    s = x[2]
    ip = x[1] // p10(s) if s else x[1]
    return -ip if x[0] else ip


def bc_add(a, b, smin=0):
    an, am, asc = a
    bn, bm, bsc = b
    rs = asc if asc > bsc else bsc
    if smin > rs:
        rs = smin
    if asc != rs:
        am *= p10(rs - asc)
    if bsc != rs:
        bm *= p10(rs - bsc)
    if an == bn:
        return (an, am + bm, rs)
    if am > bm:
        return (an, am - bm, rs)
    if am < bm:
        return (bn, bm - am, rs)
    return (False, 0, rs)


def bc_sub(a, b, smin=0):
    return bc_add(a, (not b[0], b[1], b[2]), smin)


def bc_mul(a, b, scale):
    asc = a[2]
    bsc = b[2]
    full = asc + bsc
    mx = asc if asc > bsc else bsc
    if scale > mx:
        mx = scale
    ps = full if full < mx else mx
    m = a[1] * b[1]
    if full != ps:
        m //= p10(full - ps)
    return ((a[0] != b[0]) and m != 0, m, ps)


def bc_div(a, b, scale):
    if b[1] == 0:
        raise BCRuntimeError("Divide by zero")
    if b[2] == 0 and b[1] == 1:
        m = a[1]
        s = a[2]
        if s > scale:
            m //= p10(s - scale)
        elif s < scale:
            m *= p10(scale - s)
        return (a[0] != b[0], m, scale)
    e = b[2] + scale - a[2]
    if e >= 0:
        q = (a[1] * p10(e)) // b[1]
    else:
        q = a[1] // (b[1] * p10(-e))
    return ((a[0] != b[0]) and q != 0, q, scale)


def bc_mod(a, b, scale):
    if b[1] == 0:
        raise BCRuntimeError("Modulo by zero")
    rscale = a[2]
    if b[2] + scale > rscale:
        rscale = b[2] + scale
    t = bc_div(a, b, scale)
    t = bc_mul(t, b, rscale)
    return bc_sub(a, t, rscale)


def bc_raise(a, b, scale):
    if b[2] != 0:
        warn("non-zero scale in exponent")
    e = num2long(b)
    if e > LONG_MAX or e < -LONG_MAX:
        raise BCRuntimeError("exponent too large in raise")
    if e == 0:
        return ONE
    if e < 0:
        neg = True
        e = -e
        rscale = scale
    else:
        neg = False
        mx = scale if scale > a[2] else a[2]
        rscale = a[2] * e
        if mx < rscale:
            rscale = mx
    m = a[1] ** e
    s = a[2] * e
    sign = a[0] and (e & 1) == 1
    if m == 0 and e > 1:
        sign = False
    if neg:
        return bc_div(ONE, (sign, m, s), rscale)
    if s > rscale:
        m //= p10(s - rscale)
        s = rscale
    return (sign, m, s)


def bc_cmp(a, b):
    if a[0] != b[0]:
        return -1 if a[0] else 1
    am, asc = a[1], a[2]
    bm, bsc = b[1], b[2]
    if asc < bsc:
        am *= p10(bsc - asc)
    elif bsc < asc:
        bm *= p10(asc - bsc)
    if am == bm:
        return 0
    c = 1 if am > bm else -1
    return -c if a[0] else c


def nlen(x):
    s = x[2]
    ip = x[1] // p10(s) if s else x[1]
    if ip == 0:
        return 1
    return len(str(ip))


def bc_length(x):
    s = x[2]
    ip = x[1] // p10(s) if s else x[1]
    if ip == 0:
        if s != 0:
            return s
        return 1
    return len(str(ip)) + s


def near_zero(x, scale):
    s = x[2]
    if scale > s:
        scale = s
    t = x[1] // p10(s - scale)
    return t <= 1


def bc_sqrt(x, scale):
    c = bc_cmp(x, ZERO)
    if c < 0:
        raise BCRuntimeError("Square root of a negative number")
    if c == 0:
        return ZERO
    c1 = bc_cmp(x, ONE)
    if c1 == 0:
        return ONE
    rscale = scale if scale > x[2] else x[2]
    if c1 < 0:
        guess = ONE
        cscale = x[2]
    else:
        e = nlen(x) // 2
        guess = (False, p10(e), 0)
        cscale = 3
    while True:
        guess1 = guess
        guess = bc_div(x, guess, cscale)
        guess = bc_add(guess, guess1, 0)
        guess = bc_mul(guess, POINT5, cscale)
        diff = bc_sub(guess, guess1, cscale + 1)
        if near_zero(diff, cscale):
            if cscale < rscale + 1:
                cscale = min(cscale * 3, rscale + 1)
            else:
                break
    return bc_div(guess, ONE, rscale)


def is_zero(x):
    return x[1] == 0


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

class Output:
    def __init__(self):
        self.buf = []
        self.size = 0
        self.col = 0

    def write(self, s):
        """Write through bc's out_char/out_schar (line splitting at 70)."""
        buf = self.buf
        if '\n' in s:
            parts = s.split('\n')
        else:
            parts = (s,)
        first = True
        for seg in parts:
            if not first:
                buf.append('\n')
                self.col = 0
            first = False
            if not seg:
                continue
            col = self.col
            n = 68 - col
            L = len(seg)
            if L <= n:
                buf.append(seg)
                self.col = col + L
            else:
                buf.append(seg[:n])
                pos = n
                while pos < L:
                    buf.append('\\\n')
                    chunk = seg[pos:pos + 68]
                    buf.append(chunk)
                    self.col = len(chunk)
                    pos += 68
        self.size += len(s)
        if self.size > 1 << 16:
            self.flush()

    def flush(self):
        if self.buf:
            data = ''.join(self.buf)
            self.buf = []
            self.size = 0
            try:
                sys.stdout.buffer.write(data.encode('latin-1', 'replace'))
            except (BrokenPipeError, OSError):
                pass
        try:
            sys.stdout.buffer.flush()
        except (BrokenPipeError, OSError):
            pass


OUT = Output()


def warn(msg):
    pass


def errmsg(msg):
    try:
        sys.stderr.write(msg + "\n")
    except Exception:
        pass


HEXDIGITS = "0123456789ABCDEF"


def int_to_base_digits(n, base):
    """Digits (most significant first) of non-negative int n in base."""
    if n < base:
        return [n]
    if n.bit_length() <= 4096:
        out = []
        while n:
            n, d = divmod(n, base)
            out.append(d)
        out.reverse()
        return out
    # divide and conquer
    k = 1
    pw = base
    # find k with base**k ~ sqrt(n)
    target = n.bit_length() // 2
    while pw.bit_length() * 2 <= target:
        pw = pw * pw
        k *= 2
    while (pw * base).bit_length() <= target:
        pw *= base
        k += 1
    hi, lo = divmod(n, pw)
    hd = int_to_base_digits(hi, base)
    ld = int_to_base_digits(lo, base)
    if len(ld) < k:
        ld = [0] * (k - len(ld)) + ld
    return hd + ld


def fmt10(x):
    neg, m, s = x
    if m == 0:
        return '-0' if neg else '0'
    d = str(m)
    if s:
        if len(d) <= s:
            r = '.' + d.zfill(s)
        else:
            r = d[:-s] + '.' + d[-s:]
    else:
        r = d
    return '-' + r if neg else r


def fmt_base(x, base):
    neg, m, s = x
    res = ['-'] if neg else []
    if m == 0:
        res.append('0')
        return ''.join(res)
    ps = p10(s)
    ip = m // ps
    fm = m - ip * ps
    width = len(str(base - 1))
    if ip:
        digs = int_to_base_digits(ip, base)
        if base <= 16:
            res.append(''.join(HEXDIGITS[d] for d in digs))
        else:
            res.append(''.join(' ' + str(d).zfill(width) for d in digs))
    if s > 0:
        res.append('.')
        frac = (False, fm, s)
        tnum = ONE
        bnum = (False, base, 0)
        pre_space = False
        while nlen(tnum) <= s:
            frac = bc_mul(frac, bnum, s)
            fd = num2long(frac)
            frac = bc_sub(frac, int2num(fd), 0)
            if base <= 16:
                res.append(HEXDIGITS[fd])
            else:
                res.append((' ' if pre_space else '') + str(fd).zfill(width))
                pre_space = True
            tnum = bc_mul(tnum, bnum, 0)
    return ''.join(res)


# ---------------------------------------------------------------------------
# Interpreter state
# ---------------------------------------------------------------------------

class State:
    __slots__ = ('scale', 'ibase', 'obase', 'last')

    def __init__(self):
        self.scale = 0
        self.ibase = 10
        self.obase = 10
        self.last = ZERO


S = State()
VARS = {}
ARRS = {}
FUNCS = {}
CB = []  # stack of constant bases for active function calls
VOID = object()
BRK = object()
CONT = object()


def fmtnum(v):
    if S.obase == 10:
        return fmt10(v)
    return fmt_base(v, S.obase)


def print_num(v):
    OUT.write(fmtnum(v))


def dval(c):
    o = ord(c)
    if o <= 57:
        return o - 48
    return o - 55


def conv_const(s, base):
    if '.' in s:
        ip, fp = s.split('.', 1)
    else:
        ip, fp = s, ''
    if base == 10:
        kd = len(ip)
        ks = len(fp)
        if kd == 1 and ks == 0:
            return (False, dval(ip), 0)
        digits = ip + fp
        if not digits.isdigit():
            digits = ''.join(c if c <= '9' else '9' for c in digits)
        return (False, int(digits) if digits else 0, ks)
    maxc = HEXDIGITS[base - 1] if base <= 16 else chr(55 + base - 1)
    build = 0
    if ip:
        first = dval(ip[0])
        if len(ip) > 1:
            cl = ''.join(c if dval(c) < base else maxc for c in ip)
            build = int(cl, base)
        else:
            build = first
    if fp:
        cl = ''.join(c if dval(c) < base else maxc for c in fp)
        n = len(cl)
        r = int(cl, base)
        fr = (r * p10(n)) // (base ** n)
        return (False, build * p10(n) + fr, n)
    return (False, build, 0)


def arr_index(v, name):
    i = num2long(v)
    if i < 0 or i >= DIM_MAX:
        raise BCRuntimeError("Array %s subscript out of bounds." % name)
    return i


def get_arr(name):
    a = ARRS.get(name)
    if a is None:
        a = {}
        ARRS[name] = a
    return a


def load_special(name):
    if name == 'scale':
        return int2num(S.scale)
    if name == 'ibase':
        return int2num(S.ibase)
    if name == 'obase':
        return int2num(S.obase)
    return S.last


def store_special(name, v):
    if name == 'last':
        S.last = v
        return
    t = num2long(v)
    toobig = t > LONG_MAX or t < -LONG_MAX
    if name == 'ibase':
        if t < 2 and not toobig:
            if t < 2:
                warn("negative ibase, set to 2")
            S.ibase = 2
        elif t > 36 or toobig:
            S.ibase = 36
        else:
            S.ibase = t
    elif name == 'obase':
        if t < 2 and not toobig:
            S.obase = 2
        elif t > INT_MAX or toobig:
            S.obase = INT_MAX
        else:
            S.obase = t
    else:
        if t > INT_MAX or toobig:
            S.scale = INT_MAX
        elif t < 0:
            S.scale = 0
        else:
            S.scale = t


def op_add(a, b):
    return bc_add(a, b)


def op_sub(a, b):
    return bc_sub(a, b)


def op_mul(a, b):
    return bc_mul(a, b, S.scale)


def op_div(a, b):
    return bc_div(a, b, S.scale)


def op_mod(a, b):
    return bc_mod(a, b, S.scale)


def op_pow(a, b):
    return bc_raise(a, b, S.scale)


OPFUNCS = {'+': op_add, '-': op_sub, '*': op_mul, '/': op_div,
           '%': op_mod, '^': op_pow}


class Func:
    __slots__ = ('name', 'params', 'autos', 'body', 'void')

    def __init__(self, name, params, autos, body, void):
        self.name = name
        self.params = params
        self.autos = autos
        self.body = body
        self.void = void


_MISSING = object()


def call_function(name, argvals):
    fn = FUNCS.get(name)
    if fn is None:
        raise BCRuntimeError("Function %s not defined." % name)
    params = fn.params
    if len(params) != len(argvals):
        raise BCRuntimeError("Parameter number mismatch")
    for (pname, kind), (akind, _) in zip(params, argvals):
        if (kind == 'val') != (akind == 'val'):
            raise BCRuntimeError("Parameter type mismatch, parameter %s." % pname)
    saved = []
    try:
        for idx in range(len(params) - 1, -1, -1):
            pname, kind = params[idx]
            akind, val = argvals[idx]
            if kind == 'val':
                saved.append((0, pname, VARS.get(pname, _MISSING)))
                VARS[pname] = val
            else:
                src = get_arr(val)
                saved.append((1, pname, ARRS.get(pname, _MISSING)))
                if kind == 'ref':
                    ARRS[pname] = src
                else:
                    ARRS[pname] = dict(src)
        for aname, isarr in fn.autos:
            if isarr:
                saved.append((1, aname, ARRS.get(aname, _MISSING)))
                ARRS[aname] = {}
            else:
                saved.append((0, aname, VARS.get(aname, _MISSING)))
                VARS[aname] = ZERO
        CB.append(S.ibase)
        try:
            r = fn.body()
        finally:
            CB.pop()
    finally:
        for kind, nm, old in reversed(saved):
            d = ARRS if kind else VARS
            if old is _MISSING:
                d.pop(nm, None)
            else:
                d[nm] = old
    if fn.void:
        return VOID
    if r is None or r is BRK or r is CONT:
        return ZERO
    return r[0]


# ---------------------------------------------------------------------------
# Compilation of AST to closures
# ---------------------------------------------------------------------------

def c_num(s):
    cache = {}

    def f():
        b = CB[-1] if CB else S.ibase
        v = cache.get(b)
        if v is None:
            v = conv_const(s, b)
            cache[b] = v
        return v
    return f


def c_call_raw(n):
    name = n[1]
    args = []
    for kind, a in n[2]:
        if kind == 'val':
            args.append(('val', cexpr(a)))
        else:
            args.append(('arr', a))

    def f():
        vals = []
        for kind, a in args:
            if kind == 'val':
                vals.append(('val', a()))
            else:
                vals.append(('arr', a))
        return call_function(name, vals)
    return f


def c_lvalue(lv):
    """Return (prep, load, store) closures for an lvalue."""
    kind = lv[0]
    if kind == 'var':
        name = lv[1]

        def prep():
            return None

        def load(k):
            return VARS.get(name, ZERO)

        def store(k, v):
            VARS[name] = v
        return prep, load, store
    if kind == 'arr':
        name = lv[1]
        idx = cexpr(lv[2])

        def prep():
            return arr_index(idx(), name)

        def load(k):
            return get_arr(name).get(k, ZERO)

        def store(k, v):
            get_arr(name)[k] = v
        return prep, load, store
    name = lv[1]

    def prep():
        return None

    def load(k):
        return load_special(name)

    def store(k, v):
        store_special(name, v)
    return prep, load, store


def cexpr(n):
    t = n[0]
    if t == 'num':
        return c_num(n[1])
    if t == 'paren':
        return cexpr(n[1])
    if t == 'var':
        name = n[1]
        return lambda: VARS.get(name, ZERO)
    if t == 'arr':
        name = n[1]
        idx = cexpr(n[2])

        def f():
            i = arr_index(idx(), name)
            return get_arr(name).get(i, ZERO)
        return f
    if t == 'special':
        name = n[1]
        if name == 'scale':
            return lambda: int2num(S.scale)
        if name == 'ibase':
            return lambda: int2num(S.ibase)
        if name == 'obase':
            return lambda: int2num(S.obase)
        return lambda: S.last
    if t == 'bin':
        op = n[1]
        l = cexpr(n[2])
        r = cexpr(n[3])
        if op == '+':
            return lambda: bc_add(l(), r())
        if op == '-':
            return lambda: bc_sub(l(), r())
        if op == '*':
            return lambda: bc_mul(l(), r(), S.scale)
        if op == '/':
            return lambda: bc_div(l(), r(), S.scale)
        if op == '%':
            return lambda: bc_mod(l(), r(), S.scale)
        if op == '^':
            return lambda: bc_raise(l(), r(), S.scale)
        raise AssertionError(op)
    if t == 'rel':
        op = n[1]
        l = cexpr(n[2])
        r = cexpr(n[3])
        if op == '<':
            return lambda: ONE if bc_cmp(l(), r()) < 0 else ZERO
        if op == '<=':
            return lambda: ONE if bc_cmp(l(), r()) <= 0 else ZERO
        if op == '>':
            return lambda: ONE if bc_cmp(l(), r()) > 0 else ZERO
        if op == '>=':
            return lambda: ONE if bc_cmp(l(), r()) >= 0 else ZERO
        if op == '==':
            return lambda: ONE if bc_cmp(l(), r()) == 0 else ZERO
        if op == '!=':
            return lambda: ONE if bc_cmp(l(), r()) != 0 else ZERO
        raise AssertionError(op)
    if t == 'and':
        l = cexpr(n[1])
        r = cexpr(n[2])

        def f():
            if l()[1] == 0:
                return ZERO
            if r()[1] == 0:
                return ZERO
            return ONE
        return f
    if t == 'or':
        l = cexpr(n[1])
        r = cexpr(n[2])

        def f():
            if l()[1] != 0:
                return ONE
            if r()[1] != 0:
                return ONE
            return ZERO
        return f
    if t == 'not':
        e = cexpr(n[1])
        return lambda: ONE if e()[1] == 0 else ZERO
    if t == 'neg':
        e = cexpr(n[1])
        return lambda: bc_sub(ZERO, e())
    if t == 'assign':
        lv, op = n[1], n[2]
        rhs = cexpr(n[3])
        if lv[0] == 'var' and op == '=':
            name = lv[1]

            def f():
                v = rhs()
                VARS[name] = v
                return v
            return f
        prep, load, store = c_lvalue(lv)
        if op == '=':
            def f():
                k = prep()
                v = rhs()
                store(k, v)
                return v
            return f
        opf = OPFUNCS[op]

        def f():
            k = prep()
            old = load(k)
            v = opf(old, rhs())
            store(k, v)
            return v
        return f
    if t == 'preinc' or t == 'postinc':
        prep, load, store = c_lvalue(n[1])
        delta = n[2]
        pre = t == 'preinc'

        def f():
            k = prep()
            old = load(k)
            if delta > 0:
                v = bc_add(old, ONE)
            else:
                v = bc_sub(old, ONE)
            store(k, v)
            return v if pre else old
        return f
    if t == 'call':
        raw = c_call_raw(n)

        def f():
            v = raw()
            if v is VOID:
                raise BCRuntimeError("void function used in an expression")
            return v
        return f
    if t == 'length':
        e = cexpr(n[1])
        return lambda: int2num(bc_length(e()))
    if t == 'sqrt':
        e = cexpr(n[1])
        return lambda: bc_sqrt(e(), S.scale)
    if t == 'scalef':
        e = cexpr(n[1])
        return lambda: int2num(e()[2])
    raise AssertionError(t)


def process_escapes(s):
    out = []
    i = 0
    L = len(s)
    while i < L:
        c = s[i]
        if c != '\\':
            out.append(c)
            i += 1
            continue
        i += 1
        if i >= L:
            break
        c = s[i]
        i += 1
        if c == 'a':
            out.append('\x07')
        elif c == 'b':
            out.append('\b')
        elif c == 'f':
            out.append('\f')
        elif c == 'n':
            out.append('\n')
        elif c == 'q':
            out.append('"')
        elif c == 'r':
            out.append('\r')
        elif c == 't':
            out.append('\t')
        elif c == '\\':
            out.append('\\')
    return ''.join(out)


def cblock(stmts):
    fs = [cstmt(s) for s in stmts]
    fs = [f for f in fs if f is not None]
    if not fs:
        return lambda: None
    if len(fs) == 1:
        return fs[0]
    fs = tuple(fs)

    def f():
        for g in fs:
            r = g()
            if r is not None:
                return r
        return None
    return f


def cstmt(n):
    t = n[0]
    if t == 'expr':
        e = n[1]
        if e[0] == 'assign':
            g = cexpr(e)

            def f():
                g()
            return f
        if e[0] == 'call':
            g = c_call_raw(e)
        else:
            g = cexpr(e)

        def f():
            v = g()
            if v is VOID:
                return None
            OUT.write(fmtnum(v))
            OUT.write('\n')
            S.last = v
        return f
    if t == 'str':
        s = n[1]

        def f():
            OUT.write(s)
        return f
    if t == 'print':
        items = []
        for kind, x in n[1]:
            if kind == 's':
                items.append((True, process_escapes(x)))
            else:
                items.append((False, cexpr(x)))

        def f():
            for isstr, x in items:
                if isstr:
                    OUT.write(x)
                else:
                    v = x()
                    OUT.write(fmtnum(v))
                    S.last = v
        return f
    if t == 'block':
        return cblock(n[1])
    if t == 'if':
        cond = cexpr(n[1])
        s1 = cstmt(n[2])
        s2 = cstmt(n[3]) if n[3] is not None else None
        if s2 is None:
            def f():
                if cond()[1] != 0:
                    return s1()
            return f

        def f():
            if cond()[1] != 0:
                return s1()
            return s2()
        return f
    if t == 'while':
        cond = cexpr(n[1])
        body = cstmt(n[2])

        def f():
            while cond()[1] != 0:
                r = body()
                if r is not None:
                    if r is BRK:
                        break
                    return r
            return None
        return f
    if t == 'for':
        e1 = cexpr(n[1]) if n[1] is not None else None
        e2 = cexpr(n[2]) if n[2] is not None else None
        e3 = cexpr(n[3]) if n[3] is not None else None
        body = cstmt(n[4])

        def f():
            if e1 is not None:
                e1()
            while True:
                if e2 is not None and e2()[1] == 0:
                    break
                r = body()
                if r is not None:
                    if r is BRK:
                        break
                    if r is not CONT:
                        return r
                if e3 is not None:
                    e3()
            return None
        return f
    if t == 'break':
        return lambda: BRK
    if t == 'continue':
        return lambda: CONT
    if t == 'halt':
        def f():
            raise HaltProgram()
        return f
    if t == 'return':
        if n[1] is None:
            return lambda: [ZERO]
        e = cexpr(n[1])
        return lambda: [e()]
    if t == 'nop':
        return None
    raise AssertionError(t)


# ---------------------------------------------------------------------------
# Lexer
# ---------------------------------------------------------------------------

KEYWORDS = {
    'auto', 'break', 'continue', 'define', 'else', 'for', 'halt', 'ibase',
    'if', 'last', 'length', 'limits', 'obase', 'print', 'quit', 'read',
    'return', 'scale', 'sqrt', 'warranty', 'while', 'void',
}

OPS3 = ()
OPS2 = {'&&', '||', '++', '--', '==', '<=', '>=', '!=', '+=', '-=', '*=',
        '/=', '%=', '^='}
OPS1 = set('+-*/%^=<>!(){}[],;&')

DIGITCH = set('0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ')
NAMESTART = set('abcdefghijklmnopqrstuvwxyz')
NAMECH = set('abcdefghijklmnopqrstuvwxyz0123456789_')


def tokenize(src):
    toks = []
    i = 0
    n = len(src)
    line = 1
    append = toks.append
    while i < n:
        c = src[i]
        if c == ' ' or c == '\t':
            i += 1
            continue
        if c == '\n':
            append(('nl', None, line))
            line += 1
            i += 1
            continue
        if c == '\\' and i + 1 < n and src[i + 1] == '\n':
            i += 2
            line += 1
            continue
        if c == '/' and i + 1 < n and src[i + 1] == '*':
            j = src.find('*/', i + 2)
            if j < 0:
                append(('bad', 'EOF in comment', line))
                i = n
                break
            line += src.count('\n', i, j)
            i = j + 2
            continue
        if c == '#':
            j = src.find('\n', i)
            if j < 0:
                i = n
            else:
                i = j
            continue
        if c == '"':
            j = src.find('"', i + 1)
            if j < 0:
                append(('bad', 'EOF in string', line))
                i = n
                break
            s = src[i + 1:j]
            append(('str', s, line))
            line += s.count('\n')
            i = j + 1
            continue
        if c in DIGITCH or (c == '.' and i + 1 < n and
                            (src[i + 1] in DIGITCH or
                             (src[i + 1] == '\\' and i + 2 < n and src[i + 2] == '\n'
                              and _dot_number_follows(src, i + 1)))):
            j = i
            parts = []
            seen_dot = False
            while j < n:
                ch = src[j]
                if ch in DIGITCH:
                    parts.append(ch)
                    j += 1
                elif ch == '\\' and j + 1 < n and src[j + 1] == '\n':
                    j += 2
                    line += 1
                elif ch == '.' and not seen_dot:
                    seen_dot = True
                    parts.append(ch)
                    j += 1
                else:
                    break
            s = ''.join(parts)
            if s.endswith('.'):
                s = s[:-1]
            k = 0
            while k < len(s) and s[k] == '0':
                k += 1
            if k == len(s):
                s = '0'
            else:
                s = s[k:]
            append(('num', s, line))
            i = j
            continue
        if c in NAMESTART:
            j = i + 1
            while j < n and src[j] in NAMECH:
                j += 1
            w = src[i:j]
            if w in KEYWORDS:
                append(('kw', w, line))
            else:
                append(('name', w, line))
            i = j
            continue
        if c == '.':
            append(('kw', 'last', line))
            i += 1
            continue
        two = src[i:i + 2]
        if two in OPS2:
            append(('op', two, line))
            i += 2
            continue
        if c in OPS1:
            append(('op', c, line))
            i += 1
            continue
        append(('bad', c, line))
        i += 1
    append(('eof', None, line))
    return toks


def _dot_number_follows(src, j):
    n = len(src)
    while j + 1 < n and src[j] == '\\' and src[j + 1] == '\n':
        j += 2
    return j < n and src[j] in DIGITCH


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

BINPREC = {'||': 1, '&&': 2, '<': 4, '<=': 4, '>': 4, '>=': 4, '==': 4,
           '!=': 4, '+': 6, '-': 6, '*': 7, '/': 7, '%': 7, '^': 8}
ASSIGNOPS = {'=': '=', '+=': '+', '-=': '-', '*=': '*', '/=': '/',
             '%=': '%', '^=': '^'}
RELOPS = {'<', '<=', '>', '>=', '==', '!='}

LIMITS_TEXT = (
    "BC_BASE_MAX     = 2147483647\n"
    "BC_DIM_MAX      = 16777215\n"
    "BC_SCALE_MAX    = 2147483647\n"
    "BC_STRING_MAX   = 2147483647\n"
    "MAX Exponent    = 9223372036854775807\n"
    "Number of vars  = 32767\n"
)


class Parser:
    def __init__(self, toks):
        self.toks = toks
        self.i = 0
        self.in_func = False
        self.in_void = False
        self.loop_depth = 0
        self.for_depth = 0

    def peek(self):
        return self.toks[self.i]

    def peek2(self, k=1):
        j = self.i + k
        if j < len(self.toks):
            return self.toks[j]
        return self.toks[-1]

    def next(self):
        t = self.toks[self.i]
        if t[0] != 'eof':
            self.i += 1
        return t

    def error(self, msg="syntax error"):
        raise ParseError(msg, self.i)

    def is_op(self, v):
        t = self.toks[self.i]
        return t[0] == 'op' and t[1] == v

    def is_kw(self, v):
        t = self.toks[self.i]
        return t[0] == 'kw' and t[1] == v

    def expect_op(self, v):
        t = self.toks[self.i]
        if t[0] == 'op' and t[1] == v:
            self.i += 1
            return
        self.error()

    def opt_newline(self):
        if self.toks[self.i][0] == 'nl':
            self.i += 1

    # ---- items ----
    def at_eof(self):
        return self.toks[self.i][0] == 'eof'

    def parse_item(self):
        """Parse one input item.  Returns ('run', stmts) or ('define', ...)."""
        t = self.peek()
        if t[0] == 'kw' and t[1] == 'define':
            return self.parse_define()
        stmts = []
        while True:
            t = self.peek()
            if t[0] == 'nl':
                self.i += 1
                break
            if t[0] == 'eof':
                break
            if t[0] == 'op' and t[1] == ';':
                self.i += 1
                continue
            stmts.append(self.parse_statement())
            t = self.peek()
            if t[0] == 'op' and t[1] == ';':
                self.i += 1
                continue
            if t[0] == 'nl':
                self.i += 1
                break
            if t[0] == 'eof':
                break
            self.error()
        return ('run', stmts)

    def parse_define(self):
        self.next()  # define
        void = False
        if self.is_kw('void'):
            self.next()
            void = True
        t = self.next()
        if t[0] != 'name':
            self.error()
        fname = t[1]
        self.defining = fname
        self.expect_op('(')
        params = []
        if not self.is_op(')'):
            while True:
                params.append(self.parse_param(True))
                if self.is_op(','):
                    self.next()
                    continue
                break
        self.expect_op(')')
        self.opt_newline()
        self.expect_op('{')
        while self.peek()[0] == 'nl':
            self.next()
        autos = []
        if self.is_kw('auto'):
            self.next()
            while True:
                nm, kind = self.parse_param(False)
                autos.append((nm, kind != 'val'))
                if self.is_op(','):
                    self.next()
                    continue
                break
            t = self.peek()
            if t[0] == 'nl' or (t[0] == 'op' and t[1] == ';'):
                self.next()
            else:
                self.error()
        # duplicate checks
        seen_v = set()
        seen_a = set()
        for nm, kind in params:
            s = seen_v if kind == 'val' else seen_a
            if nm in s:
                self.error("duplicate parameter names")
            s.add(nm)
        for nm, isarr in autos:
            s = seen_a if isarr else seen_v
            if nm in s:
                self.error("duplicate auto variable names")
            s.add(nm)
        old = (self.in_func, self.in_void, self.loop_depth, self.for_depth)
        self.in_func = True
        self.in_void = void
        self.loop_depth = 0
        self.for_depth = 0
        try:
            body = self.parse_stmt_list_until_brace()
        finally:
            self.in_func, self.in_void, self.loop_depth, self.for_depth = old
        self.expect_op('}')
        return ('define', fname, void, params, autos, body)

    def parse_param(self, allow_ref):
        kind = 'val'
        if allow_ref and (self.is_op('*') or self.is_op('&')):
            self.next()
            kind = 'ref'
        t = self.next()
        if t[0] != 'name':
            self.error()
        if self.is_op('['):
            self.next()
            self.expect_op(']')
            if kind == 'val':
                kind = 'arr'
        elif kind == 'ref':
            self.error()
        return (t[1], kind)

    def parse_stmt_list_until_brace(self):
        stmts = []
        while True:
            t = self.peek()
            if t[0] == 'op' and t[1] == '}':
                return stmts
            if t[0] == 'nl' or (t[0] == 'op' and t[1] == ';'):
                self.i += 1
                continue
            if t[0] == 'eof':
                self.error()
            stmts.append(self.parse_statement())
            t = self.peek()
            if t[0] == 'nl' or (t[0] == 'op' and t[1] == ';'):
                self.i += 1
                continue
            if t[0] == 'op' and t[1] == '}':
                return stmts
            self.error()

    # ---- statements ----
    def parse_statement(self):
        t = self.peek()
        tt, tv = t[0], t[1]
        if tt == 'str':
            self.next()
            return ('str', tv)
        if tt == 'op' and tv == '{':
            self.next()
            stmts = self.parse_stmt_list_until_brace()
            self.expect_op('}')
            return ('block', stmts)
        if tt == 'kw':
            if tv == 'if':
                self.next()
                self.expect_op('(')
                cond = self.parse_expr()
                self.expect_op(')')
                self.opt_newline()
                s1 = self.parse_statement()
                s2 = None
                if self.is_kw('else'):
                    self.next()
                    self.opt_newline()
                    s2 = self.parse_statement()
                return ('if', cond, s1, s2)
            if tv == 'while':
                self.next()
                self.expect_op('(')
                cond = self.parse_expr()
                self.expect_op(')')
                self.opt_newline()
                self.loop_depth += 1
                try:
                    body = self.parse_statement()
                finally:
                    self.loop_depth -= 1
                return ('while', cond, body)
            if tv == 'for':
                self.next()
                self.expect_op('(')
                e1 = None if self.is_op(';') else self.parse_expr()
                self.expect_op(';')
                e2 = None if self.is_op(';') else self.parse_expr()
                self.expect_op(';')
                e3 = None if self.is_op(')') else self.parse_expr()
                self.expect_op(')')
                self.opt_newline()
                self.loop_depth += 1
                self.for_depth += 1
                try:
                    body = self.parse_statement()
                finally:
                    self.loop_depth -= 1
                    self.for_depth -= 1
                return ('for', e1, e2, e3, body)
            if tv == 'break':
                self.next()
                if self.loop_depth == 0:
                    self.error("Break outside a for/while")
                return ('break',)
            if tv == 'continue':
                self.next()
                if self.for_depth == 0:
                    self.error("Continue outside a for")
                return ('continue',)
            if tv == 'halt':
                self.next()
                return ('halt',)
            if tv == 'quit':
                self.next()
                raise QuitProgram()
            if tv == 'limits':
                self.next()
                OUT.write(LIMITS_TEXT)
                return ('nop',)
            if tv == 'warranty':
                self.next()
                return ('nop',)
            if tv == 'return':
                self.next()
                if not self.in_func:
                    self.error("Return outside of a function.")
                if self.starts_expr():
                    e = self.parse_expr()
                    if self.in_void:
                        self.error("return expression in a void function")
                    return ('return', e)
                return ('return', None)
            if tv == 'print':
                self.next()
                items = []
                while True:
                    t = self.peek()
                    if t[0] == 'str':
                        self.next()
                        items.append(('s', t[1]))
                    else:
                        items.append(('e', self.parse_expr()))
                    if self.is_op(','):
                        self.next()
                        continue
                    break
                return ('print', items)
        return ('expr', self.parse_expr())

    def starts_expr(self):
        t = self.peek()
        tt, tv = t[0], t[1]
        if tt in ('num', 'name'):
            return True
        if tt == 'op':
            return tv in ('(', '-', '!', '++', '--')
        if tt == 'kw':
            return tv in ('scale', 'ibase', 'obase', 'last', 'length',
                          'sqrt', 'read')
        return False

    # ---- expressions ----
    def parse_expr(self, minp=1):
        left = self.parse_unary()
        toks = self.toks
        while True:
            t = toks[self.i]
            if t[0] != 'op':
                break
            op = t[1]
            p = BINPREC.get(op)
            if p is None or p < minp:
                break
            self.i += 1
            if op == '^':
                right = self.parse_expr(8)
            else:
                right = self.parse_expr(p + 1)
            if op in RELOPS:
                left = ('rel', op, left, right)
            elif op == '&&':
                left = ('and', left, right)
            elif op == '||':
                left = ('or', left, right)
            else:
                left = ('bin', op, left, right)
        return left

    def parse_unary(self):
        t = self.peek()
        if t[0] == 'op':
            if t[1] == '!':
                self.next()
                return ('not', self.parse_expr(4))
            if t[1] == '-':
                self.next()
                return ('neg', self.parse_unary())
            if t[1] in ('++', '--'):
                self.next()
                lv = self.parse_named()
                if lv is None:
                    self.error()
                return ('preinc', lv, 1 if t[1] == '++' else -1)
        return self.parse_primary()

    def parse_named(self):
        """Parse a named expression (lvalue) or return None."""
        t = self.peek()
        if t[0] == 'name':
            nt = self.peek2()
            if nt[0] == 'op' and nt[1] == '[':
                self.next()
                self.next()
                idx = self.parse_expr()
                self.expect_op(']')
                return ('arr', t[1], idx)
            if nt[0] == 'op' and nt[1] == '(':
                return None
            self.next()
            return ('var', t[1])
        if t[0] == 'kw':
            if t[1] == 'scale':
                nt = self.peek2()
                if nt[0] == 'op' and nt[1] == '(':
                    return None
                self.next()
                return ('special', 'scale')
            if t[1] in ('ibase', 'obase', 'last'):
                self.next()
                return ('special', t[1])
        return None

    def parse_primary(self):
        t = self.peek()
        tt, tv = t[0], t[1]
        if tt == 'num':
            self.next()
            return ('num', tv)
        if tt == 'op' and tv == '(':
            self.next()
            e = self.parse_expr()
            self.expect_op(')')
            return ('paren', e)
        if tt == 'name':
            nt = self.peek2()
            if nt[0] == 'op' and nt[1] == '(':
                self.next()
                self.next()
                args = []
                if not self.is_op(')'):
                    while True:
                        a = self.peek()
                        if (a[0] == 'name' and self.peek2()[0] == 'op' and
                                self.peek2()[1] == '[' and
                                self.peek2(2)[0] == 'op' and
                                self.peek2(2)[1] == ']'):
                            self.next()
                            self.next()
                            self.next()
                            args.append(('arr', a[1]))
                        else:
                            args.append(('val', self.parse_expr()))
                        if self.is_op(','):
                            self.next()
                            continue
                        break
                self.expect_op(')')
                return ('call', tv, args)
        if tt == 'kw':
            if tv in ('length', 'sqrt') or (tv == 'scale' and self.peek2()[0] == 'op'
                                             and self.peek2()[1] == '('):
                self.next()
                self.expect_op('(')
                e = self.parse_expr()
                self.expect_op(')')
                return ({'length': 'length', 'sqrt': 'sqrt',
                         'scale': 'scalef'}[tv], e)
            if tv == 'read':
                self.error("read() is not supported")
        lv = self.parse_named()
        if lv is None:
            self.error()
        t = self.peek()
        if t[0] == 'op':
            op = t[1]
            if op in ASSIGNOPS:
                self.next()
                rhs = self.parse_expr(5)
                return ('assign', lv, ASSIGNOPS[op], rhs)
            if op == '++' or op == '--':
                self.next()
                return ('postinc', lv, 1 if op == '++' else -1)
        if lv[0] == 'arr':
            return lv
        return lv


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

def recover(parser, start, errpos):
    toks = parser.toks
    depth = 0
    j = start
    n = len(toks)
    while j < n:
        t = toks[j]
        if t[0] == 'eof':
            parser.i = j
            return
        if t[0] == 'op':
            if t[1] == '{':
                depth += 1
            elif t[1] == '}':
                depth -= 1
        if t[0] == 'nl' and j >= errpos and depth <= 0:
            parser.i = j + 1
            return
        j += 1
    parser.i = n - 1


def run_program(src):
    toks = tokenize(src)
    parser = Parser(toks)
    while not parser.at_eof():
        start = parser.i
        try:
            item = parser.parse_item()
        except ParseError as e:
            line = toks[min(e.pos, len(toks) - 1)][2]
            errmsg("(standard_in) %d: %s" % (line, e))
            parser.in_func = False
            parser.in_void = False
            parser.loop_depth = 0
            parser.for_depth = 0
            t0 = toks[start]
            if t0[0] == 'kw' and t0[1] == 'define':
                j = start + 1
                if toks[j][0] == 'kw' and toks[j][1] == 'void':
                    j += 1
                if toks[j][0] == 'name':
                    FUNCS.pop(toks[j][1], None)
            recover(parser, start, e.pos)
            continue
        if item[0] == 'define':
            _, fname, void, params, autos, body = item
            FUNCS[fname] = Func(fname, params, autos, cblock(body), void)
            continue
        stmts = item[1]
        if not stmts:
            continue
        code = cblock(stmts)
        try:
            code()
        except BCRuntimeError as e:
            errmsg("Runtime error (func=(main), adr=0): %s" % e)
            del CB[:]


def main():
    data = sys.stdin.buffer.read()
    src = data.decode('latin-1')
    status = [0]

    def worker():
        try:
            run_program(src)
        except (HaltProgram, QuitProgram):
            pass
        except RecursionError:
            errmsg("pybc: recursion too deep")
        except MemoryError:
            errmsg("pybc: out of memory")
        OUT.flush()

    sys.setrecursionlimit(1000000)
    threading.stack_size(1024 * 1024 * 1024)
    th = threading.Thread(target=worker)
    th.start()
    th.join()
    return status[0]


if __name__ == "__main__":
    sys.exit(main())
