"""pysort: a GNU sort 9.1 replacement in pure Python.

Usage: python3 /app/pysort/sort.py [OPTION]... [FILE]...

Behaves like GNU sort 9.1 run with LC_ALL=C.
"""

import os
import sys
import hashlib
from decimal import Decimal
from fractions import Fraction
from functools import cmp_to_key

try:
    sys.set_int_max_str_digits(0)
except AttributeError:  # pragma: no cover
    pass

SIZE_MAX = (1 << 64) - 1
SORT_FAILURE = 2
SORT_OUT_OF_ORDER = 1

PROG = "sort"


class SortError(Exception):
    pass


def die(msg):
    raise SortError(msg)


# ---------------------------------------------------------------------------
# Character tables (C locale)

BLANKS = [False] * 256
for _c in (0x20, 0x09, 0x0A):
    BLANKS[_c] = True


def _isalnum(c):
    return (0x30 <= c <= 0x39) or (0x41 <= c <= 0x5A) or (0x61 <= c <= 0x7A)


def _isalpha(c):
    return (0x41 <= c <= 0x5A) or (0x61 <= c <= 0x7A)


def _isdigit(c):
    return 0x30 <= c <= 0x39


NONPRINTING = bytes(c for c in range(256) if not (0x20 <= c <= 0x7E))
NONDICTIONARY = bytes(c for c in range(256)
                      if not _isalnum(c) and not BLANKS[c])
FOLD_TOUPPER = bytes((c - 32) if 0x61 <= c <= 0x7A else c for c in range(256))
IDENTITY = bytes(range(256))

MONTHS = {b"JAN": 1, b"FEB": 2, b"MAR": 3, b"APR": 4, b"MAY": 5, b"JUN": 6,
          b"JUL": 7, b"AUG": 8, b"SEP": 9, b"OCT": 10, b"NOV": 11, b"DEC": 12}

UNIT_ORDER = [0] * 256
for _ch, _o in zip(b"KMGTPEZY", range(1, 9)):
    UNIT_ORDER[_ch] = _o
UNIT_ORDER[ord("k")] = 1


# ---------------------------------------------------------------------------
# Key description

class Key:
    __slots__ = ("sword", "schar", "eword", "echar", "skipsblanks",
                 "skipeblanks", "ignore", "translate", "numeric",
                 "general_numeric", "human_numeric", "month", "random",
                 "version", "reverse")

    def __init__(self):
        self.sword = 0
        self.schar = 0
        self.eword = SIZE_MAX
        self.echar = 0
        self.skipsblanks = False
        self.skipeblanks = False
        self.ignore = None
        self.translate = None
        self.numeric = False
        self.general_numeric = False
        self.human_numeric = False
        self.month = False
        self.random = False
        self.version = False
        self.reverse = False

    def default_compare(self):
        return not (self.ignore or self.translate or self.skipsblanks
                    or self.skipeblanks or self.numeric
                    or self.general_numeric or self.human_numeric
                    or self.month or self.version or self.random)


def set_ordering(s, pos, key, blanktype):
    """Apply ordering letters in s starting at pos; return index of first
    unrecognized character.  blanktype: 'start', 'end' or 'both'."""
    n = len(s)
    while pos < n:
        c = s[pos]
        if c == "b":
            if blanktype in ("start", "both"):
                key.skipsblanks = True
            if blanktype in ("end", "both"):
                key.skipeblanks = True
        elif c == "d":
            key.ignore = NONDICTIONARY
        elif c == "f":
            key.translate = FOLD_TOUPPER
        elif c == "g":
            key.general_numeric = True
        elif c == "h":
            key.human_numeric = True
        elif c == "i":
            if not key.ignore:
                key.ignore = NONPRINTING
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
            return pos
        pos += 1
    return pos


def parse_field_count(s, pos, msgid, spec):
    """Parse a decimal count at s[pos:].  Returns (value, newpos).
    If there is no number: error (or (None, pos) if msgid is None)."""
    start = pos
    n = len(s)
    while pos < n and "0" <= s[pos] <= "9":
        pos += 1
    if pos == start:
        if msgid is None:
            return None, pos
        die("%s: invalid field specification '%s'" % (msgid, spec))
    val = int(s[start:pos])
    if val > SIZE_MAX:
        val = SIZE_MAX
    return val, pos


