"""pydate: a GNU date 9.1 replacement in pure Python (display only).

Usage: python3 /app/pydate/date.py [OPTION]... [+FORMAT]

The behaviour mirrors coreutils 9.1 `date` (with gnulib's parse-datetime
and nstrftime) running with LC_ALL=C and TZ=UTC0.
"""

import os
import sys
import time

INT_MAX = 2 ** 31 - 1
INT_MIN = -(2 ** 31)
I64_MAX = 2 ** 63 - 1
I64_MIN = -(2 ** 63)
BILLION = 1000000000


class Fail(Exception):
    pass


def fits_int(v):
    return INT_MIN <= v <= INT_MAX


def fits_i64(v):
    return I64_MIN <= v <= I64_MAX


def cdiv(a, b):
    q = abs(a) // abs(b)
    return q if (a >= 0) == (b > 0) else -q


def cmod(a, b):
    return a - b * cdiv(a, b)


# ---------------------------------------------------------------------------
# Calendar arithmetic (proleptic Gregorian, arbitrary integers)
# ---------------------------------------------------------------------------

def days_from_civil(y, m, d):
    y -= 1 if m <= 2 else 0
    era = y // 400
    yoe = y - era * 400
    mp = (m + 9) % 12
    doy = (153 * mp + 2) // 5 + d - 1
    doe = yoe * 365 + yoe // 4 - yoe // 100 + doy
    return era * 146097 + doe - 719468


