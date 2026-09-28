"""pysort: a GNU sort 9.1 replacement in pure Python.

Usage: python3 /app/pysort/sort.py [OPTION]... [FILE]...

Behaves like GNU sort 9.1 under LC_ALL=C.
"""

import os
import re
import sys
from fractions import Fraction
from functools import cmp_to_key

PROG = "sort"

# ---------------------------------------------------------------------------
# Character classes (C locale)

BLANKS = frozenset(b" \t\n")          # isblank() plus '\n', as GNU sort does
ALNUM = frozenset(b"0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz")
NONDICT = frozenset(c for c in range(256) if c not in ALNUM and c not in BLANKS)
NONPRINT = frozenset(c for c in range(256) if not (0x20 <= c < 0x7f))
FOLD = bytes((c - 32) if 0x61 <= c <= 0x7a else c for c in range(256))
DIGITS = frozenset(b"0123456789")

MONTHS = {b"JAN": 1, b"FEB": 2, b"MAR": 3, b"APR": 4, b"MAY": 5, b"JUN": 6,
          b"JUL": 7, b"AUG": 8, b"SEP": 9, b"OCT": 10, b"NOV": 11, b"DEC": 12}

UNIT_ORDER = {ord("K"): 1, ord("k"): 1, ord("M"): 2, ord("G"): 3, ord("T"): 4,
              ord("P"): 5, ord("E"): 6, ord("Z"): 7, ord("Y"): 8}


class UsageError(Exception):
    pass


def die(msg, status=2):
    sys.stderr.write("%s: %s\n" % (PROG, msg))
    sys.stdout.flush()
    raise SystemExit(status)


# ---------------------------------------------------------------------------
# Keys

class Key:
    __slots__ = ("sword", "schar", "eword", "echar", "skipsblanks",
                 "skipeblanks", "ignore", "translate", "numeric",
                 "general_numeric", "human_numeric", "month", "version",
                 "random", "reverse")

    def __init__(self):
        self.sword = None   # None == SIZE_MAX (start of line)
        self.schar = 0
        self.eword = None   # None == SIZE_MAX (end of line)
        self.echar = 0
        self.skipsblanks = False
        self.skipeblanks = False
        self.ignore = None
        self.translate = False
        self.numeric = False
        self.general_numeric = False
        self.human_numeric = False
        self.month = False
        self.version = False
        self.random = False
        self.reverse = False

    def is_default(self):
        return not (self.ignore or self.translate or self.skipsblanks
                    or self.skipeblanks or self.month or self.numeric
                    or self.general_numeric or self.human_numeric
                    or self.version or self.random)


def set_ordering(s, i, key, where):
    """Parse ordering letters from s[i:]; where is 'global', 'start', 'end'."""
    while i < len(s):
        c = s[i]
        if c == "b":
            if where == "start":
                key.skipsblanks = True
            elif where == "end":
                key.skipeblanks = True
            else:
                key.skipsblanks = key.skipeblanks = True
        elif c == "d":
            key.ignore = NONDICT
        elif c == "f":
            key.translate = True
        elif c == "g":
            key.general_numeric = True
        elif c == "h":
            key.human_numeric = True
        elif c == "i":
            if not key.ignore:
                key.ignore = NONPRINT
        elif c == "M":
            key.month = True
        elif c == "n":
            key.numeric = True
        elif c == "R":
            key.random = True
        elif c == "r":
            key.reverse = True
        elif c == "V":
            key.version = True
        else:
            return i
        i += 1
    return i


def parse_count(s, i):
    j = i
    while j < len(s) and s[j].isdigit() and s[j] in "0123456789":
        j += 1
    if j == i:
        raise UsageError("invalid number in key spec")
    return int(s[i:j]), j


def parse_key(spec):
    key = Key()
    n, i = parse_count(spec, 0)
    if n == 0:
        raise UsageError("field number is zero")
    sword = n - 1
    schar = 0
    if i < len(spec) and spec[i] == ".":
        c, i = parse_count(spec, i + 1)
        if c == 0:
            raise UsageError("character offset is zero")
        schar = c - 1
    if sword == 0 and schar == 0:
        key.sword = None
    else:
        key.sword = sword
    key.schar = schar
    i = set_ordering(spec, i, key, "start")
    if i < len(spec) and spec[i] == ",":
        n, i = parse_count(spec, i + 1)
        if n == 0:
            raise UsageError("field number is zero")
        key.eword = n - 1
        if i < len(spec) and spec[i] == ".":
            key.echar, i = parse_count(spec, i + 1)
        i = set_ordering(spec, i, key, "end")
    else:
        key.eword = None
        key.echar = 0
    if i != len(spec):
        raise UsageError("stray character in field spec")
    return key