def badfieldspec(spec, msg):
    die("%s: invalid field specification '%s'" % (msg, spec))


def parse_key_spec(spec):
    key = Key()
    v, pos = parse_field_count(spec, 0, "invalid number at field start", spec)
    if v == 0:
        badfieldspec(spec, "field number is zero")
    key.sword = v - 1
    if pos < len(spec) and spec[pos] == ".":
        v, pos = parse_field_count(spec, pos + 1,
                                   "invalid number after '.'", spec)
        if v == 0:
            badfieldspec(spec, "character offset is zero")
        key.schar = v - 1
    if not (key.sword or key.schar):
        key.sword = SIZE_MAX
    pos = set_ordering(spec, pos, key, "start")
    if pos >= len(spec) or spec[pos] != ",":
        key.eword = SIZE_MAX
        key.echar = 0
    else:
        v, pos = parse_field_count(spec, pos + 1,
                                   "invalid number after ','", spec)
        if v == 0:
            badfieldspec(spec, "field number is zero")
        key.eword = v - 1
        if pos < len(spec) and spec[pos] == ".":
            v, pos = parse_field_count(spec, pos + 1,
                                       "invalid number after '.'", spec)
            key.echar = v
        pos = set_ordering(spec, pos, key, "end")
    if pos < len(spec):
        badfieldspec(spec, "stray character in field spec")
    return key


def parse_obsolete_key(arg, nextarg):
    """Parse +POS1 [-POS2].  Returns (key or None, consumed_next)."""
    key = Key()
    v, pos = parse_field_count(arg, 1, None, arg)
    if v is None:
        return None, False
    key.sword = v
    if pos < len(arg) and arg[pos] == ".":
        v, pos = parse_field_count(arg, pos + 1, None, arg)
        if v is None:
            return None, False
        key.schar = v
    if not (key.sword or key.schar):
        key.sword = SIZE_MAX
    pos = set_ordering(arg, pos, key, "start")
    if pos < len(arg):
        return None, False
    if nextarg is not None:
        v, pos = parse_field_count(nextarg, 1, "invalid number after '-'",
                                   nextarg)
        key.eword = v
        if pos < len(nextarg) and nextarg[pos] == ".":
            v, pos = parse_field_count(nextarg, pos + 1,
                                       "invalid number after '.'", nextarg)
            key.echar = v
        if not key.echar and key.eword:
            key.eword -= 1
        pos = set_ordering(nextarg, pos, key, "end")
        if pos < len(nextarg):
            badfieldspec(nextarg, "stray character in field spec")
        return key, True
    key.eword = SIZE_MAX
    return key, False


# ---------------------------------------------------------------------------
# Field location

def begfield(line, key, tab):
    ptr = 0
    lim = len(line)
    sword = key.sword
    if sword == SIZE_MAX:
        sword = 0
    if tab is not None:
        while ptr < lim and sword > 0:
            sword -= 1
            idx = line.find(tab, ptr)
            if idx < 0:
                ptr = lim
            else:
                ptr = idx + 1
    else:
        while ptr < lim and sword > 0:
            sword -= 1
            while ptr < lim and BLANKS[line[ptr]]:
                ptr += 1
            while ptr < lim and not BLANKS[line[ptr]]:
                ptr += 1
    if key.skipsblanks:
        while ptr < lim and BLANKS[line[ptr]]:
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
            idx = line.find(tab, ptr)
            if idx < 0:
                ptr = lim
            else:
                ptr = idx
            if ptr < lim and (eword or echar):
                ptr += 1
    else:
        while ptr < lim and eword > 0:
            eword -= 1
            while ptr < lim and BLANKS[line[ptr]]:
                ptr += 1
            while ptr < lim and not BLANKS[line[ptr]]:
                ptr += 1
    if echar != 0:
        if key.skipeblanks:
            while ptr < lim and BLANKS[line[ptr]]:
                ptr += 1
        ptr = min(lim, ptr + echar)
    return ptr


def extract_key(line, key, tab):
    if key.eword != SIZE_MAX:
        lim = limfield(line, key, tab)
    else:
        lim = len(line)
    beg = begfield(line, key, tab)
    if lim < beg:
        lim = beg
    return line[beg:lim]


# ---------------------------------------------------------------------------
# Value parsers