def civil_from_days(z):
    z += 719468
    era = z // 146097
    doe = z - era * 146097
    yoe = (doe - doe // 1460 + doe // 36524 - doe // 146096) // 365
    y = yoe + era * 400
    doy = doe - (365 * yoe + yoe // 4 - yoe // 100)
    mp = (5 * doy + 2) // 153
    d = doy - (153 * mp + 2) // 5 + 1
    m = mp + 3 if mp < 10 else mp - 9
    return (y + 1 if m <= 2 else y), m, d


def isleap(y):
    return y % 4 == 0 and (y % 100 != 0 or y % 400 == 0)


def days_in_month(y, m):
    if m == 2:
        return 29 if isleap(y) else 28
    return 31 if m in (1, 3, 5, 7, 8, 10, 12) else 30


class TM(object):
    __slots__ = ('year', 'mon', 'mday', 'hour', 'min', 'sec', 'wday',
                 'yday', 'gmtoff', 'zone', 'isdst')

    def copy(self):
        t = TM()
        for k in TM.__slots__:
            setattr(t, k, getattr(self, k))
        return t


def gmtime_fields(t):
    days, secs = divmod(t, 86400)
    y, m, d = civil_from_days(days)
    tm = TM()
    tm.year = y
    tm.mon = m - 1
    tm.mday = d
    tm.hour = secs // 3600
    tm.min = secs % 3600 // 60
    tm.sec = secs % 60
    tm.wday = (days + 4) % 7
    tm.yday = days - days_from_civil(y, 1, 1)
    tm.gmtoff = 0
    tm.zone = 'UTC'
    tm.isdst = 0
    return tm


def timegm_fields(year, mon, mday, hour, minute, sec):
    y = year + mon // 12
    m0 = mon % 12
    days = days_from_civil(y, m0 + 1, 1) + mday - 1
    return days * 86400 + hour * 3600 + minute * 60 + sec


# ---------------------------------------------------------------------------
# Time zones (only needed for TZ="..." inside date strings)
# ---------------------------------------------------------------------------

class Zone(object):
    """Fixed offset zone (seconds east of UTC)."""

    def __init__(self, off=0, name='UTC', zi=None):
        self.off = off
        self.name = name
        self.zi = zi

    def offset_at(self, t):
        if self.zi is None:
            return self.off, self.name
        try:
            import datetime
            dt = datetime.datetime.fromtimestamp(t, datetime.timezone.utc)
            loc = dt.astimezone(self.zi)
            return int(loc.utcoffset().total_seconds()), loc.tzname() or ''
        except Exception:
            return 0, 'UTC'

    def localtime(self, t):
        off, name = self.offset_at(t)
        tm = gmtime_fields(t + off)
        tm.gmtoff = off
        tm.zone = name
        return tm

    def mktime(self, year, mon, mday, hour, minute, sec):
        """Return (t, normalized tm) or None on overflow."""
        loc = timegm_fields(year, mon, mday, hour, minute, sec)
        off, _ = self.offset_at(loc)
        t = loc - off
        off2, _ = self.offset_at(t)
        if off2 != off:
            t = loc - off2
        if not fits_i64(t):
            return None
        tm = self.localtime(t)
        if not fits_int(tm.year - 1900):
            return None
        return t, tm


UTC = Zone(0, 'UTC')


def parse_posix_tz(s):
    i = 0
    n = len(s)
    if s.startswith(':'):
        return None
    if i < n and s[i] == '<':
        j = s.find('>', i)
        if j < 0:
            return None
        name = s[i + 1:j]
        i = j + 1
    else:
        j = i
        while j < n and s[j].isalpha() and s[j].isascii():
            j += 1
        name = s[i:j]
        if len(name) < 3:
            return None
        i = j
    sign = 1
    if i < n and s[i] in '+-':
        if s[i] == '-':
            sign = -1
        i += 1
    parts = []
    while True:
        j = i
        while j < n and s[j].isdigit() and s[j].isascii():
            j += 1
        if j == i:
            return None
        parts.append(int(s[i:j]))
        i = j
        if len(parts) < 3 and i < n and s[i] == ':':
            i += 1
            continue
        break
    while len(parts) < 3:
        parts.append(0)
    off = parts[0] * 3600 + parts[1] * 60 + parts[2]
    # POSIX offsets are west of UTC.  DST rules (if any) are ignored.
    return Zone(-sign * off, name)


def make_zone(tzstr):
    z = parse_posix_tz(tzstr)
    if z is not None and all(c not in tzstr for c in ',/'):
        return z
    try:
        import zoneinfo
        name = tzstr[1:] if tzstr.startswith(':') else tzstr
        zi = zoneinfo.ZoneInfo(name)
        return Zone(0, 'UTC', zi)
    except Exception:
        pass
    if z is not None:
        return z
    return Zone(0, 'UTC')


# ---------------------------------------------------------------------------
# Date string lexer (gnulib parse-datetime.y)
# ---------------------------------------------------------------------------

SPACES = ' \t\n\v\f\r'


def isdig(c):
    return '0' <= c <= '9'


def isalph(c):
    return ('a' <= c <= 'z') or ('A' <= c <= 'Z')


def HOUR(x):
    return x * 3600


MERIDIAN_TABLE = {'AM': 0, 'A.M.': 0, 'PM': 1, 'P.M.': 1}
MER_AM, MER_PM, MER24 = 0, 1, 2

MONTH_AND_DAY_TABLE = [
    ('JANUARY', 'MONTH', 1), ('FEBRUARY', 'MONTH', 2), ('MARCH', 'MONTH', 3),
    ('APRIL', 'MONTH', 4), ('MAY', 'MONTH', 5), ('JUNE', 'MONTH', 6),
    ('JULY', 'MONTH', 7), ('AUGUST', 'MONTH', 8), ('SEPTEMBER', 'MONTH', 9),
    ('SEPT', 'MONTH', 9), ('OCTOBER', 'MONTH', 10), ('NOVEMBER', 'MONTH', 11),
    ('DECEMBER', 'MONTH', 12), ('SUNDAY', 'DAY', 0), ('MONDAY', 'DAY', 1),
    ('TUESDAY', 'DAY', 2), ('TUES', 'DAY', 2), ('WEDNESDAY', 'DAY', 3),
    ('WEDNES', 'DAY', 3), ('THURSDAY', 'DAY', 4), ('THUR', 'DAY', 4),
    ('THURS', 'DAY', 4), ('FRIDAY', 'DAY', 5), ('SATURDAY', 'DAY', 6),
]

UNIVERSAL_ZONES = {'GMT': 0, 'UT': 0, 'UTC': 0}

TIME_ZONE_TABLE = [
    ('WET', 'ZONE', HOUR(0)), ('WEST', 'DAYZONE', HOUR(0)),
    ('BST', 'DAYZONE', HOUR(0)), ('ART', 'ZONE', -HOUR(3)),
    ('BRT', 'ZONE', -HOUR(3)), ('BRST', 'DAYZONE', -HOUR(3)),
    ('NST', 'ZONE', -(HOUR(3) + 30 * 60)),
    ('NDT', 'DAYZONE', -(HOUR(3) + 30 * 60)),
    ('AST', 'ZONE', -HOUR(4)), ('ADT', 'DAYZONE', -HOUR(4)),
    ('EST', 'ZONE', -HOUR(5)), ('EDT', 'DAYZONE', -HOUR(5)),
    ('CST', 'ZONE', -HOUR(6)), ('CDT', 'DAYZONE', -HOUR(6)),
    ('MST', 'ZONE', -HOUR(7)), ('MDT', 'DAYZONE', -HOUR(7)),
    ('PST', 'ZONE', -HOUR(8)), ('PDT', 'DAYZONE', -HOUR(8)),
    ('AKST', 'ZONE', -HOUR(9)), ('AKDT', 'DAYZONE', -HOUR(9)),
    ('HST', 'ZONE', -HOUR(10)), ('HAST', 'ZONE', -HOUR(10)),
    ('HADT', 'DAYZONE', -HOUR(10)), ('SST', 'ZONE', -HOUR(12)),
    ('WAT', 'ZONE', HOUR(1)), ('CET', 'ZONE', HOUR(1)),
    ('CEST', 'DAYZONE', HOUR(1)), ('MET', 'ZONE', HOUR(1)),
    ('MEZ', 'ZONE', HOUR(1)), ('MEST', 'DAYZONE', HOUR(1)),
    ('MESZ', 'DAYZONE', HOUR(1)), ('EET', 'ZONE', HOUR(2)),
    ('EEST', 'DAYZONE', HOUR(2)), ('CAT', 'ZONE', HOUR(2)),
    ('SAST', 'ZONE', HOUR(2)), ('EAT', 'ZONE', HOUR(3)),
    ('MSK', 'ZONE', HOUR(3)), ('MSD', 'DAYZONE', HOUR(3)),
    ('IST', 'ZONE', HOUR(5) + 30 * 60), ('SGT', 'ZONE', HOUR(8)),
    ('KST', 'ZONE', HOUR(9)), ('JST', 'ZONE', HOUR(9)),
    ('GST', 'ZONE', HOUR(10)), ('NZST', 'ZONE', HOUR(12)),
    ('NZDT', 'DAYZONE', HOUR(12)),
]

TIME_UNITS_TABLE = {
    'YEAR': ('YEAR_UNIT', 1), 'MONTH': ('MONTH_UNIT', 1),
    'FORTNIGHT': ('DAY_UNIT', 14), 'WEEK': ('DAY_UNIT', 7),
    'DAY': ('DAY_UNIT', 1), 'HOUR': ('HOUR_UNIT', 1),
    'MINUTE': ('MIN_UNIT', 1), 'MIN': ('MIN_UNIT', 1),
    'SECOND': ('SEC_UNIT', 1), 'SEC': ('SEC_UNIT', 1),
}

RELATIVE_TIME_TABLE = {
    'TOMORROW': ('DAY_SHIFT', 1), 'YESTERDAY': ('DAY_SHIFT', -1),
    'TODAY': ('DAY_SHIFT', 0), 'NOW': ('DAY_SHIFT', 0),
    'LAST': ('ORD', -1), 'THIS': ('ORD', 0), 'NEXT': ('ORD', 1),
    'FIRST': ('ORD', 1), 'THIRD': ('ORD', 3), 'FOURTH': ('ORD', 4),
    'FIFTH': ('ORD', 5), 'SIXTH': ('ORD', 6), 'SEVENTH': ('ORD', 7),
    'EIGHTH': ('ORD', 8), 'NINTH': ('ORD', 9), 'TENTH': ('ORD', 10),
    'ELEVENTH': ('ORD', 11), 'TWELFTH': ('ORD', 12),
    'AGO': ('AGO', -1), 'HENCE': ('AGO', 1),
}

MILITARY_TABLE = {
    'A': HOUR(1), 'B': HOUR(2), 'C': HOUR(3), 'D': HOUR(4), 'E': HOUR(5),
    'F': HOUR(6), 'G': HOUR(7), 'H': HOUR(8), 'I': HOUR(9), 'K': HOUR(10),
    'L': HOUR(11), 'M': HOUR(12), 'N': -HOUR(1), 'O': -HOUR(2),
    'P': -HOUR(3), 'Q': -HOUR(4), 'R': -HOUR(5), 'S': -HOUR(6),
    'U': -HOUR(8), 'V': -HOUR(9), 'W': -HOUR(10), 'X': -HOUR(11),
    'Y': -HOUR(12), 'Z': HOUR(0),
}

UNIT_TYPES = ('YEAR_UNIT', 'MONTH_UNIT', 'DAY_UNIT', 'HOUR_UNIT',
              'MIN_UNIT', 'SEC_UNIT')


def lookup_zone(word, local_table):
    if word in UNIVERSAL_ZONES:
        return ('ZONE', UNIVERSAL_ZONES[word])
    for name, isdst in local_table:
        if name == word:
            return ('LOCAL_ZONE', isdst)
    for name, typ, val in TIME_ZONE_TABLE:
        if name == word:
            return (typ, val)
    return None


def lookup_word(word, local_table):
    word = word.upper()
    if word in MERIDIAN_TABLE:
        return ('MERIDIAN', MERIDIAN_TABLE[word])
    wordlen = len(word)
    abbrev = wordlen == 3 or (wordlen == 4 and word[3] == '.')
    for name, typ, val in MONTH_AND_DAY_TABLE:
        if (name[:3] == word[:3]) if abbrev else (name == word):
            return (typ, val)
    tp = lookup_zone(word, local_table)
    if tp:
        return tp
    if word == 'DST':
        return ('DST', 0)
    if word in TIME_UNITS_TABLE:
        return TIME_UNITS_TABLE[word]
    if word.endswith('S'):
        w = word[:-1]
        if w in TIME_UNITS_TABLE:
            return TIME_UNITS_TABLE[w]
    if word in RELATIVE_TIME_TABLE:
        return RELATIVE_TIME_TABLE[word]
    if wordlen == 1:
        if word == 'T':
            return ('T', 0)
        if word in MILITARY_TABLE:
            return ('ZONE', MILITARY_TABLE[word])
    if '.' in word:
        w = word.replace('.', '')
        tp = lookup_zone(w, local_table)
        if tp:
            return tp
    return None


def lex(s, local_table):
    """Tokenize.  Tokens are tuples whose first element is the type.

    N / S : (type, value, digits, negative)
    UD / SD : (type, sec, ns)
    others : (type, value)
    """
    toks = []
    i = 0
    n = len(s)
    while True:
        while i < n and s[i] in SPACES:
            i += 1
        if i >= n:
            toks.append(('EOF', 0))
            return toks
        c = s[i]
        if isdig(c) or c == '-' or c == '+':
            if c == '-' or c == '+':
                sign = -1 if c == '-' else 1
                p = i + 1
                while p < n and s[p] in SPACES:
                    p += 1
                i = p
                if not (p < n and isdig(s[p])):
                    continue
            else:
                sign = 0
            p = i
            value = 0
            overflow = False
            while p < n and isdig(s[p]):
                d = ord(s[p]) - 48
                value = value * 10 + (-d if sign < 0 else d)
                if not fits_i64(value):
                    overflow = True
                p += 1
            if overflow:
                toks.append(('ERR', 0))
                toks.append(('EOF', 0))
                return toks
            if p < n and s[p] in '.,' and p + 1 < n and isdig(s[p + 1]):
                sec = value
                p += 1
                ns = ord(s[p]) - 48
                p += 1
                for _ in range(2, 10):
                    ns *= 10
                    if p < n and isdig(s[p]):
                        ns += ord(s[p]) - 48
                        p += 1
                if sign < 0:
                    while p < n and isdig(s[p]):
                        if s[p] != '0':
                            ns += 1
                            break
                        p += 1
                while p < n and isdig(s[p]):
                    p += 1
                if sign < 0 and ns:
                    if sec == I64_MIN:
                        toks.append(('ERR', 0))
                        toks.append(('EOF', 0))
                        return toks
                    sec -= 1
                    ns = BILLION - ns
                toks.append(('SD' if sign else 'UD', sec, ns))
                i = p
            else:
                toks.append(('S' if sign else 'N', value, p - i, sign < 0))
                i = p
            continue
        if isalph(c):
            buf = []
            while True:
                if len(buf) < 19:
                    buf.append(c)
                i += 1
                c = s[i] if i < n else ''
                if not (c and (isalph(c) or c == '.')):
                    break
            tp = lookup_word(''.join(buf), local_table)
            if tp is None:
                toks.append(('ERR', 0))
            else:
                toks.append(tp)
            continue
        if c != '(':
            toks.append(('CHAR', c))
            i += 1
            continue
        count = 0
        while True:
            if i >= n:
                toks.append(('EOF', 0))
                return toks
            c = s[i]
            i += 1
            if c == '(':
                count += 1
            elif c == ')':
                count -= 1
            if count == 0:
                break


# ---------------------------------------------------------------------------
# Parser (mimics the bison LALR(1) parser, shift preferred on conflicts)
# ---------------------------------------------------------------------------

class PC(object):
    pass


REL_FIELDS = ('year', 'month', 'day', 'hour', 'minutes', 'seconds', 'ns')


def rel0():
    return dict.fromkeys(REL_FIELDS, 0)


def apply_relative_time(pc, rel, factor):
    for k in REL_FIELDS:
        if factor < 0:
            v = pc.rel[k] - rel[k]
        else:
            v = pc.rel[k] + rel[k]
        if k == 'ns':
            if not fits_int(v):
                raise Fail()
        elif not fits_i64(v):
            raise Fail()
        pc.rel[k] = v
    pc.rels_seen = True


def set_hhmmss(pc, h, m, s, ns):
    pc.hour = h
    pc.minutes = m
    pc.sec = s
    pc.nsec = ns


def time_zone_hhmm(pc, stok, mm):
    value, digits, negative = stok[1], stok[2], stok[3]
    if digits <= 2 and mm < 0:
        value *= 100
    if mm < 0:
        n_minutes = cdiv(value, 100) * 60 + cmod(value, 100)
    else:
        n_minutes = value * 60 + (-mm if negative else mm)
        if not fits_i64(n_minutes):
            raise Fail()
    if not (-24 * 60 <= n_minutes <= 24 * 60):
        raise Fail()
    pc.time_zone = n_minutes * 60


def digits_to_date_time(pc, tok):
    value, digits = tok[1], tok[2]
    if (pc.dates_seen and not pc.year_digits and not pc.rels_seen
            and (pc.times_seen or 2 < digits)):
        pc.year = value
        pc.year_digits = digits
    else:
        if 4 < digits:
            pc.dates_seen += 1
            pc.day = value % 100
            pc.month = (value // 100) % 100
            pc.year = value // 10000
            pc.year_digits = digits - 4
        else:
            pc.times_seen += 1
            if digits <= 2:
                pc.hour = value
                pc.minutes = 0
            else:
                pc.hour = value // 100
                pc.minutes = value % 100
            pc.sec = 0
            pc.nsec = 0
            pc.meridian = MER24


def make_rel(unit_tok, mult):
    rel = rel0()
    typ = unit_tok[0]
    if typ == 'YEAR_UNIT':
        rel['year'] = mult
    elif typ == 'MONTH_UNIT':
        rel['month'] = mult
    elif typ == 'DAY_UNIT':
        v = mult * unit_tok[1]
        if not fits_i64(v):
            raise Fail()
        rel['day'] = v
    elif typ == 'HOUR_UNIT':
        rel['hour'] = mult
    elif typ == 'MIN_UNIT':
        rel['minutes'] = mult
    else:
        rel['seconds'] = mult
    return rel


def parse_tokens(toks, pc):
    def t(k):
        return toks[k][0] if k < len(toks) else 'EOF'

    def ischar(k, c):
        return t(k) == 'CHAR' and toks[k][1] == c

    def zone_offset(k):
        # toks[k] is S
        stok = toks[k]
        if ischar(k + 1, ':'):
            if t(k + 2) != 'N':
                raise Fail()
            mm = toks[k + 2][1]
            k += 3
        else:
            mm = -1
            k += 1
        pc.zones_seen += 1
        time_zone_hhmm(pc, stok, mm)
        return k

    def unsigned_seconds(k):
        if t(k) == 'N':
            return toks[k][1], 0
        if t(k) == 'UD':
            return toks[k][1], toks[k][2]
        raise Fail()

    def finish_rel(k, rel):
        if t(k) == 'AGO':
            apply_relative_time(pc, rel, toks[k][1])
            return k + 1
        apply_relative_time(pc, rel, 1)
        return k

    i = 0
    if ischar(0, '@'):
        tt = t(1)
        if tt in ('N', 'S'):
            sec, ns = toks[1][1], 0
        elif tt in ('UD', 'SD'):
            sec, ns = toks[1][1], toks[1][2]
        else:
            raise Fail()
        if t(2) != 'EOF':
            raise Fail()
        pc.timespec = (sec, ns)
        return

    while t(i) != 'EOF':
        tt = t(i)
        tok = toks[i]
        if tt == 'N':
            nt = t(i + 1)
            if nt == 'MERIDIAN':
                set_hhmmss(pc, tok[1], 0, 0, 0)
                pc.meridian = toks[i + 1][1]
                pc.times_seen += 1
                i += 2
            elif ischar(i + 1, ':'):
                if t(i + 2) != 'N':
                    raise Fail()
                mins = toks[i + 2][1]
                i += 3
                if t(i) == 'MERIDIAN':
                    set_hhmmss(pc, tok[1], mins, 0, 0)
                    pc.meridian = toks[i][1]
                    i += 1
                elif ischar(i, ':'):
                    sec, ns = unsigned_seconds(i + 1)
                    i += 2
                    if t(i) == 'MERIDIAN':
                        set_hhmmss(pc, tok[1], mins, sec, ns)
                        pc.meridian = toks[i][1]
                        i += 1
                    else:
                        if t(i) == 'S':
                            i = zone_offset(i)
                        set_hhmmss(pc, tok[1], mins, sec, ns)
                        pc.meridian = MER24
                else:
                    if t(i) == 'S':
                        i = zone_offset(i)
                    set_hhmmss(pc, tok[1], mins, 0, 0)
                    pc.meridian = MER24
                pc.times_seen += 1
            elif ischar(i + 1, '/'):
                if t(i + 2) != 'N':
                    raise Fail()
                n2 = toks[i + 2]
                if ischar(i + 3, '/'):
                    if t(i + 4) != 'N':
                        raise Fail()
                    n3 = toks[i + 4]
                    if 4 <= tok[2]:
                        pc.year, pc.year_digits = tok[1], tok[2]
                        pc.month = n2[1]
                        pc.day = n3[1]
                    else:
                        pc.month = tok[1]
                        pc.day = n2[1]
                        pc.year, pc.year_digits = n3[1], n3[2]
                    i += 5
                else:
                    pc.month = tok[1]
                    pc.day = n2[1]
                    i += 3
                pc.dates_seen += 1
            elif nt == 'MONTH':
                mon = toks[i + 1][1]
                nt2 = t(i + 2)
                pc.day = tok[1]
                pc.month = mon
                if nt2 == 'N':
                    pc.year, pc.year_digits = toks[i + 2][1], toks[i + 2][2]
                    i += 3
                elif nt2 == 'S':
                    pc.year = -toks[i + 2][1]
                    pc.year_digits = toks[i + 2][2]
                    i += 3
                else:
                    i += 2
                pc.dates_seen += 1
            elif nt == 'DAY':
                pc.day_ordinal = tok[1]
                pc.day_number = toks[i + 1][1]
                pc.days_seen += 1
                i += 2
            elif nt in UNIT_TYPES:
                rel = make_rel(toks[i + 1], tok[1])
                i = finish_rel(i + 2, rel)
            elif nt == 'S':
                s1 = toks[i + 1]
                nt2 = t(i + 2)
                if nt2 == 'S':
                    s2 = toks[i + 2]
                    pc.year, pc.year_digits = tok[1], tok[2]
                    pc.month = -s1[1]
                    pc.day = -s2[1]
                    i += 3
                    if t(i) == 'T':
                        i += 1
                        if t(i) != 'N':
                            raise Fail()
                        hr = toks[i][1]
                        if t(i + 1) == 'S':
                            i = zone_offset(i + 1)
                            set_hhmmss(pc, hr, 0, 0, 0)
                        elif ischar(i + 1, ':'):
                            if t(i + 2) != 'N':
                                raise Fail()
                            mins = toks[i + 2][1]
                            i += 3
                            sec, ns = 0, 0
                            if ischar(i, ':'):
                                sec, ns = unsigned_seconds(i + 1)
                                i += 2
                            if t(i) == 'S':
                                i = zone_offset(i)
                            set_hhmmss(pc, hr, mins, sec, ns)
                        else:
                            raise Fail()
                        pc.meridian = MER24
                        pc.times_seen += 1
                        pc.dates_seen += 1
                    else:
                        pc.dates_seen += 1
                elif nt2 in UNIT_TYPES:
                    digits_to_date_time(pc, tok)
                    rel = make_rel(toks[i + 2], s1[1])
                    apply_relative_time(pc, rel, 1)
                    i += 3
                else:
                    i = zone_offset(i + 1)
                    set_hhmmss(pc, tok[1], 0, 0, 0)
                    pc.meridian = MER24
                    pc.times_seen += 1
            else:
                digits_to_date_time(pc, tok)
                i += 1
        elif tt == 'MONTH':
            nt = t(i + 1)
            if nt == 'S':
                if t(i + 2) != 'S':
                    raise Fail()
                pc.month = tok[1]
                pc.day = -toks[i + 1][1]
                pc.year = -toks[i + 2][1]
                pc.year_digits = toks[i + 2][2]
                i += 3
            elif nt == 'N':
                pc.month = tok[1]
                pc.day = toks[i + 1][1]
                if ischar(i + 2, ','):
                    if t(i + 3) != 'N':
                        raise Fail()
                    pc.year = toks[i + 3][1]
                    pc.year_digits = toks[i + 3][2]
                    i += 4
                else:
                    i += 2
            else:
                raise Fail()
            pc.dates_seen += 1
        elif tt == 'DAY':
            pc.day_ordinal = 0
            pc.day_number = tok[1]
            i += 1
            if ischar(i, ','):
                i += 1
            pc.days_seen += 1
        elif tt == 'ORD':
            nt = t(i + 1)
            if nt == 'DAY':
                pc.day_ordinal = tok[1]
                pc.day_number = toks[i + 1][1]
                pc.days_seen += 1
                i += 2
            elif nt in UNIT_TYPES:
                rel = make_rel(toks[i + 1], tok[1])
                i = finish_rel(i + 2, rel)
            else:
                raise Fail()
        elif tt in ('UD', 'SD'):
            if t(i + 1) != 'SEC_UNIT':
                raise Fail()
            rel = rel0()
            rel['seconds'] = tok[1]
            rel['ns'] = tok[2]
            i = finish_rel(i + 2, rel)
        elif tt == 'S':
            if t(i + 1) not in UNIT_TYPES:
                raise Fail()
            rel = make_rel(toks[i + 1], tok[1])
            i = finish_rel(i + 2, rel)
        elif tt in UNIT_TYPES:
            rel = make_rel(tok, 1)
            i = finish_rel(i + 1, rel)
        elif tt == 'DAY_SHIFT':
            rel = rel0()
            rel['day'] = tok[1]
            apply_relative_time(pc, rel, 1)
            i += 1
        elif tt == 'ZONE':
            nt = t(i + 1)
            if nt == 'DST':
                pc.time_zone = tok[1] + 3600
                i += 2
            elif nt == 'S':
                if t(i + 2) in UNIT_TYPES:
                    pc.time_zone = tok[1]
                    rel = make_rel(toks[i + 2], toks[i + 1][1])
                    apply_relative_time(pc, rel, 1)
                    i += 3
                else:
                    stok = toks[i + 1]
                    if ischar(i + 2, ':'):
                        if t(i + 3) != 'N':
                            raise Fail()
                        mm = toks[i + 3][1]
                        i += 4
                    else:
                        mm = -1
                        i += 2
                    time_zone_hhmm(pc, stok, mm)
                    v = pc.time_zone + tok[1]
                    if not fits_i64(v):
                        raise Fail()
                    pc.time_zone = v
            else:
                pc.time_zone = tok[1]
                i += 1
            pc.zones_seen += 1
        elif tt == 'DAYZONE':
            pc.time_zone = tok[1] + 3600
            pc.zones_seen += 1
            i += 1
        elif tt == 'LOCAL_ZONE':
            if t(i + 1) == 'DST':
                pc.local_isdst = 1
                pc.dsts_seen += 1
                i += 2
            else:
                pc.local_isdst = tok[1]
                i += 1
            pc.local_zones_seen += 1
        elif tt == 'T':
            pc.time_zone = -HOUR(7)
            if t(i + 1) == 'S':
                if t(i + 2) not in UNIT_TYPES:
                    raise Fail()
                rel = make_rel(toks[i + 2], toks[i + 1][1])
                apply_relative_time(pc, rel, 1)
                i += 3
            else:
                i += 1
            pc.zones_seen += 1
        else:
            raise Fail()


def to_hour(hours, meridian):
    if meridian == MER24:
        return hours if 0 <= hours < 24 else -1
    if meridian == MER_AM:
        return hours if 0 < hours < 12 else (0 if hours == 12 else -1)
    return hours + 12 if 0 < hours < 12 else (12 if hours == 12 else -1)


def to_tm_year(year, digits):
    if 0 <= year and digits == 2:
        year += 2000 if year < 69 else 1900
    if year < 0:
        v = -1900 - year
    else:
        v = year - 1900
    if not fits_int(v):
        raise Fail()
    return v + 1900


def parse_datetime(s, now_ns):
    """Return (sec, ns) or None if the string is invalid."""
    try:
        return _parse_datetime(s, now_ns)
    except Fail:
        return None


def _parse_datetime(s, now_ns):
    nul = s.find('\0')
    if nul >= 0:
        s = s[:nul]
    tz = UTC
    p = 0
    while p < len(s) and s[p] in SPACES:
        p += 1
    if s.startswith('TZ="', p):
        q = p + 4
        buf = []
        while q < len(s):
            c = s[q]
            if c == '\\':
                q += 1
                if q < len(s) and s[q] in '\\"':
                    buf.append(s[q])
                    q += 1
                    continue
                break
            if c == '"':
                tz = make_zone(''.join(buf))
                s = s[q + 1:]
                break
            buf.append(c)
            q += 1

    now_sec, now_nsec = divmod(now_ns, BILLION)
    ntm = tz.localtime(now_sec)
    local_table = [(ntm.zone, ntm.isdst)] if ntm.zone else []

    pc = PC()
    pc.year = ntm.year
    pc.year_digits = 0
    pc.month = ntm.mon + 1
    pc.day = ntm.mday
    pc.hour = ntm.hour
    pc.minutes = ntm.min
    pc.sec = ntm.sec
    pc.nsec = now_nsec
    pc.meridian = MER24
    pc.rel = rel0()
    pc.timespec = None
    pc.rels_seen = False
    pc.dates_seen = 0
    pc.days_seen = 0
    pc.times_seen = 0
    pc.local_zones_seen = 0
    pc.dsts_seen = 0
    pc.zones_seen = 0
    pc.time_zone = 0
    pc.local_isdst = 0
    pc.day_ordinal = 0
    pc.day_number = 0

    toks = lex(s, local_table)
    parse_tokens(toks, pc)

    if pc.timespec is not None:
        return pc.timespec

    if 1 < (pc.times_seen | pc.dates_seen | pc.days_seen | pc.dsts_seen
            | (pc.local_zones_seen + pc.zones_seen)):
        raise Fail()

    year = to_tm_year(pc.year, pc.year_digits)
    mon = pc.month - 1
    mday = pc.day
    if not fits_int(mon) or not fits_int(mday):
        raise Fail()
    nsec = pc.nsec
    if pc.times_seen or (pc.rels_seen and not pc.dates_seen
                         and not pc.days_seen):
        hour = to_hour(pc.hour, pc.meridian)
        if hour < 0:
            raise Fail()
        minute = pc.minutes
        sec = pc.sec
        if not fits_int(minute) or not fits_int(sec):
            raise Fail()
    else:
        hour = minute = sec = 0
        nsec = 0

    # Validate the way mktime_ok does: no field may be normalized.
    if not (0 <= mon <= 11 and 1 <= mday <= days_in_month(year, mon + 1)
            and 0 <= minute <= 59 and 0 <= sec <= 59):
        raise Fail()
    r = tz.mktime(year, mon, mday, hour, minute, sec)
    if r is None:
        raise Fail()
    start, tm = r
    tm0 = (hour, minute, sec)

    if pc.days_seen and not pc.dates_seen:
        dayincr = (pc.day_ordinal
                   - (1 if (0 < pc.day_ordinal
                            and tm.wday != pc.day_number) else 0)) * 7
        if not fits_i64(dayincr):
            raise Fail()
        dayincr += (pc.day_number - tm.wday + 7) % 7
        if not fits_i64(dayincr):
            raise Fail()
        nm = dayincr + tm.mday
        if not fits_int(nm):
            raise Fail()
        r = tz.mktime(tm.year, tm.mon, nm, tm.hour, tm.min, tm.sec)
        if r is None or r[0] == -1:
            raise Fail()
        start, tm = r

    if pc.rel['year'] or pc.rel['month'] or pc.rel['day']:
        ty = tm.year - 1900 + pc.rel['year']
        tmo = tm.mon + pc.rel['month']
        td = tm.mday + pc.rel['day']
        if not (fits_int(ty) and fits_int(tmo) and fits_int(td)):
            raise Fail()
        r = tz.mktime(ty + 1900, tmo, td, tm0[0], tm0[1], tm0[2])
        if r is None or r[0] == -1:
            raise Fail()
        start, tm = r

    if pc.zones_seen:
        delta = pc.time_zone - tm.gmtoff
        start = start - delta
        if not fits_i64(start):
            raise Fail()

    sum_ns = nsec + pc.rel['ns']
    normalized_ns = sum_ns % BILLION
    d4 = (sum_ns - normalized_ns) // BILLION
    d1 = pc.rel['hour'] * 3600
    if not fits_i64(d1):
        raise Fail()
    t1 = start + d1
    if not fits_i64(t1):
        raise Fail()
    d2 = pc.rel['minutes'] * 60
    if not fits_i64(d2):
        raise Fail()
    t2 = t1 + d2
    if not fits_i64(t2):
        raise Fail()
    t3 = t2 + pc.rel['seconds']
    if not fits_i64(t3):
        raise Fail()
    t4 = t3 + d4
    if not fits_i64(t4):
        raise Fail()
    return (t4, normalized_ns)


# ---------------------------------------------------------------------------
# posixtime (MMDDhhmm[[CC]YY][.ss]) for the clock-setting operand
# ---------------------------------------------------------------------------

def posixtime(s, now_sec):
    dot = s.find('.')
    body = s
    if dot >= 0:
        body = s[:dot]
        if len(s) - dot != 3:
            return None
    L = len(body)
    if not (8 <= L <= 12 and L % 2 == 0):
        return None
    if not all(isdig(c) for c in body):
        return None
    pairs = [int(body[k:k + 2]) for k in range(0, L, 2)]
    mon = pairs[0] - 1
    mday = pairs[1]
    hour = pairs[2]
    minute = pairs[3]
    rest = pairs[4:]
    if not rest:
        year = UTC.localtime(now_sec).year
    elif len(rest) == 1:
        y = rest[0]
        if y < 69:
            y += 100
        year = 1900 + y
    else:
        year = rest[0] * 100 + rest[1]
    if dot >= 0:
        if isdig(s[dot + 1]) and isdig(s[dot + 2]):
            sec = int(s[dot + 1:dot + 3])
        else:
            return None
    else:
        sec = 0
    leap = sec == 60
    if leap:
        sec = 59
    if not (0 <= mon <= 11 and 1 <= mday <= days_in_month(year, mon + 1)
            and 0 <= hour <= 23 and 0 <= minute <= 59 and 0 <= sec <= 59):
        return None
    t = timegm_fields(year, mon, mday, hour, minute, sec)
    return t + (1 if leap else 0)


# ---------------------------------------------------------------------------
# strftime (gnulib nstrftime, C locale)
# ---------------------------------------------------------------------------

WDAY_ABBR = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
WDAY_FULL = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday',
             'Friday', 'Saturday']
MON_ABBR = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep',
            'Oct', 'Nov', 'Dec']
MON_FULL = ['January', 'February', 'March', 'April', 'May', 'June', 'July',
            'August', 'September', 'October', 'November', 'December']

_UP = {i: i - 32 for i in range(97, 123)}
_LO = {i: i + 32 for i in range(65, 91)}


def upper_ascii(s):
    return s.translate(_UP)


def lower_ascii(s):
    return s.translate(_LO)


def pad_text(s, width, pad, lower=False, upper=False):
    w = 0 if (pad == '-' or width < 0) else width
    prefix = ''
    if len(s) < w:
        prefix = ('0' if pad in ('0', '+') else ' ') * (w - len(s))
    if lower:
        s = lower_ascii(s)
    elif upper:
        s = upper_ascii(s)
    return prefix + s


def number_body(mag, negative, always_sign, digits, pad, width, mask,
                lower, upper):
    buf = []
    u = mag
    while True:
        if mask & 1:
            buf.append(':')
        mask >>= 1
        buf.append(chr(48 + u % 10))
        u //= 10
        if u == 0 and mask == 0:
            break
    s = ''.join(reversed(buf))
    return sign_and_padding(s, negative, always_sign, digits, pad, width,
                            lower, upper)


def sign_and_padding(s, negative, always_sign, digits, pad, width,
                     lower, upper):
    if not pad:
        pad = '0'
    if width < 0:
        width = digits
    sign = '-' if negative else ('+' if always_sign else '')
    res = ''
    if sign:
        shortage = width - 1 - len(s)
        padding = 0 if (pad == '-' or shortage <= 0) else shortage
        if pad == '_':
            res += ' ' * padding
            width -= padding
        res += sign
        width -= 1
    return res + pad_text(s, width, pad, lower, upper)


def iso_week_days(yday, wday):
    big_enough_multiple_of_7 = (366 // 7 + 2) * 7
    return (yday - (yday - wday + 4 + big_enough_multiple_of_7) % 7
            + 4 - 1)


class TMOut(object):
    """Broken-down time for output."""

    def __init__(self, t, ns, zone=UTC):
        tm = zone.localtime(t)
        self.tm = tm
        self.t = t
        self.ns = ns


def strftime_internal(fmt, T, upcase=False, yr_spec=0, width=-1):
    tm = T.tm
    out = []
    n = len(fmt)
    f = 0
    tm_year = tm.year - 1900
    hour12 = tm.hour
    if hour12 > 12:
        hour12 -= 12
    elif hour12 == 0:
        hour12 = 12
    while f < n:
        c = fmt[f]
        if c != '%':
            out.append(pad_text(c, width, 0))
            width = -1
            f += 1
            continue
        pct = f
        pad = 0
        to_lowcase = False
        to_uppcase = upcase
        change_case = False
        f += 1
        while f < n and fmt[f] in '_-+0^#':
            ch = fmt[f]
            if ch == '^':
                to_uppcase = True
            elif ch == '#':
                change_case = True
            else:
                pad = ch
            f += 1
        if f < n and isdig(fmt[f]):
            width = 0
            while f < n and isdig(fmt[f]):
                width = width * 10 + ord(fmt[f]) - 48
                if width > INT_MAX:
                    width = INT_MAX
                f += 1
        modifier = 0
        if f < n and fmt[f] in 'EO':
            modifier = fmt[f]
            f += 1
        fc = fmt[f] if f < n else '\0'

        res = None
        bad = False

        def number(v, digits, spacepad=False):
            p = pad
            if spacepad and not p:
                p = '_'
            return number_body(abs(v), v < 0, False, digits, p, width, 0,
                               to_lowcase, to_uppcase)

        def signed_number(neg, v, digits):
            mag = (-v) % (2 ** 32) if neg else v % (2 ** 32)
            return number_body(mag, neg, False, digits, pad or 0, width, 0,
                               to_lowcase, to_uppcase)

        def yearish(digits, neg, v):
            p = pad
            if not p:
                p = yr_spec
            u = v % (2 ** 32)
            always = (p == '+' and ((99 if digits == 2 else 9999) < u
                                    or digits < width))
            mag = (-v) % (2 ** 32) if neg else u
            return number_body(mag, neg, always, digits, p, width, 0,
                               to_lowcase, to_uppcase)

        def underlying(sub):
            text = strftime_internal(sub, T)
            return pad_text(text, width, pad, to_lowcase, to_uppcase)

        def subformat(sub, subwidth=-1):
            text = strftime_internal(sub, T, to_uppcase, pad, subwidth)
            return pad_text(text, width, pad)

        if fc == '%':
            if modifier:
                bad = True
            else:
                res = pad_text('%', width, pad)
        elif fc == 'n':
            res = pad_text('\n', width, pad)
        elif fc == 't':
            res = pad_text('\t', width, pad)
        elif fc in 'aA':
            if modifier:
                bad = True
            else:
                if change_case:
                    to_uppcase = True
                    to_lowcase = False
                txt = (WDAY_ABBR if fc == 'a' else WDAY_FULL)[tm.wday]
                res = pad_text(txt, width, pad, to_lowcase, to_uppcase)
        elif fc in 'bh':
            if change_case:
                to_uppcase = True
                to_lowcase = False
            if modifier == 'E':
                bad = True
            else:
                res = pad_text(MON_ABBR[tm.mon], width, pad, to_lowcase,
                               to_uppcase)
        elif fc == 'B':
            if modifier == 'E':
                bad = True
            else:
                if change_case:
                    to_uppcase = True
                    to_lowcase = False
                res = pad_text(MON_FULL[tm.mon], width, pad, to_lowcase,
                               to_uppcase)
        elif fc == 'c':
            if modifier == 'O':
                bad = True
            else:
                res = underlying('%a %b %e %H:%M:%S %Y')
        elif fc == 'C':
            if modifier == 'E':
                res = underlying('%C')
            else:
                negative_year = tm_year < -1900
                zero_thru_1899 = (not negative_year) and tm_year < 0
                century = cdiv(tm_year - 99 * (1 if zero_thru_1899 else 0),
                               100) + 19
                res = yearish(2, negative_year, century)
        elif fc == 'd':
            if modifier == 'E':
                bad = True
            else:
                res = number(tm.mday, 2)
        elif fc == 'D':
            if modifier:
                bad = True
            else:
                res = subformat('%m/%d/%y')
        elif fc == 'e':
            if modifier == 'E':
                bad = True
            else:
                res = number(tm.mday, 2, True)
        elif fc == 'F':
            if modifier:
                bad = True
            else:
                if not pad and width < 0:
                    pad = '+'
                    subwidth = 4
                else:
                    subwidth = width - 6
                    if subwidth < 0:
                        subwidth = 0
                res = subformat('%Y-%m-%d', subwidth)
        elif fc in 'VgG':
            if modifier == 'E':
                bad = True
            else:
                Y = tm.year
                year_adjust = 0
                days = iso_week_days(tm.yday, tm.wday)
                if days < 0:
                    year_adjust = -1
                    days = iso_week_days(
                        tm.yday + (365 + (1 if isleap(Y - 1) else 0)),
                        tm.wday)
                else:
                    d = iso_week_days(
                        tm.yday - (365 + (1 if isleap(Y) else 0)), tm.wday)
                    if 0 <= d:
                        year_adjust = 1
                        days = d
                if fc == 'g':
                    yy = cmod(cmod(tm_year, 100) + year_adjust, 100)
                    if yy >= 0:
                        val = yy
                    elif tm_year < -1900 - year_adjust:
                        val = -yy
                    else:
                        val = yy + 100
                    res = yearish(2, False, val)
                elif fc == 'G':
                    res = yearish(4, tm_year < -1900 - year_adjust,
                                  tm_year + 1900 + year_adjust)
                else:
                    res = number(days // 7 + 1, 2)
        elif fc == 'H':
            if modifier == 'E':
                bad = True
            else:
                res = number(tm.hour, 2)
        elif fc == 'I':
            if modifier == 'E':
                bad = True
            else:
                res = number(hour12, 2)
        elif fc == 'k':
            if modifier == 'E':
                bad = True
            else:
                res = number(tm.hour, 2, True)
        elif fc == 'l':
            if modifier == 'E':
                bad = True
            else:
                res = number(hour12, 2, True)
        elif fc == 'j':
            if modifier == 'E':
                bad = True
            else:
                res = signed_number(tm.yday < -1, tm.yday + 1, 3)
        elif fc == 'm':
            if modifier == 'E':
                bad = True
            else:
                res = signed_number(tm.mon < -1, tm.mon + 1, 2)
        elif fc == 'M':
            if modifier == 'E':
                bad = True
            else:
                res = number(tm.min, 2)
        elif fc == 'N':
            if modifier == 'E':
                bad = True
            else:
                nv = T.ns
                w = width
                if w <= 0:
                    w = 9
                ndigs = 9
                while w < ndigs or (1 < ndigs and nv % 10 == 0):
                    ndigs -= 1
                    nv //= 10
                digs = str(nv).rjust(ndigs, '0')[-ndigs:] if ndigs else ''
                p = pad or '0'
                res = pad_text(digs, 0, p, to_lowcase, to_uppcase)
                extra = w - ndigs
                if p != '-' and extra > 0:
                    res += ('0' if p in ('0', '+') else ' ') * extra
        elif fc in 'pP':
            if fc == 'P':
                to_lowcase = True
            if change_case:
                to_uppcase = False
                to_lowcase = True
            res = pad_text('AM' if tm.hour < 12 else 'PM', width, pad,
                           to_lowcase, to_uppcase)
        elif fc == 'q':
            if modifier == 'E':
                bad = True
            else:
                res = number(tm.mon // 3 + 1, 1)
        elif fc == 'r':
            res = underlying('%I:%M:%S %p')
        elif fc == 'R':
            res = subformat('%H:%M')
        elif fc == 's':
            tv = T.t
            s = str(abs(tv))
            res = sign_and_padding(s, tv < 0, False, 1, pad, width,
                                   to_lowcase, to_uppcase)
        elif fc == 'S':
            if modifier == 'E':
                bad = True
            else:
                res = number(tm.sec, 2)
        elif fc == 'T':
            res = subformat('%H:%M:%S')
        elif fc == 'u':
            if modifier == 'E':
                bad = True
            else:
                res = number((tm.wday - 1 + 7) % 7 + 1, 1)
        elif fc == 'U':
            if modifier == 'E':
                bad = True
            else:
                res = number((tm.yday - tm.wday + 7) // 7, 2)
        elif fc == 'W':
            if modifier == 'E':
                bad = True
            else:
                res = number((tm.yday - (tm.wday - 1 + 7) % 7 + 7) // 7, 2)
        elif fc == 'w':
            if modifier == 'E':
                bad = True
            else:
                res = number(tm.wday, 1)
        elif fc == 'x':
            if modifier == 'O':
                bad = True
            else:
                res = underlying('%m/%d/%y')
        elif fc == 'X':
            if modifier == 'O':
                bad = True
            else:
                res = underlying('%H:%M:%S')
        elif fc == 'y':
            if modifier == 'E':
                res = underlying('%y')
            else:
                yy = cmod(tm_year, 100)
                if yy < 0:
                    yy = -yy if tm_year < -1900 else yy + 100
                res = yearish(2, False, yy)
        elif fc == 'Y':
            if modifier == 'E':
                res = underlying('%Y')
            elif modifier == 'O':
                bad = True
            else:
                res = yearish(4, tm_year < -1900, tm_year + 1900)
        elif fc == 'Z':
            if change_case:
                to_uppcase = False
                to_lowcase = True
            res = pad_text(tm.zone, width, pad, to_lowcase, to_uppcase)
        elif fc in 'z:':
            colons = 0
            if fc == ':':
                colons = 1
                while f + colons < n and fmt[f + colons] == ':':
                    colons += 1
                if not (f + colons < n and fmt[f + colons] == 'z'):
                    bad = True
                else:
                    f += colons
            if not bad:
                if tm.isdst < 0:
                    res = ''
                else:
                    diff = tm.gmtoff
                    negative = diff < 0 or (diff == 0 and tm.zone[:1] == '-')
                    hour_diff = cdiv(cdiv(diff, 60), 60)
                    min_diff = cmod(cdiv(diff, 60), 60)
                    sec_diff = cmod(diff, 60)
                    if colons == 3:
                        if sec_diff != 0:
                            colons = 2
                        elif min_diff != 0:
                            colons = 1
                        else:
                            colons = 'h'
                    if colons == 0:
                        d, mask, v = 5, 0, hour_diff * 100 + min_diff
                    elif colons == 1:
                        d, mask, v = 6, 0o4, hour_diff * 100 + min_diff
                    elif colons == 2:
                        d, mask, v = 9, 0o24, (hour_diff * 10000
                                               + min_diff * 100 + sec_diff)
                    elif colons == 'h':
                        d, mask, v = 3, 0, hour_diff
                    else:
                        bad = True
                    if not bad:
                        res = number_body(abs(v), negative, True, d, pad,
                                          width, mask, to_lowcase,
                                          to_uppcase)
        else:
            bad = True

        if bad:
            if fc == '\0':
                text = fmt[pct:n]
                f = n - 1
            else:
                text = fmt[pct:f + 1]
            res = pad_text(text, width, pad, to_lowcase, to_uppcase)
        out.append(res)
        width = -1
        f += 1
    return ''.join(out)


# ---------------------------------------------------------------------------
# Command line
# ---------------------------------------------------------------------------

PROG = 'date'

LONG_OPTIONS = [
    ('date', 1, 'd'),
    ('debug', 0, 'debug'),
    ('file', 1, 'f'),
    ('iso-8601', 2, 'I'),
    ('reference', 1, 'r'),
    ('resolution', 0, 'resolution'),
    ('rfc-email', 0, 'R'),
    ('rfc-822', 0, 'R'),
    ('rfc-2822', 0, 'R'),
    ('rfc-3339', 1, 'rfc-3339'),
    ('set', 1, 's'),
    ('uct', 0, 'u'),
    ('utc', 0, 'u'),
    ('universal', 0, 'u'),
    ('help', 0, 'help'),
    ('version', 0, 'version'),
]

SHORT_OPTIONS = {'d': 1, 'f': 1, 'I': 2, 'r': 1, 'R': 0, 's': 1, 'u': 0}

TIME_SPEC_STRING = ['hours', 'minutes', 'date', 'seconds', 'ns']
TIME_SPEC = [3, 4, 0, 1, 2]
ISO_8601_FORMAT = [
    '%Y-%m-%d',
    '%Y-%m-%dT%H:%M:%S%:z',
    '%Y-%m-%dT%H:%M:%S,%N%:z',
    '%Y-%m-%dT%H%:z',
    '%Y-%m-%dT%H:%M%:z',
]
RFC_3339_FORMAT = [
    '%Y-%m-%d',
    '%Y-%m-%d %H:%M:%S%:z',
    '%Y-%m-%d %H:%M:%S.%N%:z',
]
RFC_EMAIL_FORMAT = '%a, %d %b %Y %H:%M:%S %z'

VERSION_TEXT = """date (GNU coreutils) 9.1
Copyright (C) 2022 Free Software Foundation, Inc.
License GPLv3+: GNU GPL version 3 or later <https://gnu.org/licenses/gpl.html>.
This is free software: you are free to change and redistribute it.
There is NO WARRANTY, to the extent permitted by law.

Written by David MacKenzie.
"""

HELP_TEXT = """Usage: date [OPTION]... [+FORMAT]
  or:  date [-u|--utc|--universal] [MMDDhhmm[[CC]YY][.ss]]
Display date and time in the given FORMAT.
With -s, or with [MMDDhhmm[[CC]YY][.ss]], set the date and time.

Mandatory arguments to long options are mandatory for short options too.
  -d, --date=STRING          display time described by STRING, not 'now'
      --debug                annotate the parsed date,
                              and warn about questionable usage to stderr
  -f, --file=DATEFILE        like --date; once for each line of DATEFILE
  -I[FMT], --iso-8601[=FMT]  output date/time in ISO 8601 format.
                               FMT='date' for date only (the default),
                               'hours', 'minutes', 'seconds', or 'ns'
                               for date and time to the indicated precision.
                               Example: 2006-08-14T02:34:56-06:00
      --resolution           output the available resolution of timestamps
                               Example: 0.000000001
  -R, --rfc-email            output date and time in RFC 5322 format.
                               Example: Mon, 14 Aug 2006 02:34:56 -0600
      --rfc-3339=FMT         output date/time in RFC 3339 format.
                               FMT='date', 'seconds', or 'ns'
                               for date and time to the indicated precision.
                               Example: 2006-08-14 02:34:56-06:00
  -r, --reference=FILE       display the last modification time of FILE
  -s, --set=STRING           set time described by STRING
  -u, --utc, --universal     print or set Coordinated Universal Time (UTC)
      --help        display this help and exit
      --version     output version information and exit

FORMAT controls the output.  Interpreted sequences are:

  %%   a literal %
  %a   locale's abbreviated weekday name (e.g., Sun)
  %A   locale's full weekday name (e.g., Sunday)
  %b   locale's abbreviated month name (e.g., Jan)
  %B   locale's full month name (e.g., January)
  %c   locale's date and time (e.g., Thu Mar  3 23:05:25 2005)
  %C   century; like %Y, except omit last two digits (e.g., 20)
  %d   day of month (e.g., 01)
  %D   date; same as %m/%d/%y
  %e   day of month, space padded; same as %_d
  %F   full date; like %+4Y-%m-%d
  %g   last two digits of year of ISO week number (see %G)
  %G   year of ISO week number (see %V); normally useful only with %V
  %h   same as %b
  %H   hour (00..23)
  %I   hour (01..12)
  %j   day of year (001..366)
  %k   hour, space padded ( 0..23); same as %_H
  %l   hour, space padded ( 1..12); same as %_I
  %m   month (01..12)
  %M   minute (00..59)
  %n   a newline
  %N   nanoseconds (000000000..999999999)
  %p   locale's equivalent of either AM or PM; blank if not known
  %P   like %p, but lower case
  %q   quarter of year (1..4)
  %r   locale's 12-hour clock time (e.g., 11:11:04 PM)
  %R   24-hour hour and minute; same as %H:%M
  %s   seconds since the Epoch (1970-01-01 00:00 UTC)
  %S   second (00..60)
  %t   a tab
  %T   time; same as %H:%M:%S
  %u   day of week (1..7); 1 is Monday
  %U   week number of year, with Sunday as first day of week (00..53)
  %V   ISO week number, with Monday as first day of week (01..53)
  %w   day of week (0..6); 0 is Sunday
  %W   week number of year, with Monday as first day of week (00..53)
  %x   locale's date representation (e.g., 12/31/99)
  %X   locale's time representation (e.g., 23:13:48)
  %y   last two digits of year (00..99)
  %Y   year
  %z   +hhmm numeric time zone (e.g., -0400)
  %:z  +hh:mm numeric time zone (e.g., -04:00)
  %::z  +hh:mm:ss numeric time zone (e.g., -04:00:00)
  %:::z  numeric time zone with : to necessary precision (e.g., -04, +05:30)
  %Z   alphabetic time zone abbreviation (e.g., EDT)

By default, date pads numeric fields with zeroes.
The following optional flags may follow '%':

  -  (hyphen) do not pad the field
  _  (underscore) pad with spaces
  0  (zero) pad with zeros
  +  pad with zeros, and put '+' before future years with >4 digits
  ^  use upper case if possible
  #  use opposite case if possible

After any flags comes an optional field width, as a decimal number;
then an optional modifier, which is either
E to use the locale's alternate representations if available, or
O to use the locale's alternate numeric symbols if available.

Examples:
Convert seconds since the Epoch (1970-01-01 UTC) to a date
  $ date --date='@2147483647'

Show the time on the west coast of the US (use tzselect(1) to find TZ)
  $ TZ='America/Los_Angeles' date

Show the local time for 9AM next Friday on the west coast of the US
  $ date --date='TZ="America/Los_Angeles" 09:00 next Fri'

GNU coreutils online help: <https://www.gnu.org/software/coreutils/>
Full documentation <https://www.gnu.org/software/coreutils/date>
or available locally via: info '(coreutils) date invocation'
"""


class Exit(Exception):
    def __init__(self, code):
        Exception.__init__(self, code)
        self.code = code


def err(msg):
    sys.stderr.write('%s: %s\n' % (PROG, msg))


def usage_fail():
    sys.stderr.write("Try '%s --help' for more information.\n" % PROG)
    raise Exit(1)


def die(msg):
    err(msg)
    raise Exit(1)


def argmatch(arg, arglist):
    matchind = -1
    ambiguous = False
    for i, a in enumerate(arglist):
        if a.startswith(arg):
            if len(a) == len(arg):
                return i
            if matchind == -1:
                matchind = i
            else:
                ambiguous = True
    if ambiguous:
        return -2
    return matchind


def xargmatch(ctx, arg, arglist, vallist):
    r = argmatch(arg, arglist)
    if r < 0:
        if r == -2:
            err("ambiguous argument '%s' for '%s'" % (arg, ctx))
        else:
            err("invalid argument '%s' for '%s'" % (arg, ctx))
        sys.stderr.write('Valid arguments are:\n')
        for a in arglist:
            sys.stderr.write("  - '%s'\n" % a)
        usage_fail()
    return vallist[r]


def getopt(argv):
    """GNU getopt_long with argument permutation.

    Yields (opt, optarg) in order; returns operands via the list.
    """
    opts = []
    operands = []
    i = 0
    n = len(argv)
    while i < n:
        a = argv[i]
        if a == '--':
            operands.extend(argv[i + 1:])
            break
        if a.startswith('--'):
            body = a[2:]
            if '=' in body:
                name, val = body.split('=', 1)
                has_val = True
            else:
                name, val, has_val = body, None, False
            exact = [o for o in LONG_OPTIONS if o[0] == name]
            if exact:
                opt = exact[0]
            else:
                cands = [o for o in LONG_OPTIONS if o[0].startswith(name)]
                if not cands:
                    opts.append(('?', "unrecognized option '%s'" % a))
                    return opts, operands
                first = cands[0]
                if any((c[1], c[2]) != (first[1], first[2])
                       for c in cands[1:]):
                    opts.append(('?', "option '%s' is ambiguous" % a))
                    return opts, operands
                opt = first
            kind = opt[1]
            if kind == 0:
                if has_val:
                    opts.append(('?', "option '--%s' doesn't allow an "
                                      "argument" % opt[0]))
                    return opts, operands
                opts.append((opt[2], None))
            elif kind == 1:
                if not has_val:
                    if i + 1 < n:
                        i += 1
                        val = argv[i]
                    else:
                        opts.append(('?', "option '--%s' requires an "
                                          "argument" % opt[0]))
                        return opts, operands
                opts.append((opt[2], val))
            else:
                opts.append((opt[2], val if has_val else None))
            i += 1
            continue
        if a.startswith('-') and len(a) > 1:
            j = 1
            while j < len(a):
                ch = a[j]
                if ch not in SHORT_OPTIONS:
                    opts.append(('?', "invalid option -- '%s'" % ch))
                    return opts, operands
                kind = SHORT_OPTIONS[ch]
                if kind == 0:
                    opts.append((ch, None))
                    j += 1
                    continue
                rest = a[j + 1:]
                if kind == 1:
                    if rest:
                        opts.append((ch, rest))
                    elif i + 1 < n:
                        i += 1
                        opts.append((ch, argv[i]))
                    else:
                        opts.append(('?', "option requires an argument "
                                          "-- '%s'" % ch))
                        return opts, operands
                else:
                    opts.append((ch, rest if rest else None))
                break
            i += 1
            continue
        operands.append(a)
        i += 1
    return opts, operands


def adjust_resolution(fmt):
    chars = list(fmt)
    f = 0
    n = len(fmt)
    changed = False
    while f < n:
        if fmt[f] == '%':
            if f + 2 < n + 0 and fmt[f + 1:f + 3] == '-N':
                chars[f + 1] = '9'
                changed = True
                f += 2
            elif f + 1 < n and fmt[f + 1] == '%':
                f += 1
        f += 1
    return ''.join(chars) if changed else fmt


def show_date(fmt, when, outbuf):
    sec, ns = when
    tm = UTC.localtime(sec)
    if not fits_int(tm.year - 1900):
        err('time %s is out of range' % sec)
        return False
    T = TMOut.__new__(TMOut)
    T.tm = tm
    T.t = sec
    T.ns = ns
    outbuf.append(strftime_internal(fmt, T) + '\n')
    return True


def flush(outbuf):
    data = ''.join(outbuf).encode('latin-1', 'replace')
    del outbuf[:]
    try:
        sys.stdout.buffer.write(data)
        sys.stdout.buffer.flush()
    except Exception:
        pass


def decode_arg(a):
    try:
        b = os.fsencode(a)
    except Exception:
        b = a.encode('utf-8', 'surrogateescape')
    return b.decode('latin-1')


def run(argv, outbuf):
    argv = [decode_arg(a) for a in argv]
    datestr = None
    set_datestr = None
    set_date = False
    fmt = None
    get_resolution = False
    batch_file = None
    reference = None

    opts, operands = getopt(argv)
    for opt, optarg in opts:
        new_format = None
        if opt == '?':
            err(optarg)
            usage_fail()
        elif opt == 'd':
            datestr = optarg
        elif opt == 'debug':
            pass
        elif opt == 'f':
            batch_file = optarg
        elif opt == 'resolution':
            get_resolution = True
        elif opt == 'rfc-3339':
            i = xargmatch('--rfc-3339', optarg, TIME_SPEC_STRING[2:],
                          TIME_SPEC[2:])
            new_format = RFC_3339_FORMAT[i]
        elif opt == 'I':
            if optarg is not None:
                i = xargmatch('--iso-8601', optarg, TIME_SPEC_STRING,
                              TIME_SPEC)
            else:
                i = 0
            new_format = ISO_8601_FORMAT[i]
        elif opt == 'r':
            reference = optarg
        elif opt == 'R':
            new_format = RFC_EMAIL_FORMAT
        elif opt == 's':
            set_datestr = optarg
            set_date = True
        elif opt == 'u':
            pass
        elif opt == 'help':
            outbuf.append(HELP_TEXT)
            raise Exit(0)
        elif opt == 'version':
            outbuf.append(VERSION_TEXT)
            raise Exit(0)
        if new_format is not None:
            if fmt is not None:
                die('multiple output formats specified')
            fmt = new_format

    option_specified_date = ((datestr is not None) + (batch_file is not None)
                             + (reference is not None) + get_resolution)
    if option_specified_date > 1:
        err('the options to specify dates for printing are mutually '
            'exclusive')
        usage_fail()
    if set_date and option_specified_date:
        err('the options to print and set the time may not be used together')
        usage_fail()

    optind = 0
    if operands:
        if len(operands) > 1:
            err("extra operand '%s'" % operands[1])
            usage_fail()
        if operands[0].startswith('+'):
            if fmt is not None:
                die('multiple output formats specified')
            fmt = operands[0][1:]
            optind = 1
        elif set_date or option_specified_date:
            err("the argument '%s' lacks a leading '+';\n"
                "when using an option to specify date(s), any non-option\n"
                "argument must be a format string beginning with '+'"
                % operands[0])
            usage_fail()

    if fmt is None:
        if get_resolution:
            fmt = '%s.%N'
        else:
            fmt = '%a %b %e %H:%M:%S %Z %Y'

    fmt = adjust_resolution(fmt)
    now_ns = time.time_ns()

    if batch_file is not None:
        ok = True
        try:
            if batch_file == '-':
                data = sys.stdin.buffer.read()
            else:
                with open(batch_file, 'rb') as fh:
                    data = fh.read()
        except OSError as e:
            die('%s: %s' % (batch_file, e.strerror))
        text = data.decode('latin-1')
        lines = text.split('\n')
        if lines and lines[-1] == '':
            lines.pop()
            lines = [ln + '\n' for ln in lines]
        else:
            lines = [ln + '\n' for ln in lines[:-1]] + lines[-1:]
        for line in lines:
            when = parse_datetime(line, now_ns)
            if when is None:
                shown = line[:-1] if line.endswith('\n') else line
                err("invalid date '%s'" % shown)
                ok = False
            else:
                ok = show_date(fmt, when, outbuf) and ok
        return 0 if ok else 1

    ok = True
    valid = True
    when = None
    if not option_specified_date and not set_date:
        if optind < len(operands):
            set_date = True
            datestr = operands[optind]
            t = posixtime(datestr, now_ns // BILLION)
            if t is None:
                valid = False
            else:
                when = (t, 0)
        else:
            when = divmod(now_ns, BILLION)
    else:
        if reference is not None:
            try:
                st = os.stat(reference)
            except OSError as e:
                die('%s: %s' % (reference, e.strerror))
            when = divmod(st.st_mtime_ns, BILLION)
        elif get_resolution:
            when = (0, 1)
        else:
            if set_datestr is not None:
                datestr = set_datestr
            when = parse_datetime(datestr, now_ns)
            if when is None:
                valid = False
    if not valid:
        die("invalid date '%s'" % datestr)
    if set_date:
        err('cannot set date: Operation not permitted')
        ok = False
    ok = show_date(fmt, when, outbuf) and ok
    return 0 if ok else 1


def main(argv):
    outbuf = []
    try:
        code = run(argv, outbuf)
    except Exit as e:
        code = e.code
    flush(outbuf)
    return code


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