# ---------------------------------------------------------------------------
# Field location

def begfield(line, key, tab):
    ptr = 0
    lim = len(line)
    sword = key.sword if key.sword is not None else 0
    if tab is not None:
        while ptr < lim and sword > 0:
            sword -= 1
            while ptr < lim and line[ptr] != tab:
                ptr += 1
            if ptr < lim:
                ptr += 1
    else:
        while ptr < lim and sword > 0:
            sword -= 1
            while ptr < lim and line[ptr] in BLANKS:
                ptr += 1
            while ptr < lim and line[ptr] not in BLANKS:
                ptr += 1
    if key.skipsblanks:
        while ptr < lim and line[ptr] in BLANKS:
            ptr += 1
    return min(lim, ptr + key.schar)


def limfield(line, key, tab):
    ptr = 0
    lim = len(line)
    eword = key.eword
    echar = key.echar
    if echar == 0:
        eword += 1
    if tab is not None:
        while ptr < lim and eword > 0:
            eword -= 1
            while ptr < lim and line[ptr] != tab:
                ptr += 1
            if ptr < lim and (eword or echar):
                ptr += 1
    else:
        while ptr < lim and eword > 0:
            eword -= 1
            while ptr < lim and line[ptr] in BLANKS:
                ptr += 1
            while ptr < lim and line[ptr] not in BLANKS:
                ptr += 1
    if echar != 0:
        if key.skipeblanks:
            while ptr < lim and line[ptr] in BLANKS:
                ptr += 1
        ptr = min(lim, ptr + echar)
    return ptr


def extract(line, key, tab):
    if key.eword is None:
        lim = len(line)
    else:
        lim = limfield(line, key, tab)
    beg = begfield(line, key, tab)
    if lim < beg:
        lim = beg
    return line[beg:lim]


# ---------------------------------------------------------------------------
# Numeric comparisons

def skip_blanks(s):
    i = 0
    n = len(s)
    while i < n and s[i] in BLANKS:
        i += 1
    return i


def num_value(s, i=None):
    """Value of a strnumcmp-style number (C locale, no thousands sep)."""
    if i is None:
        i = skip_blanks(s)
    n = len(s)
    neg = False
    if i < n and s[i] == 0x2D:  # '-'
        neg = True
        i += 1
    j = i
    while j < n and s[j] in DIGITS:
        j += 1
    ip = s[i:j]
    fp = b""
    if j < n and s[j] == 0x2E:  # '.'
        k = j + 1
        while k < n and s[k] in DIGITS:
            k += 1
        fp = s[j + 1:k]
    if not ip and not fp:
        return Fraction(0)
    v = Fraction(int(ip + fp or b"0"), 10 ** len(fp))
    return -v if neg else v


def cmp(a, b):
    return (a > b) - (a < b)


def numcompare(a, b):
    return cmp(num_value(a), num_value(b))


def find_unit_order(s, i):
    n = len(s)
    neg = False
    if i < n and s[i] == 0x2D:
        neg = True
        i += 1
    nonzero = False
    while i < n and s[i] in DIGITS:
        if s[i] != 0x30:
            nonzero = True
        i += 1
    if i < n and s[i] == 0x2E:
        i += 1
        while i < n and s[i] in DIGITS:
            if s[i] != 0x30:
                nonzero = True
            i += 1
    if not nonzero:
        return 0
    order = UNIT_ORDER.get(s[i], 0) if i < n else 0
    return -order if neg else order


def human_numcompare(a, b):
    ia = skip_blanks(a)
    ib = skip_blanks(b)
    d = find_unit_order(a, ia) - find_unit_order(b, ib)
    if d:
        return d
    return cmp(num_value(a, ia), num_value(b, ib))


# --- strtold emulation (x86-64 80-bit long double) ---

LD_MANT = 64
LD_EMIN = -16382           # min normal exponent (value = m * 2**e, 1<=m<2)
LD_EMAX = 16383
LD_DENORM_Q = LD_EMIN - (LD_MANT - 1)   # quantum for subnormals