def parse_numeric(t):
    """Value of the leading number as used by -n (exact)."""
    i = 0
    n = len(t)
    while i < n and BLANKS[t[i]]:
        i += 1
    neg = False
    if i < n and t[i] == 0x2D:
        neg = True
        i += 1
    s = i
    while i < n and _isdigit(t[i]):
        i += 1
    ip = t[s:i]
    fp = b""
    if i < n and t[i] == 0x2E:
        i += 1
        s = i
        while i < n and _isdigit(t[i]):
            i += 1
        fp = t[s:i]
    txt = (ip or b"0") + b"." + (fp or b"0")
    d = Decimal(txt.decode("ascii"))
    if neg:
        d = -d
    return d


def find_unit_order(t, i):
    n = len(t)
    minus = i < n and t[i] == 0x2D
    p = i + (1 if minus else 0)
    nonzero = False
    ch = 0
    while True:
        if p < n and _isdigit(t[p]):
            if t[p] != 0x30:
                nonzero = True
            p += 1
            continue
        ch = t[p] if p < n else 0
        p += 1
        break
    # thousands_sep is not a character in the C locale
    if ch == 0x2E:
        while True:
            if p < n and _isdigit(t[p]):
                if t[p] != 0x30:
                    nonzero = True
                p += 1
                continue
            ch = t[p] if p < n else 0
            p += 1
            break
    if nonzero:
        order = UNIT_ORDER[ch]
        return -order if minus else order
    return 0


def parse_human(t):
    i = 0
    n = len(t)
    while i < n and BLANKS[t[i]]:
        i += 1
    return (find_unit_order(t, i), parse_numeric(t[i:]))


def getmonth(t):
    i = 0
    n = len(t)
    while i < n and BLANKS[t[i]]:
        i += 1
    m = t[i:i + 3].translate(FOLD_TOUPPER)
    return MONTHS.get(m, 0)


# long double emulation (x86 80-bit extended: 64-bit significand)
LD_MANT = 64
LD_MIN_EXP = -16445   # exponent of the smallest subnormal quantum
LD_MAX = 1 << 16384


def _round_ld(q):
    """Round positive Fraction q to the nearest long double.  Returns a
    Fraction, or None for overflow to infinity."""
    num, den = q.numerator, q.denominator
    e = num.bit_length() - den.bit_length()
    # ensure 2^e <= q < 2^(e+1)
    if (num << max(0, -e)) < (den << max(0, e)):
        e -= 1
    sh = e - (LD_MANT - 1)
    if sh < LD_MIN_EXP:
        sh = LD_MIN_EXP
    # m = round_half_even(q / 2^sh)
    if sh >= 0:
        n2, d2 = num, den << sh
    else:
        n2, d2 = num << (-sh), den
    m, r = divmod(n2, d2)
    if 2 * r > d2 or (2 * r == d2 and (m & 1)):
        m += 1
    if m == 0:
        return Fraction(0)
    val = Fraction(m) * (Fraction(2) ** sh)
    if val >= LD_MAX:
        return None
    return val


SPACE_BYTES = b" \t\n\v\f\r"
HEXDIGITS = b"0123456789abcdefABCDEF"


