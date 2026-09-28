"""pydc: a GNU dc 1.4.1 replacement in pure Python.

Usage: python3 /app/pydc/dc.py [OPTION] [FILE]...
"""

import sys
import threading

try:
    sys.set_int_max_str_digits(0)
except AttributeError:  # pragma: no cover
    pass

EOF = None

# ---------------------------------------------------------------------------
# Arbitrary precision decimal numbers, modelled on the bc number library.
# A number is sign + magnitude + scale: value = mag / 10**scale.
# ---------------------------------------------------------------------------

_P10 = {}


def p10(n):
    v = _P10.get(n)
    if v is None:
        v = 10 ** n
        if n < 4096:
            _P10[n] = v
    return v


class Num(object):
    __slots__ = ('neg', 'mag', 'scale')

    def __init__(self, neg, mag, scale):
        self.neg = neg
        self.mag = mag
        self.scale = scale


def num_int(v):
    return Num(v < 0, abs(v), 0)


ONE = Num(False, 1, 0)
TWO = Num(False, 2, 0)
POINT5 = Num(False, 5, 1)


def _cmp_mag(a, b):
    if a.scale == b.scale:
        ma, mb = a.mag, b.mag
    elif a.scale > b.scale:
        ma, mb = a.mag, b.mag * p10(a.scale - b.scale)
    else:
        ma, mb = a.mag * p10(b.scale - a.scale), b.mag
    return (ma > mb) - (ma < mb)


def bc_compare(a, b):
    if a.neg != b.neg:
        return -1 if a.neg else 1
    c = _cmp_mag(a, b)
    return -c if a.neg else c


def _aligned(a, b, smin):
    s = max(smin, a.scale, b.scale)
    return a.mag * p10(s - a.scale), b.mag * p10(s - b.scale), s


def bc_add(a, b, smin=0):
    ma, mb, s = _aligned(a, b, smin)
    if a.neg == b.neg:
        return Num(a.neg, ma + mb, s)
    if ma == mb:
        return Num(False, 0, s)
    if ma < mb:
        return Num(b.neg, mb - ma, s)
    return Num(a.neg, ma - mb, s)


def bc_sub(a, b, smin=0):
    ma, mb, s = _aligned(a, b, smin)
    if a.neg != b.neg:
        return Num(a.neg, ma + mb, s)
    if ma == mb:
        return Num(False, 0, s)
    if ma < mb:
        return Num(not b.neg, mb - ma, s)
    return Num(a.neg, ma - mb, s)


def bc_mul(a, b, scale):
    full = a.scale + b.scale
    ps = min(full, max(scale, a.scale, b.scale))
    m = a.mag * b.mag
    if full > ps:
        m //= p10(full - ps)
    return Num(a.neg != b.neg and m != 0, m, ps)


def bc_div(a, b, scale):
    if b.mag == 0:
        return None
    num = a.mag * p10(b.scale + scale)
    den = b.mag * p10(a.scale)
    q = num // den
    return Num(a.neg != b.neg and q != 0, q, scale)


def bc_divmod(a, b, scale):
    if b.mag == 0:
        return None
    rscale = max(a.scale, b.scale + scale)
    q = bc_div(a, b, scale)
    t = bc_mul(q, b, rscale)
    r = bc_sub(a, t, rscale)
    return q, r


def bc_mod(a, b, scale):
    r = bc_divmod(a, b, scale)
    if r is None:
        return None
    return r[1]


def int_part(n):
    """bc_num2long style: integer part, truncated toward zero."""
    ip = n.mag // p10(n.scale)
    return -ip if n.neg else ip


def bc_raise(a, b, scale):
    e = int_part(b)
    if e == 0:
        return Num(False, 1, 0)
    negexp = e < 0
    if negexp:
        e = -e
        rscale = scale
    else:
        rscale = min(a.scale * e, max(scale, a.scale))
    if e == 1:
        tneg, tmag, tscale = a.neg, a.mag, a.scale
    else:
        tmag = a.mag ** e
        tscale = a.scale * e
        tneg = a.neg and (e & 1) == 1 and tmag != 0
    if negexp:
        r = bc_div(ONE, Num(tneg, tmag, tscale), rscale)
        if r is None:
            return Num(False, 0, 0)
        return r
    if tscale > rscale:
        tmag //= p10(tscale - rscale)
        tscale = rscale
    return Num(tneg, tmag, tscale)