_DEC_RE = re.compile(
    rb"([+-]?)(?:(\d+)(?:\.(\d*))?|\.(\d+))(?:[eE]([+-]?\d+))?")
_HEX_RE = re.compile(
    rb"([+-]?)0[xX](?:([0-9a-fA-F]+)(?:\.([0-9a-fA-F]*))?|\.([0-9a-fA-F]+))"
    rb"(?:[pP]([+-]?\d+))?")
_INF_RE = re.compile(rb"([+-]?)(?:inf(?:inity)?)", re.I)
_NAN_RE = re.compile(rb"([+-]?)nan(?:\([0-9A-Za-z_]*\))?", re.I)

SPACES = frozenset(b" \t\n\v\f\r")

INF = "inf"


def round_ld(x):
    """Round a nonnegative Fraction to long double; return Fraction or INF."""
    if x == 0:
        return x
    num, den = x.numerator, x.denominator
    e = num.bit_length() - den.bit_length()
    # adjust so 2**e <= x < 2**(e+1)
    if e >= 0:
        if num < (den << e):
            e -= 1
    else:
        if (num << -e) < den:
            e -= 1
    if e > LD_EMAX:
        return INF
    q = e - (LD_MANT - 1) if e >= LD_EMIN else LD_DENORM_Q
    # scaled = x / 2**q
    if q >= 0:
        sn, sd = num, den << q
    else:
        sn, sd = num << -q, den
    m, r = divmod(sn, sd)
    if 2 * r > sd or (2 * r == sd and (m & 1)):
        m += 1
    if m == 0:
        return Fraction(0)
    if q >= 0:
        v = Fraction(m << q)
    else:
        v = Fraction(m, 1 << -q)
    if v >= Fraction(2) ** (LD_EMAX + 1):
        return INF
    return v


def strtold(s):
    """Return None for conversion failure, ('nan', sign) for NaN, else
    a comparable tuple value (float-like): ('num', sign, magnitude)."""
    i = 0
    n = len(s)
    while i < n and s[i] in SPACES:
        i += 1
    t = s[i:]
    m = _HEX_RE.match(t)
    if m:
        sign = -1 if m.group(1) == b"-" else 1
        ip = m.group(2) or b""
        fp = m.group(3) if m.group(2) is not None else m.group(4)
        fp = fp or b""
        exp = int(m.group(5)) if m.group(5) is not None else 0
        mant = int((ip + fp) or b"0", 16)
        shift = exp - 4 * len(fp)
        return ("num", sign, _scale2(mant, shift))
    m = _DEC_RE.match(t)
    if m:
        sign = -1 if m.group(1) == b"-" else 1
        if m.group(2) is not None:
            ip = m.group(2)
            fp = m.group(3) or b""
        else:
            ip = b""
            fp = m.group(4)
        exp = int(m.group(5)) if m.group(5) is not None else 0
        digits = (ip + fp).lstrip(b"0")
        if not digits:
            return ("num", sign, Fraction(0))
        e10 = exp - len(fp)
        # quick range guards
        mag = len(digits) + e10
        if mag > 4940:
            return ("num", sign, INF)
        if mag < -4960:
            return ("num", sign, Fraction(0))
        mant = int(digits)
        if e10 >= 0:
            v = Fraction(mant * 10 ** e10)
        else:
            v = Fraction(mant, 10 ** -e10)
        return ("num", sign, round_ld(v))
    m = _INF_RE.match(t)
    if m:
        sign = -1 if m.group(1) == b"-" else 1
        return ("num", sign, INF)
    m = _NAN_RE.match(t)
    if m:
        sign = -1 if m.group(1) == b"-" else 1
        return ("nan", sign)
    return None


def _scale2(mant, shift):
    if mant == 0:
        return Fraction(0)
    top = mant.bit_length() + shift
    if top > LD_EMAX + 2:
        return INF
    if top < LD_DENORM_Q - 2:
        return Fraction(0)
    if shift >= 0:
        v = Fraction(mant << shift)
    else:
        v = Fraction(mant, 1 << -shift)
    return round_ld(v)


def _num_order(v):
    """Map ('num', sign, mag) to a sortable tuple."""
    _, sign, mag = v
    if mag == INF:
        return (sign, 0) if sign > 0 else (sign, 0)
    return None