def parse_general(t):
    """Emulate strtold on t.  Returns a comparable tuple:
    (0,) conversion error; (1, 0) -nan; (1, 1) nan; (2, -1) -inf;
    (2, 0, value) finite; (2, 1) +inf."""
    n = len(t)
    i = 0
    while i < n and t[i] in SPACE_BYTES:
        i += 1
    neg = False
    if i < n and t[i] in b"+-":
        neg = t[i] == 0x2D
        i += 1
    low = t[i:i + 3].lower()
    if low == b"inf":
        return (2, -1) if neg else (2, 1)
    if low == b"nan":
        return (1, 0) if neg else (1, 1)
    # hexadecimal
    if (t[i:i + 2].lower() == b"0x"):
        j = i + 2
        hs = j
        while j < n and t[j] in HEXDIGITS:
            j += 1
        ipart = t[hs:j]
        fpart = b""
        if j < n and t[j] == 0x2E:
            k = j + 1
            while k < n and t[k] in HEXDIGITS:
                k += 1
            fpart = t[j + 1:k]
            if ipart or fpart:
                j = k
        if ipart or fpart:
            mant = int((ipart + fpart).decode("ascii") or "0", 16)
            exp = -4 * len(fpart)
            if j < n and t[j] in b"pP":
                k = j + 1
                esign = 1
                if k < n and t[k] in b"+-":
                    esign = -1 if t[k] == 0x2D else 1
                    k += 1
                es = k
                while k < n and _isdigit(t[k]):
                    k += 1
                if k > es:
                    ev = int(t[es:k])
                    if ev > 100000:
                        ev = 100000
                    exp += esign * ev
            if mant == 0:
                return (2, 0, Fraction(0))
            bits = mant.bit_length() + exp
            if bits > 16400:
                return (2, -1) if neg else (2, 1)
            if bits < -16500:
                return (2, 0, Fraction(0))
            q = Fraction(mant) * (Fraction(2) ** exp)
            v = _round_ld(q)
            if v is None:
                return (2, -1) if neg else (2, 1)
            return (2, 0, -v if neg else v)
        # "0x" without hex digits: parse "0" as decimal below
    j = i
    ds = j
    while j < n and _isdigit(t[j]):
        j += 1
    ipart = t[ds:j]
    fpart = b""
    if j < n and t[j] == 0x2E:
        k = j + 1
        while k < n and _isdigit(t[k]):
            k += 1
        fpart = t[j + 1:k]
        if ipart or fpart:
            j = k
    if not (ipart or fpart):
        return (0,)
    exp = -len(fpart)
    if j < n and t[j] in b"eE":
        k = j + 1
        esign = 1
        if k < n and t[k] in b"+-":
            esign = -1 if t[k] == 0x2D else 1
            k += 1
        es = k
        while k < n and _isdigit(t[k]):
            k += 1
        if k > es:
            ev = int(t[es:k])
            if ev > 100000:
                ev = 100000
            exp += esign * ev
    digits = (ipart + fpart).lstrip(b"0")
    if not digits:
        return (2, 0, Fraction(0))
    mant = int(digits)
    mag = len(digits) + exp  # value < 10^mag
    if mag > 4940:
        return (2, -1) if neg else (2, 1)
    if mag < -4960:
        return (2, 0, Fraction(0))
    if exp >= 0:
        q = Fraction(mant * 10 ** exp)
    else:
        q = Fraction(mant, 10 ** (-exp))
    v = _round_ld(q)
    if v is None:
        return (2, -1) if neg else (2, 1)
    return (2, 0, -v if neg else v)


# ---------------------------------------------------------------------------
# Version comparison (gnulib filevercmp, 2022)

def _file_prefixlen(s, n):
    prefixlen = 0
    i = 0
    while True:
        if i == n:
            return prefixlen
        i += 1
        prefixlen = i
        while i + 1 < n and s[i] == 0x2E and (_isalpha(s[i + 1])
                                               or s[i + 1] == 0x7E):
            i += 2
            while i < n and (_isalnum(s[i]) or s[i] == 0x7E):
                i += 1


def _order(s, pos, length):
    if pos == length:
        return -1
    c = s[pos]
    if _isdigit(c):
        return 0
    if _isalpha(c):
        return c
    if c == 0x7E:
        return -2
    return c + 256


def _verrevcmp(s1, l1, s2, l2):
    p1 = 0
    p2 = 0
    while p1 < l1 or p2 < l2:
        first_diff = 0
        while ((p1 < l1 and not _isdigit(s1[p1]))
               or (p2 < l2 and not _isdigit(s2[p2]))):
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
        while (p1 < l1 and p2 < l2 and _isdigit(s1[p1])
               and _isdigit(s2[p2])):
            if not first_diff:
                first_diff = s1[p1] - s2[p2]
            p1 += 1
            p2 += 1
        if p1 < l1 and _isdigit(s1[p1]):
            return 1
        if p2 < l2 and _isdigit(s2[p2]):
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
            return 0 if bdot else -1
        if bdot:
            return 1
        adotdot = a[1] == 0x2E and alen == 2
        bdotdot = b[1] == 0x2E and blen == 2
        if adotdot:
            return 0 if bdotdot else -1
        if bdotdot:
            return 1
    elif b[0] == 0x2E:
        return 1
    ap = _file_prefixlen(a, alen)
    bp = _file_prefixlen(b, blen)
    one_pass_only = ap == alen and bp == blen
    result = _verrevcmp(a, ap, b, bp)
    if result or one_pass_only:
        return result
    return _verrevcmp(a, alen, b, blen)