def bc_raisemod(base, expo, mod, scale):
    if mod.mag == 0:
        return None
    if expo.neg:
        return None
    power = base
    exponent = expo
    if exponent.scale != 0:
        exponent = bc_div(exponent, ONE, 0)
    modulus = mod
    temp = ONE
    rscale = max(scale, power.scale)
    if bc_compare(modulus, ONE) == 0:
        return Num(False, 0, scale)
    while exponent.mag != 0:
        exponent, parity = bc_divmod(exponent, TWO, 0)
        if parity.mag != 0:
            temp = bc_mul(temp, power, rscale)
            temp = bc_mod(temp, modulus, scale)
        power = bc_mul(power, power, rscale)
        power = bc_mod(power, modulus, scale)
    return temp


def _near_zero(n, scale):
    if scale > n.scale:
        scale = n.scale
    m = n.mag // p10(n.scale - scale)
    return m <= 1


def bc_sqrt(num, scale):
    c = bc_compare(num, Num(False, 0, 0))
    if c < 0:
        return None
    if c == 0:
        return Num(False, 0, 0)
    c = bc_compare(num, ONE)
    if c == 0:
        return Num(False, 1, 0)
    rscale = max(scale, num.scale)
    if c < 0:
        guess = ONE
        cscale = num.scale
    else:
        nlen = len(str(num.mag // p10(num.scale)))
        guess = Num(False, p10(nlen // 2), 0)
        cscale = 3
    while True:
        guess1 = guess
        guess = bc_div(num, guess, cscale)
        guess = bc_add(guess, guess1, 0)
        guess = bc_mul(guess, POINT5, cscale)
        diff = bc_sub(guess, guess1, cscale + 1)
        if _near_zero(diff, cscale):
            if cscale < rscale + 1:
                cscale = min(cscale * 3, rscale + 1)
            else:
                break
    return bc_div(guess, ONE, rscale)


REF = '0123456789ABCDEF'


def num_chars(n, obase):
    out = []
    if n.neg:
        out.append('-')
    if n.mag == 0:
        out.append('0')
        return out
    sc = n.scale
    ps = p10(sc)
    ip, fp = divmod(n.mag, ps)
    if obase == 10:
        if ip != 0:
            out.append(str(ip))
        if sc > 0:
            out.append('.')
            out.append(str(fp).rjust(sc, '0'))
        return out
    width = len(str(obase - 1))
    digits = []
    while ip:
        ip, d = divmod(ip, obase)
        digits.append(d)
    digits.reverse()
    if obase <= 16:
        for d in digits:
            out.append(REF[d])
    else:
        for d in digits:
            out.append(' ' + str(d).rjust(width, '0'))
    if sc > 0:
        out.append('.')
        t = 1
        first = True
        while t < ps:
            fp *= obase
            d, fp = divmod(fp, ps)
            if obase <= 16:
                out.append(REF[d])
            else:
                if first:
                    out.append(str(d).rjust(width, '0'))
                else:
                    out.append(' ' + str(d).rjust(width, '0'))
                first = False
            t *= obase
    return out


def split_lines(s, line_max=70):
    if len(s) < line_max:
        return s
    res = []
    col = 0
    for ch in s:
        col += 1
        if col >= line_max:
            res.append('\\\n')
            col = 1
        res.append(ch)
    return ''.join(res)


def num2int(n):
    ip = n.mag // p10(n.scale)
    if ip == 0:
        return -1 if n.mag != 0 else 0
    if ip >= 2 ** 31:
        return -1
    return -ip if n.neg else ip


def numlen(n):
    if n.mag == 0:
        return 1
    return len(str(n.mag))


# ---------------------------------------------------------------------------
# Interpreter
# ---------------------------------------------------------------------------

(OK, EATONE, EVALREG, EVALTOS, QUIT, COMMENT, NEGCMP, EOFERR,
 SYSTEM) = range(9)

HEX = dict((ch, i) for i, ch in enumerate('0123456789ABCDEF'))
NUMSTART = set('_.0123456789ABCDEF')
WS = set(' \t\n\v\f\r')


class ExitProgram(Exception):
    pass


class Stream(object):
    def __init__(self, text):
        self.text = text
        self.pos = 0

    def getc(self):
        p = self.pos
        if p < len(self.text):
            self.pos = p + 1
            return self.text[p]
        return EOF

    def ungetc(self):
        if self.pos > 0:
            self.pos -= 1


class LazyStdin(Stream):
    def __init__(self):
        self._text = None
        self.pos = 0

    @property
    def text(self):
        if self._text is None:
            try:
                data = sys.stdin.buffer.read()
            except Exception:
                data = b''
            self._text = data.decode('latin-1')
        return self._text


class DC(object):
    def __init__(self):
        self.stack = []
        self.regs = {}
        self.ibase = 10
        self.obase = 10
        self.scale = 0
        self.unwind = 0
        self.noexit = False
        self.out = []
        self.stdin = LazyStdin()
        self.stdin_lookahead = EOF

    def err(self, msg):
        try:
            sys.stderr.write('dc: ' + msg + '\n')
        except Exception:
            pass

    # -- output ----------------------------------------------------------
    def print_value(self, v, newline):
        if isinstance(v, Num):
            self.out.append(split_lines(''.join(num_chars(v, self.obase))))
        else:
            self.out.append(v)
        if newline:
            self.out.append('\n')

    # -- stack helpers ---------------------------------------------------
    def pop(self):
        if not self.stack:
            self.err('stack empty')
            return None
        return self.stack.pop()

    def binop(self, op):
        st = self.stack
        if not st:
            self.err('stack empty')
            return
        if len(st) < 2:
            self.err('stack empty')
            return
        b = st[-1]
        a = st[-2]
        if isinstance(a, Num) and isinstance(b, Num):
            r = op(a, b)
            if r is None:
                return
            del st[-2:]
            st.append(r)
        else:
            self.err('non-numeric value')

    def binop2(self, op):
        st = self.stack
        if len(st) < 2:
            self.err('stack empty')
            return
        b = st[-1]
        a = st[-2]
        if isinstance(a, Num) and isinstance(b, Num):
            r = op(a, b)
            if r is None:
                return
            del st[-2:]
            st.append(r[0])
            st.append(r[1])
        else:
            self.err('non-numeric value')

    def triop(self, op):
        st = self.stack
        if len(st) < 3:
            self.err('stack empty')
            return
        c = st[-1]
        b = st[-2]
        a = st[-3]
        if isinstance(a, Num) and isinstance(b, Num) and isinstance(c, Num):
            r = op(a, b, c)
            if r is None:
                return
            del st[-3:]
            st.append(r)
        else:
            self.err('non-numeric value')

    def cmpop(self):
        st = self.stack
        if len(st) < 2:
            self.err('stack empty')
            return 0
        b = st[-1]
        a = st[-2]
        if not (isinstance(a, Num) and isinstance(b, Num)):
            self.err('non-numeric value')
            return 0
        del st[-2:]
        return bc_compare(b, a)

    # -- registers -------------------------------------------------------
    def reg_get(self, r):
        lst = self.regs.get(r)
        if not lst or lst[-1][0] is None:
            return Num(False, 0, 0)
        return lst[-1][0]

    def rotate(self, n):
        st = self.stack
        if n == 0:
            return
        m = min(abs(n), len(st))
        if m <= 1:
            return
        grp = st[-m:]
        if n > 0:
            new = grp[1:] + grp[:1]
        else:
            new = grp[-1:] + grp[:-1]
        st[-m:] = new

    # -- the command dispatcher -----------------------------------------
    def func(self, c, peekc, negcmp):
        st = self.stack
        k = self.scale
        if c in ' \t\n':
            return OK
        if c == '+':
            self.binop(lambda a, b: bc_add(a, b, 0))
        elif c == '-':
            self.binop(lambda a, b: bc_sub(a, b, 0))
        elif c == '*':
            self.binop(lambda a, b: bc_mul(a, b, k))
        elif c == '/':
            def op(a, b):
                r = bc_div(a, b, k)
                if r is None:
                    self.err('divide by zero')
                return r
            self.binop(op)
        elif c == '%':
            def op(a, b):
                r = bc_mod(a, b, k)
                if r is None:
                    self.err('remainder by zero')
                return r
            self.binop(op)
        elif c == '~':
            def op(a, b):
                r = bc_divmod(a, b, k)
                if r is None:
                    self.err('divide by zero')
                return r
            self.binop2(op)
        elif c == '^':
            self.binop(lambda a, b: bc_raise(a, b, k))
        elif c == '|':
            def op(a, b, m):
                r = bc_raisemod(a, b, m, k)
                if r is None:
                    self.err('modexp error')
                return r
            self.triop(op)
        elif c in '<=>':
            if peekc is EOF:
                return EOFERR
            r = self.cmpop()
            if c == '<':
                cond = r < 0
            elif c == '=':
                cond = r == 0
            else:
                cond = r > 0
            if cond == (not negcmp):
                return EVALREG
            return EATONE
        elif c == '?':
            if self.stdin_lookahead is not EOF:
                self.stdin.ungetc()
                self.stdin_lookahead = EOF
            buf = []
            while True:
                ch = self.stdin.getc()
                if ch is EOF or ch == '\n':
                    break
                buf.append(ch)
            st.append(''.join(buf))
            return EVALTOS
        elif c == '!':
            if peekc is not EOF and peekc in '<=>':
                return NEGCMP
            return SYSTEM
        elif c == '#':
            return COMMENT
        elif c == 'a':
            v = self.pop()
            if v is not None:
                if isinstance(v, Num):
                    st.append(chr(num2int(v) & 0xFF))
                else:
                    st.append(v[0] if v else '\0')
        elif c == 'c':
            del st[:]
        elif c == 'd':
            if st:
                st.append(st[-1])
            else:
                self.err('stack empty')
        elif c == 'f':
            for v in reversed(st):
                self.print_value(v, True)
        elif c == 'i':
            v = self.pop()
            if v is not None:
                t = num2int(v) if isinstance(v, Num) else 0
                if 2 <= t <= 16:
                    self.ibase = t
                else:
                    self.err('input base must be a number between 2 and 16')
        elif c == 'k':
            v = self.pop()
            if v is not None:
                t = num2int(v) if isinstance(v, Num) else -1
                if t >= 0:
                    self.scale = t
                else:
                    self.err('scale must be a nonnegative number')
        elif c == 'n':
            v = self.pop()
            if v is not None:
                self.print_value(v, False)
        elif c == 'o':
            v = self.pop()
            if v is not None:
                t = num2int(v) if isinstance(v, Num) else 0
                if t > 1:
                    self.obase = t
                else:
                    self.err('output base must be a number greater than 1')
        elif c == 'p':
            if st:
                self.print_value(st[-1], True)
            else:
                self.err('stack empty')
        elif c == 'q':
            self.unwind = 1
            self.noexit = False
            return QUIT
        elif c == 'r':
            if len(st) >= 2:
                st[-1], st[-2] = st[-2], st[-1]
            else:
                self.err('stack empty')
        elif c == 'R':
            v = self.pop()
            if v is not None:
                t = num2int(v) if isinstance(v, Num) else 0
                self.rotate(t)
        elif c == 'v':
            v = self.pop()
            if v is not None:
                if not isinstance(v, Num):
                    self.err('square root of nonnumeric attempted')
                else:
                    r = bc_sqrt(v, k)
                    if r is None:
                        self.err('square root of negative number')
                    else:
                        st.append(r)
        elif c == 'x':
            return EVALTOS
        elif c == 'z':
            st.append(num_int(len(st)))
        elif c == 'I':
            st.append(num_int(self.ibase))
        elif c == 'K':
            st.append(num_int(self.scale))
        elif c == 'O':
            st.append(num_int(self.obase))
        elif c == 'P':
            v = self.pop()
            if v is not None:
                if isinstance(v, Num):
                    ip = v.mag // p10(v.scale)
                    bs = []
                    while True:
                        ip, d = divmod(ip, 256)
                        bs.append(chr(d))
                        if ip == 0:
                            break
                    bs.reverse()
                    self.out.append(''.join(bs))
                else:
                    self.out.append(v)
        elif c == 'Q':
            v = self.pop()
            if v is not None:
                n = num2int(v) if isinstance(v, Num) else 0
                if n > 0:
                    self.unwind = n - 1
                    self.noexit = True
                    return QUIT
                self.unwind = 0
                self.err('Q command requires a number >= 1')
        elif c == 'X':
            v = self.pop()
            if v is not None:
                st.append(num_int(v.scale if isinstance(v, Num) else 0))
        elif c == 'Z':
            v = self.pop()
            if v is not None:
                if isinstance(v, Num):
                    st.append(num_int(numlen(v)))
                else:
                    st.append(num_int(len(v)))
        elif c == ':':
            if peekc is EOF:
                return EOFERR
            v = self.pop()
            if v is not None:
                t = num2int(v) if isinstance(v, Num) else -1
                val = self.pop()
                if val is not None:
                    if t < 0:
                        self.err('array index must be a nonnegative integer')
                    else:
                        lst = self.regs.setdefault(peekc, [])
                        if not lst:
                            lst.append([None, {}])
                        lst[-1][1][t] = val
            return EATONE
        elif c == ';':
            if peekc is EOF:
                return EOFERR
            v = self.pop()
            if v is not None:
                t = num2int(v) if isinstance(v, Num) else -1
                if t < 0:
                    self.err('array index must be a nonnegative integer')
                else:
                    lst = self.regs.get(peekc)
                    if lst:
                        st.append(lst[-1][1].get(t, Num(False, 0, 0)))
                    else:
                        st.append(Num(False, 0, 0))
            return EATONE
        elif c == 'l':
            if peekc is EOF:
                return EOFERR
            st.append(self.reg_get(peekc))
            return EATONE
        elif c == 'L':
            if peekc is EOF:
                return EOFERR
            lst = self.regs.get(peekc)
            if not lst or lst[-1][0] is None:
                self.err('stack register is empty')
            else:
                st.append(lst.pop()[0])
            return EATONE
        elif c == 's':
            if peekc is EOF:
                return EOFERR
            v = self.pop()
            if v is not None:
                lst = self.regs.setdefault(peekc, [])
                if not lst:
                    lst.append([v, {}])
                else:
                    lst[-1][0] = v
            return EATONE
        elif c == 'S':
            if peekc is EOF:
                return EOFERR
            v = self.pop()
            if v is not None:
                self.regs.setdefault(peekc, []).append([v, {}])
            return EATONE
        else:
            self.err('%r unimplemented' % c)
        return OK

    # -- number reading --------------------------------------------------
    def getnum(self, c, nextc):
        base = self.ibase
        neg = False
        if c == '_' or c == '-':
            neg = True
            c = nextc()
        elif c == '+':
            c = nextc()
        while c is not EOF and c in WS:
            c = nextc()
        ival = 0
        while c is not EOF and c in HEX:
            ival = ival * base + HEX[c]
            c = nextc()
        mag = ival
        scale = 0
        if c == '.':
            build = 0
            div = 1
            dec = 0
            while True:
                c = nextc()
                if c is not EOF and c in HEX:
                    build = build * base + HEX[c]
                    div *= base
                    dec += 1
                else:
                    break
            mag = ival * p10(dec) + (build * p10(dec)) // div
            scale = dec
        return Num(neg and mag != 0, mag, scale), c

    # -- evaluating strings (macros and -e expressions) -------------------
    def evalstr(self, text, toplevel=False):
        s = text
        i = 0
        end = len(s)
        tail = 1
        next_neg = False
        st = self.stack
        while i < end:
            c = s[i]
            i += 1
            peekc = s[i] if i < end else EOF
            neg = next_neg
            next_neg = False
            if c in NUMSTART:
                cur = Stream(s)
                cur.pos = i
                val, ra = self.getnum(c, cur.getc)
                st.append(val)
                i = cur.pos - (1 if ra is not EOF else 0)
                continue
            if c == '[':
                depth = 1
                j = i
                while j < end:
                    ch = s[j]
                    if ch == '[':
                        depth += 1
                    elif ch == ']':
                        depth -= 1
                        if depth == 0:
                            break
                    j += 1
                if j >= end:
                    self.err('unexpected EOF')
                    return OK
                st.append(s[i:j])
                i = j + 1
                continue
            status = self.func(c, peekc, neg)
            if status == OK:
                continue
            if status == EATONE:
                i += 1
                continue
            if status == EVALREG:
                i += 1
                st.append(self.reg_get(peekc))
                status = EVALTOS
            if status == EVALTOS:
                if not toplevel:
                    while i < end and s[i] in ' \t\n#':
                        if s[i] == '#':
                            nl = s.find('\n', i)
                            i = end if nl < 0 else nl + 1
                        else:
                            i += 1
                if not st:
                    self.err('stack empty')
                    continue
                v = st.pop()
                if isinstance(v, Num):
                    st.append(v)
                    continue
                if not toplevel and i >= end:
                    s = v
                    i = 0
                    end = len(s)
                    tail += 1
                    continue
                status = self.evalstr(v)
                if status != QUIT:
                    continue
            if status == QUIT:
                if toplevel:
                    if not self.noexit:
                        raise ExitProgram()
                    continue
                if self.unwind >= tail:
                    self.unwind -= tail
                    return QUIT
                return OK
            if status == COMMENT or status == SYSTEM:
                nl = s.find('\n', i)
                i = end if nl < 0 else nl + 1
                continue
            if status == NEGCMP:
                next_neg = True
                continue
            if status == EOFERR:
                if toplevel:
                    return OK
                return OK
        return OK

    # -- evaluating files and standard input ------------------------------
    def evalfile(self, stream, is_stdin):
        st = self.stack
        self.stdin_lookahead = EOF
        getc = stream.getc
        next_neg = False
        c = getc()
        while c is not EOF:
            peekc = getc()
            if is_stdin:
                self.stdin_lookahead = peekc
            neg = next_neg
            next_neg = False
            if c in NUMSTART:
                if peekc is not EOF:
                    stream.ungetc()
                val, peekc = self.getnum(c, getc)
                st.append(val)
                c = peekc
                continue
            if c == '[':
                if peekc is not EOF:
                    stream.ungetc()
                buf = []
                depth = 1
                while True:
                    ch = getc()
                    if ch is EOF:
                        break
                    if ch == ']':
                        depth -= 1
                        if depth < 1:
                            break
                    elif ch == '[':
                        depth += 1
                    buf.append(ch)
                st.append(''.join(buf))
                peekc = getc()
                c = peekc
                continue
            status = self.func(c, peekc, neg)
            if status == OK:
                if is_stdin and self.stdin_lookahead != peekc:
                    peekc = getc()
            elif status == EATONE:
                peekc = getc()
            elif status == EVALREG or status == EVALTOS:
                if status == EVALREG:
                    reg = peekc
                    peekc = getc()
                    self.stdin_lookahead = peekc
                    st.append(self.reg_get(reg))
                if is_stdin and self.stdin_lookahead != peekc:
                    peekc = getc()
                if not st:
                    self.err('stack empty')
                else:
                    v = st.pop()
                    if isinstance(v, Num):
                        st.append(v)
                    else:
                        if self.evalstr(v) == QUIT and not self.noexit:
                            raise ExitProgram()
            elif status == QUIT:
                if not self.noexit:
                    raise ExitProgram()
            elif status == COMMENT or status == SYSTEM:
                while peekc is not EOF and peekc != '\n':
                    peekc = getc()
            elif status == NEGCMP:
                next_neg = True
            elif status == EOFERR:
                pass
            c = peekc
        return OK


def parse_args(argv):
    ops = []
    files = []
    i = 0
    only_files = False
    n = len(argv)
    while i < n:
        a = argv[i]
        i += 1
        if only_files or a == '-' or not a.startswith('-'):
            files.append(a)
            continue
        if a == '--':
            only_files = True
            continue
        if a.startswith('--'):
            name, eq, val = a[2:].partition('=')
            if name in ('expression', 'file'):
                if not eq:
                    if i < n:
                        val = argv[i]
                        i += 1
                    else:
                        continue
                ops.append(('e' if name == 'expression' else 'f', val))
            continue
        j = 1
        while j < len(a):
            ch = a[j]
            j += 1
            if ch in 'ef':
                if j < len(a):
                    val = a[j:]
                elif i < n:
                    val = argv[i]
                    i += 1
                else:
                    break
                ops.append((ch, val))
                break
    return ops, files


def read_file(dc, name):
    if name == '-':
        return None
    try:
        with open(name, 'rb') as fh:
            return fh.read().decode('latin-1')
    except Exception:
        dc.err('Could not open file %s' % name)
        return False


def run(argv, result):
    dc = DC()
    ops, files = parse_args(argv)
    try:
        for kind, val in ops:
            if kind == 'e':
                dc.evalstr(val, toplevel=True)
            else:
                text = read_file(dc, val)
                if text is None:
                    dc.evalfile(dc.stdin, True)
                elif text is not False:
                    dc.evalfile(Stream(text), False)
        for name in files:
            text = read_file(dc, name)
            if text is None:
                dc.evalfile(dc.stdin, True)
            elif text is not False:
                dc.evalfile(Stream(text), False)
        if not ops and not files:
            dc.evalfile(dc.stdin, True)
    except ExitProgram:
        pass
    finally:
        data = ''.join(dc.out).encode('latin-1', 'replace')
        try:
            sys.stdout.buffer.write(data)
            sys.stdout.buffer.flush()
        except Exception:
            pass
    result.append(0)


def main(argv):
    sys.setrecursionlimit(1000000)
    result = []
    try:
        threading.stack_size(512 * 1024 * 1024)
    except Exception:
        try:
            threading.stack_size(128 * 1024 * 1024)
        except Exception:
            pass
    t = threading.Thread(target=run, args=(argv, result))
    t.start()
    t.join()
    return 0 if result else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