def general_numcompare(a, b):
    va = strtold(a)
    vb = strtold(b)
    if va is None:
        return 0 if vb is None else -1
    if vb is None:
        return 1
    if va[0] == "nan":
        if vb[0] == "nan":
            # memcmp of little-endian long double: sign byte last
            return cmp(1 if va[1] < 0 else 0, 1 if vb[1] < 0 else 0)
        return -1
    if vb[0] == "nan":
        return 1
    return cmp(_numkey(va), _numkey(vb))


def _numkey(v):
    _, sign, mag = v
    if mag == INF:
        return (sign * 2, Fraction(0))
    if mag == 0:
        return (0, Fraction(0))
    return (0, sign * mag)


def getmonth(s):
    i = skip_blanks(s)
    return MONTHS.get(s[i:i + 3].translate(FOLD), 0)


# --- version sort (gnulib filevercmp, 2022) ---

def _isalpha(c):
    return 0x41 <= c <= 0x5A or 0x61 <= c <= 0x7A


def _isalnum(c):
    return _isalpha(c) or 0x30 <= c <= 0x39


def file_prefixlen(s):
    n = len(s)
    prefixlen = 0
    i = 0
    while True:
        if i == n:
            return prefixlen
        i += 1
        prefixlen = i
        while i + 1 < n and s[i] == 0x2E and (_isalpha(s[i + 1]) or s[i + 1] == 0x7E):
            i += 2
            while i < n and (_isalnum(s[i]) or s[i] == 0x7E):
                i += 1


def _order(s, pos, ln):
    if pos == ln:
        return -1
    c = s[pos]
    if 0x30 <= c <= 0x39:
        return 0
    if _isalpha(c):
        return c
    if c == 0x7E:
        return -2
    return c + 256


def verrevcmp(s1, l1, s2, l2):
    p1 = p2 = 0
    while p1 < l1 or p2 < l2:
        first_diff = 0
        while (p1 < l1 and not (0x30 <= s1[p1] <= 0x39)) or \
                (p2 < l2 and not (0x30 <= s2[p2] <= 0x39)):
            c1 = _order(s1, p1, l1)
            c2 = _order(s2, p2, l2)
            if c1 != c2:
                return c1 - c2
            p1 += 1
            p2 += 1
        while p1 < l1 and s1[p1] == 0x30:
            p1 += 1
        while p2 < l2 and s2[p2] == 0x30:
            p2 += 1
        while p1 < l1 and p2 < l2 and 0x30 <= s1[p1] <= 0x39 and 0x30 <= s2[p2] <= 0x39:
            if not first_diff:
                first_diff = s1[p1] - s2[p2]
            p1 += 1
            p2 += 1
        if p1 < l1 and 0x30 <= s1[p1] <= 0x39:
            return 1
        if p2 < l2 and 0x30 <= s2[p2] <= 0x39:
            return -1
        if first_diff:
            return first_diff
    return 0


def filenvercmp(a, b):
    alen = len(a)
    blen = len(b)
    if alen == 0:
        return -1 if blen else 0
    if blen == 0:
        return 1
    if a[0] == 0x2E:
        if b[0] != 0x2E:
            return -1
        adot = alen == 1
        bdot = blen == 1
        if adot:
            return -1 if not bdot else 0
        if bdot:
            return 1
        adotdot = a[1] == 0x2E and alen == 2
        bdotdot = b[1] == 0x2E and blen == 2
        if adotdot:
            return -1 if not bdotdot else 0
        if bdotdot:
            return 1
    elif b[0] == 0x2E:
        return 1
    ap = file_prefixlen(a)
    bp = file_prefixlen(b)
    one_pass_only = ap == alen and bp == blen
    result = verrevcmp(a, ap, b, bp)
    if result or one_pass_only:
        return result
    return verrevcmp(a, alen, b, blen)


# ---------------------------------------------------------------------------
# Comparison