# ---------------------------------------------------------------------------
# Comparison machinery

def _cmp(x, y):
    return (x > y) - (x < y)


class Sorter:
    def __init__(self, keys, tab, unique, stable, reverse, random_salt):
        self.keys = keys
        self.tab = tab
        self.unique = unique
        self.stable = stable
        self.reverse = reverse
        self.salt = random_salt
        self.kfuncs = []
        for key in keys:
            self.kfuncs.append(self._make_keyfunc(key))

    def _make_keyfunc(self, key):
        tab = self.tab
        ignore = key.ignore
        translate = key.translate

        def transform(line):
            t = extract_key(line, key, tab)
            if ignore is not None or translate is not None:
                t = t.translate(translate if translate is not None
                                else IDENTITY, ignore if ignore else b"")
            return t

        if key.numeric:
            return (lambda line: parse_numeric(transform(line))), _cmp
        if key.general_numeric:
            return (lambda line: parse_general(transform(line))), _cmp
        if key.human_numeric:
            return (lambda line: parse_human(transform(line))), _cmp
        if key.month:
            return (lambda line: getmonth(transform(line))), _cmp
        if key.random:
            salt = self.salt

            def rnd(line):
                t = transform(line)
                return (hashlib.md5(salt + t).digest(), t)
            return rnd, _cmp
        if key.version:
            return transform, filenvercmp
        return transform, _cmp

    def prepare(self, lines):
        out = []
        for ln in lines:
            vals = [f(ln) for f, _ in self.kfuncs]
            out.append((ln, vals))
        return out

    def compare(self, a, b):
        if self.keys:
            av = a[1]
            bv = b[1]
            for i, key in enumerate(self.keys):
                d = self.kfuncs[i][1](av[i], bv[i])
                if d:
                    return -d if key.reverse else d
            if self.unique or self.stable:
                return 0
        d = _cmp(a[0], b[0])
        return -d if self.reverse else d


# ---------------------------------------------------------------------------
# Option parsing

LONG_OPTIONS = [
    ("ignore-leading-blanks", 0, "b"),
    ("check", 2, "check"),
    ("compress-program", 1, "compress-program"),
    ("debug", 0, "debug"),
    ("dictionary-order", 0, "d"),
    ("ignore-case", 0, "f"),
    ("files0-from", 1, "files0-from"),
    ("general-numeric-sort", 0, "g"),
    ("ignore-nonprinting", 0, "i"),
    ("key", 1, "k"),
    ("merge", 0, "m"),
    ("month-sort", 0, "M"),
    ("numeric-sort", 0, "n"),
    ("human-numeric-sort", 0, "h"),
    ("version-sort", 0, "V"),
    ("random-sort", 0, "R"),
    ("random-source", 1, "random-source"),
    ("sort", 1, "sort"),
    ("output", 1, "o"),
    ("reverse", 0, "r"),
    ("stable", 0, "s"),
    ("batch-size", 1, "batch-size"),
    ("buffer-size", 1, "S"),
    ("field-separator", 1, "t"),
    ("temporary-directory", 1, "T"),
    ("unique", 0, "u"),
    ("zero-terminated", 0, "z"),
    ("parallel", 1, "parallel"),
    ("help", 0, "help"),
    ("version", 0, "version"),
]

SHORT_NOARG = set("bcCdfghimMnrRsuVz")
SHORT_ARG = set("koStTy")

SORT_TYPES = {
    "general-numeric": "g", "human-numeric": "h", "month": "M",
    "numeric": "n", "random": "R", "version": "V",
}


def match_long(name):
    for ln, has, code in LONG_OPTIONS:
        if ln == name:
            return ln, has, code
    cands = [o for o in LONG_OPTIONS if o[0].startswith(name)]
    if len(cands) == 1:
        return cands[0]
    if not cands:
        die("unrecognized option '--%s'" % name)
    # ambiguous unless all candidates are identical in effect
    if all(c[1:] == cands[0][1:] for c in cands):
        return cands[0]
    die("option '--%s' is ambiguous" % name)


def match_argmatch(value, table, what):
    if value in table:
        return table[value]
    cands = [k for k in table if k.startswith(value)]
    vals = set(table[k] for k in cands)
    if len(vals) == 1 and value:
        return vals.pop()
    die("invalid argument '%s' for '--%s'" % (value, what))


class Config:
    def __init__(self):
        self.gkey = Key()
        self.keys = []
        self.files = []
        self.checkonly = None
        self.merge = False
        self.unique = False
        self.stable = False
        self.zero = False
        self.tab = None
        self.outfile = None
        self.files0_from = None
        self.mode_exit = None


def handle_option(cfg, code, optarg):
    if code in ("b", "d", "f", "g", "h", "i", "M", "n", "r", "R", "V"):
        set_ordering(code, 0, cfg.gkey, "both")
    elif code in ("c", "C", "check"):
        if code == "check":
            if optarg is None:
                c = "c"
            else:
                c = match_argmatch(optarg, {"quiet": "C", "silent": "C",
                                            "diagnose-first": "c"}, "check")
        else:
            c = code
        if cfg.checkonly and cfg.checkonly != c:
            die("options '-cC' are incompatible")
        cfg.checkonly = c
    elif code == "sort":
        c = match_argmatch(optarg, SORT_TYPES, "sort")
        set_ordering(c, 0, cfg.gkey, "both")
    elif code == "k":
        cfg.keys.append(parse_key_spec(optarg))
    elif code == "m":
        cfg.merge = True
    elif code == "o":
        if cfg.outfile is not None and cfg.outfile != optarg:
            die("multiple output files specified")
        cfg.outfile = optarg
    elif code == "s":
        cfg.stable = True
    elif code == "t":
        b = os.fsencode(optarg)
        if not b:
            die("empty tab")
        newtab = b[0:1]
        if len(b) > 1:
            if b == b"\\0":
                newtab = b"\0"
            else:
                die("multi-character tab '%s'" % optarg)
        if cfg.tab is not None and cfg.tab != newtab:
            die("incompatible tabs")
        cfg.tab = newtab
    elif code == "u":
        cfg.unique = True
    elif code == "z":
        cfg.zero = True
    elif code == "files0-from":
        cfg.files0_from = optarg
    elif code == "help":
        cfg.mode_exit = "help"
    elif code == "version":
        cfg.mode_exit = "version"
    # S, T, y, parallel, batch-size, compress-program, random-source,
    # debug: accepted and ignored.


def parse_args(argv):
    cfg = Config()
    i = 0
    n = len(argv)
    while i < n:
        arg = argv[i]
        i += 1
        if arg == "--":
            cfg.files.extend(argv[i:])
            break
        if arg.startswith("--"):
            body = arg[2:]
            if "=" in body:
                name, val = body.split("=", 1)
            else:
                name, val = body, None
            ln, has, code = match_long(name)
            if has == 0:
                if val is not None:
                    die("option '--%s' doesn't allow an argument" % ln)
                handle_option(cfg, code, None)
            elif has == 1:
                if val is None:
                    if i >= n:
                        die("option '--%s' requires an argument" % ln)
                    val = argv[i]
                    i += 1
                handle_option(cfg, code, val)
            else:
                handle_option(cfg, code, val)
            continue
        if arg.startswith("-") and arg != "-":
            j = 1
            while j < len(arg):
                c = arg[j]
                j += 1
                if c in SHORT_NOARG:
                    handle_option(cfg, c, None)
                elif c in SHORT_ARG:
                    if j < len(arg):
                        val = arg[j:]
                    else:
                        if i >= n:
                            die("option requires an argument -- '%s'" % c)
                        val = argv[i]
                        i += 1
                    handle_option(cfg, c, val)
                    break
                else:
                    die("invalid option -- '%s'" % c)
            continue
        # operand
        key = None
        if arg.startswith("+"):
            minus_pos = (i < n and len(argv[i]) > 1 and argv[i][0] == "-"
                         and argv[i][1].isdigit())
            if minus_pos and not os.environ.get("POSIXLY_CORRECT"):
                key, used = parse_obsolete_key(arg, argv[i])
                if key is not None and used:
                    i += 1
        if key is not None:
            cfg.keys.append(key)
        else:
            cfg.files.append(arg)
    return cfg


# ---------------------------------------------------------------------------
# I/O