class Sorter:
    def __init__(self, keys, tab, reverse, unique, stable):
        self.keys = keys
        self.tab = tab
        self.reverse = reverse
        self.unique = unique
        self.stable = stable

    def keycompare(self, a, b):
        tab = self.tab
        for key in self.keys:
            ta = extract(a, key, tab)
            tb = extract(b, key, tab)
            if key.ignore:
                ig = key.ignore
                ta = bytes(c for c in ta if c not in ig)
                tb = bytes(c for c in tb if c not in ig)
            if key.translate:
                ta = ta.translate(FOLD)
                tb = tb.translate(FOLD)
            if key.numeric:
                diff = numcompare(ta, tb)
            elif key.general_numeric:
                diff = general_numcompare(ta, tb)
            elif key.human_numeric:
                diff = human_numcompare(ta, tb)
            elif key.month:
                diff = getmonth(ta) - getmonth(tb)
            elif key.version:
                diff = filenvercmp(ta, tb)
            else:
                diff = cmp(ta, tb)
            if diff:
                diff = 1 if diff > 0 else -1
                return -diff if key.reverse else diff
        return 0

    def compare(self, a, b):
        if self.keys:
            diff = self.keycompare(a, b)
            if diff or self.unique or self.stable:
                return diff
        diff = cmp(a, b)
        return -diff if self.reverse else diff


# ---------------------------------------------------------------------------
# Option parsing

LONG_OPTS = [
    # name, has_arg (0 no, 1 required, 2 optional), short equivalent
    ("ignore-leading-blanks", 0, "b"),
    ("check", 2, "check"),
    ("compress-program", 1, None),
    ("debug", 0, "debug"),
    ("dictionary-order", 0, "d"),
    ("ignore-case", 0, "f"),
    ("files0-from", 1, "files0"),
    ("general-numeric-sort", 0, "g"),
    ("human-numeric-sort", 0, "h"),
    ("ignore-nonprinting", 0, "i"),
    ("key", 1, "k"),
    ("merge", 0, "m"),
    ("month-sort", 0, "M"),
    ("numeric-sort", 0, "n"),
    ("output", 1, "o"),
    ("random-sort", 0, "R"),
    ("random-source", 1, None),
    ("reverse", 0, "r"),
    ("sort", 1, "sort"),
    ("stable", 0, "s"),
    ("buffer-size", 1, None),
    ("field-separator", 1, "t"),
    ("temporary-directory", 1, None),
    ("unique", 0, "u"),
    ("version-sort", 0, "V"),
    ("zero-terminated", 0, "z"),
    ("parallel", 1, None),
    ("batch-size", 1, None),
    ("help", 0, "help"),
    ("version", 0, "version"),
]

SHORT_NOARG = set("bcCdfghimMnrRsuVz")
SHORT_ARG = set("kotSTy")


def lookup_long(name):
    exact = [o for o in LONG_OPTS if o[0] == name]
    if exact:
        return exact[0]
    cands = [o for o in LONG_OPTS if o[0].startswith(name)]
    if len(cands) == 1:
        return cands[0]
    raise UsageError("unrecognized or ambiguous option '--%s'" % name)


def parse_args(argv):
    opts = []   # list of (optchar, arg)
    files = []
    i = 0
    n = len(argv)
    while i < n:
        arg = argv[i]
        i += 1
        if arg == "--":
            files.extend(argv[i:])
            break
        if arg.startswith("--"):
            body = arg[2:]
            if "=" in body:
                name, val = body.split("=", 1)
            else:
                name, val = body, None
            name, has_arg, short = lookup_long(name)
            if has_arg == 1 and val is None:
                if i >= n:
                    raise UsageError("option requires an argument")
                val = argv[i]
                i += 1
            elif has_arg == 0 and val is not None:
                raise UsageError("option doesn't allow an argument")
            opts.append((short, val))
            continue
        if arg.startswith("-") and len(arg) > 1:
            j = 1
            while j < len(arg):
                c = arg[j]
                j += 1
                if c in SHORT_NOARG:
                    opts.append((c, None))
                elif c in SHORT_ARG:
                    if j < len(arg):
                        val = arg[j:]
                    else:
                        if i >= n:
                            raise UsageError("option requires an argument -- '%s'" % c)
                        val = argv[i]
                        i += 1
                    opts.append((c, val))
                    break
                else:
                    raise UsageError("invalid option -- '%s'" % c)
            continue
        files.append(arg)
    return opts, files


# ---------------------------------------------------------------------------
# I/O

def read_lines(data, eol):
    if not data:
        return []
    parts = data.split(eol)
    if parts[-1] == b"":
        parts.pop()
    return parts


def read_input(name):
    if name == "-":
        return sys.stdin.buffer.read()
    try:
        with open(name, "rb") as f:
            return f.read()
    except OSError as e:
        die("cannot read: %s: %s" % (name, e.strerror or "error"))


def main(argv):
    try:
        opts, files = parse_args(argv)
    except UsageError as e:
        sys.stderr.write("%s: %s\n" % (PROG, e))
        return 2

    gkey = Key()
    keys = []
    tab = None
    unique = False
    stable = False
    check = None
    eol = b"\n"
    output = None

    try:
        for c, val in opts:
            if c in ("b", "d", "f", "g", "h", "i", "M", "n", "r", "R", "V"):
                set_ordering(c, 0, gkey, "global")
            elif c == "sort":
                m = {"general-numeric": "g", "human-numeric": "h",
                     "month": "M", "numeric": "n", "random": "R",
                     "version": "V"}
                if val not in m:
                    raise UsageError("invalid argument for --sort")
                set_ordering(m[val], 0, gkey, "global")
            elif c == "k":
                keys.append(parse_key(val))
            elif c == "t":
                v = os.fsencode(val)
                if not v:
                    raise UsageError("empty tab")
                if len(v) > 1:
                    if v == b"\\0":
                        v = b"\0"
                    else:
                        raise UsageError("multi-character tab")
                if tab is not None and tab != v[0]:
                    raise UsageError("incompatible tabs")
                tab = v[0]
            elif c == "u":
                unique = True
            elif c == "s":
                stable = True
            elif c == "c":
                check = "c"
            elif c == "C":
                check = "C"
            elif c == "check":
                if val is None or val == "diagnose-first":
                    check = "c"
                elif val in ("quiet", "silent"):
                    check = "C"
                else:
                    raise UsageError("invalid argument for --check")
            elif c == "z":
                eol = b"\0"
            elif c == "o":
                output = val
            elif c in ("help", "version"):
                if c == "version":
                    sys.stdout.write("sort (GNU coreutils) 9.1\n")
                return 0
            # m, S, T, y, debug, etc.: ignored
    except UsageError as e:
        sys.stderr.write("%s: %s\n" % (PROG, e))
        return 2

    # Inherit global options into keys with none of their own.
    for key in keys:
        if key.is_default() and not key.reverse:
            key.ignore = gkey.ignore
            key.translate = gkey.translate
            key.skipsblanks = gkey.skipsblanks
            key.skipeblanks = gkey.skipeblanks
            key.month = gkey.month
            key.numeric = gkey.numeric
            key.general_numeric = gkey.general_numeric
            key.human_numeric = gkey.human_numeric
            key.version = gkey.version
            key.random = gkey.random
            key.reverse = gkey.reverse
    if not keys and not gkey.is_default():
        gkey.sword = None
        gkey.schar = 0
        gkey.eword = None
        gkey.echar = 0
        keys.append(gkey)

    sorter = Sorter(keys, tab, gkey.reverse, unique, stable)

    if not files:
        files = ["-"]

    if check:
        if len(files) > 1:
            sys.stderr.write("%s: extra operand '%s' not allowed with -%s\n"
                             % (PROG, files[1], check))
            return 2
        data = read_input(files[0])
        lines = read_lines(data, eol)
        limit = 0 if unique else 1  # disorder when compare >= limit
        for idx in range(1, len(lines)):
            if sorter.compare(lines[idx - 1], lines[idx]) >= limit:
                if check == "c":
                    sys.stderr.write("%s: %s:%d: disorder: %s\n" % (
                        PROG, files[0], idx + 1,
                        lines[idx].decode("latin-1")))
                return 1
        return 0

    lines = []
    for name in files:
        lines.extend(read_lines(read_input(name), eol))

    lines.sort(key=cmp_to_key(sorter.compare))

    out = []
    if unique:
        prev = None
        for ln in lines:
            if prev is not None and sorter.compare(prev, ln) == 0:
                continue
            prev = ln
            out.append(ln)
    else:
        out = lines

    payload = b"".join(ln + eol for ln in out)
    if output is not None and output != "-":
        try:
            with open(output, "wb") as f:
                f.write(payload)
        except OSError as e:
            die("open failed: %s: %s" % (output, e.strerror))
    else:
        sys.stdout.buffer.write(payload)
        sys.stdout.buffer.flush()
    return 0


if __name__ == "__main__":
    try:
        rc = main(sys.argv[1:])
    except BrokenPipeError:
        rc = 2
    sys.exit(rc)