def read_file(name):
    if name == "-":
        return sys.stdin.buffer.read()
    try:
        with open(name, "rb") as fh:
            return fh.read()
    except OSError as e:
        die("cannot read: %s: %s" % (name, e.strerror))


def split_lines(data, delim):
    if not data:
        return []
    parts = data.split(delim)
    if parts[-1] == b"":
        parts.pop()
    return parts


def run(argv):
    cfg = parse_args(argv)
    if cfg.mode_exit == "help":
        sys.stdout.write("Usage: sort [OPTION]... [FILE]...\n")
        return 0
    if cfg.mode_exit == "version":
        sys.stdout.write("sort (GNU coreutils) 9.1\n")
        return 0

    gkey = cfg.gkey
    for key in cfg.keys:
        if key.default_compare() and not key.reverse:
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
    keys = list(cfg.keys)
    if not keys and not gkey.default_compare():
        keys = [gkey]

    for key in keys:
        cnt = (int(key.numeric) + int(key.general_numeric)
               + int(key.human_numeric) + int(key.month)
               + int(bool(key.version or key.random or key.ignore)))
        if cnt > 1:
            die("options are incompatible")

    files = list(cfg.files)
    if cfg.files0_from is not None:
        if files:
            die("extra operand '%s'" % files[0])
        data = read_file(cfg.files0_from)
        names = split_lines(data, b"\0")
        for nm in names:
            if not nm:
                die("invalid zero-length file name")
        files = [os.fsdecode(nm) for nm in names]
        if not files:
            die("no input from '%s'" % cfg.files0_from)
    if not files:
        files = ["-"]

    delim = b"\0" if cfg.zero else b"\n"
    salt = os.urandom(16)
    sorter = Sorter(keys, cfg.tab, cfg.unique, cfg.stable, gkey.reverse,
                    salt)

    if cfg.checkonly:
        if len(files) > 1:
            die("extra operand '%s' not allowed with -%s"
                % (files[1], cfg.checkonly))
        if cfg.outfile is not None:
            die("options '-%so' are incompatible" % cfg.checkonly)
        lines = split_lines(read_file(files[0]), delim)
        prep = sorter.prepare(lines)
        threshold = 0 if cfg.unique else 1
        for idx in range(1, len(prep)):
            if sorter.compare(prep[idx - 1], prep[idx]) >= threshold:
                if cfg.checkonly == "c":
                    sys.stderr.buffer.write(
                        ("%s: %s:%d: disorder: " % (PROG, files[0], idx + 1))
                        .encode("utf-8", "surrogateescape")
                        + prep[idx][0] + b"\n")
                return SORT_OUT_OF_ORDER
        return 0

    cmp = sorter.compare
    if cfg.merge:
        inputs = [sorter.prepare(split_lines(read_file(f), delim))
                  for f in files]
        result = []
        pos = [0] * len(inputs)
        while True:
            best = -1
            for fi, lst in enumerate(inputs):
                if pos[fi] < len(lst):
                    if best < 0 or cmp(lst[pos[fi]],
                                       inputs[best][pos[best]]) < 0:
                        best = fi
            if best < 0:
                break
            result.append(inputs[best][pos[best]])
            pos[best] += 1
    else:
        lines = []
        for f in files:
            lines.extend(split_lines(read_file(f), delim))
        result = sorter.prepare(lines)
        result.sort(key=cmp_to_key(cmp))

    if cfg.unique:
        out = []
        saved = None
        for item in result:
            if saved is not None and cmp(item, saved) == 0:
                continue
            saved = item
            out.append(item)
        result = out

    payload = b"".join(item[0] + delim for item in result)
    if cfg.outfile is not None:
        try:
            with open(cfg.outfile, "wb") as fh:
                fh.write(payload)
        except OSError as e:
            die("open failed: %s: %s" % (cfg.outfile, e.strerror))
    else:
        sys.stdout.buffer.write(payload)
        sys.stdout.buffer.flush()
    return 0


def main(argv):
    try:
        return run(argv)
    except SortError as e:
        try:
            sys.stdout.flush()
        except Exception:
            pass
        sys.stderr.write("%s: %s\n" % (PROG, e))
        return SORT_FAILURE
    except BrokenPipeError:
        try:
            sys.stdout = None
        except Exception:
            pass
        return SORT_FAILURE


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
