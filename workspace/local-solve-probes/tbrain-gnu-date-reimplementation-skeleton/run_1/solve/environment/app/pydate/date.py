"""pydate: a GNU date 9.1 replacement in pure Python (display only).

Usage: python3 /app/pydate/date.py [OPTION]... [+FORMAT]

This mirrors coreutils 9.1 date.c, gnulib parse-datetime.y and gnulib
nstrftime.c (plus the parts of glibc strftime that nstrftime delegates to
in the C locale).
"""

import os
import sys
import time

INT_MIN = -(1 << 31)
INT_MAX = (1 << 31) - 1
I64_MIN = -(1 << 63)
I64_MAX = (1 << 63) - 1
BILLION = 1000000000


def fits_int(v):
    return INT_MIN <= v <= INT_MAX


def fits_i64(v):
    return I64_MIN <= v <= I64_MAX


def cdiv(a, b):
    q = abs(a) // abs(b)
    return q if (a >= 0) == (b >= 0) else -q


def cmod(a, b):
    return a - b * cdiv(a, b)


# ---------------------------------------------------------------------------
# Calendar arithmetic (proleptic Gregorian, unbounded ints)

def days_from_civil(y, m, d):
    y -= m <= 2
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
    return y + (m <= 2), m, d


def is_leap(y):
    return y % 4 == 0 and (y % 100 != 0 or y % 400 == 0)


class TM(object):
    __slots__ = ('year', 'mon', 'mday', 'hour', 'min', 'sec', 'wday',
                 'yday', 'gmtoff', 'zone', 'isdst')

    @property
    def tm_year(self):
        return self.year - 1900


def gm_fields(t):
    """Broken-down UTC fields for an integer timestamp."""
    days, secs = divmod(t, 86400)
    y, m, d = civil_from_days(days)
    tm = TM()
    tm.year = y
    tm.mon = m - 1
    tm.mday = d
    tm.hour = secs // 3600
    tm.min = secs // 60 % 60
    tm.sec = secs % 60
    tm.wday = (days + 4) % 7
    tm.yday = days - days_from_civil(y, 1, 1)
    tm.gmtoff = 0
    tm.zone = b'UTC'
    tm.isdst = 0
    return tm


def timegm_norm(tm_year, mon, mday, hour, minute, sec):
    y = tm_year + 1900
    y += mon // 12
    mon %= 12
    days = days_from_civil(y, mon + 1, 1) + mday - 1
    return days * 86400 + hour * 3600 + minute * 60 + sec


# ---------------------------------------------------------------------------
# Time zones

class FixedTZ(object):
    def __init__(self, gmtoff, abbr=b'UTC', isdst=0):
        self.off = gmtoff
        self.abbr = abbr
        self.isdst = isdst

    def offset_at(self, t):
        return self.off, self.abbr, self.isdst

    def localtime(self, t):
        off, abbr, isdst = self.offset_at(t)
        tm = gm_fields(t + off)
        tm.gmtoff = off
        tm.zone = abbr
        tm.isdst = isdst
        if not fits_int(tm.year - 1900):
            return None
        return tm

    def mktime(self, tm_year, mon, mday, hour, minute, sec):
        for v in (tm_year, mon, mday, hour, minute, sec):
            if not fits_int(v):
                return None
        t = timegm_norm(tm_year, mon, mday, hour, minute, sec) - self.off
        if not fits_i64(t):
            return None
        tm = self.localtime(t)
        if tm is None:
            return None
        return t, tm


class ZoneTZ(FixedTZ):
    def __init__(self, zi):
        import datetime
        self.zi = zi
        self.dt = datetime
        # fallback offset for timestamps outside datetime's range
        try:
            d = datetime.datetime(2000, 1, 1, tzinfo=zi)
            self.off = int(d.utcoffset().total_seconds())
            self.abbr = (d.tzname() or 'UTC').encode()
        except Exception:
            self.off = 0
            self.abbr = b'UTC'
        self.isdst = 0

    def offset_at(self, t):
        datetime = self.dt
        try:
            if not (-62135596800 + 86400 <= t <= 253402300799 - 86400):
                raise OverflowError
            d = datetime.datetime.fromtimestamp(t, self.zi)
            off = int(d.utcoffset().total_seconds())
            dst = d.dst()
            return off, (d.tzname() or '').encode(), 1 if dst else 0
        except Exception:
            return self.off, self.abbr, 0

    def mktime(self, tm_year, mon, mday, hour, minute, sec):
        for v in (tm_year, mon, mday, hour, minute, sec):
            if not fits_int(v):
                return None
        naive = timegm_norm(tm_year, mon, mday, hour, minute, sec)
        off = self.off
        try:
            if not (-62135596800 + 86400 <= naive <= 253402300799 - 86400):
                raise OverflowError
            f = gm_fields(naive)
            datetime = self.dt
            d = datetime.datetime(f.year, f.mon + 1, f.mday, f.hour, f.min,
                                  f.sec, tzinfo=self.zi, fold=0)
            off = int(d.utcoffset().total_seconds())
        except Exception:
            pass
        t = naive - off
        if not fits_i64(t):
            return None
        tm = self.localtime(t)
        if tm is None:
            return None
        return t, tm


def _parse_posix_offset(s, i):
    n = len(s)
    sign = 1
    if i < n and s[i] in '+-':
        if s[i] == '-':
            sign = -1
        i += 1
    j = i
    while j < n and s[j].isdigit() and s[j].isascii():
        j += 1
    if j == i:
        return None
    secs = int(s[i:j]) * 3600
    i = j
    for mult in (60, 1):
        if i < n and s[i] == ':':
            j = i + 1
            while j < n and s[j].isdigit() and s[j].isascii():
                j += 1
            if j == i + 1:
                return None
            secs += int(s[i + 1:j]) * mult
            i = j
        else:
            break
    return sign * secs, i


def _parse_posix_name(s, i):
    n = len(s)
    if i < n and s[i] == '<':
        j = s.find('>', i)
        if j < 0:
            return None
        return s[i + 1:j], j + 1
    j = i
    while j < n and s[j].isalpha() and s[j].isascii():
        j += 1
    if j - i < 3:
        return None
    return s[i:j], j


def make_tz(tzstring):
    if tzstring is None:
        tzstring = ''
    if isinstance(tzstring, bytes):
        tzstring = tzstring.decode('utf-8', 'surrogateescape')
    s = tzstring
    if s.startswith(':'):
        s = s[1:]
    if s == '':
        return FixedTZ(0, b'UTC')
    r = _parse_posix_name(s, 0)
    std = None
    if r is not None:
        name, i = r
        o = _parse_posix_offset(s, i)
        if o is not None:
            off, i = o
            std = FixedTZ(-off, name.encode('utf-8', 'surrogateescape'))
            if i == len(s):
                return std
    try:
        import zoneinfo
        if '..' not in s and not s.startswith('/'):
            return ZoneTZ(zoneinfo.ZoneInfo(s))
    except Exception:
        pass
    if std is not None:
        return std
    return FixedTZ(0, b'UTC')


# ---------------------------------------------------------------------------
# Date string lexer (gnulib parse-datetime.y)

MERam, MERpm, MER24 = 0, 1, 2

UNITS = ('YEAR_UNIT', 'MONTH_UNIT', 'DAY_UNIT', 'HOUR_UNIT', 'MINUTE_UNIT',
         'SEC_UNIT')


def HOUR(x):
    return x * 3600


MERIDIAN_TABLE = [(b'AM', 'MERIDIAN', MERam), (b'A.M.', 'MERIDIAN', MERam),
                  (b'PM', 'MERIDIAN', MERpm), (b'P.M.', 'MERIDIAN', MERpm)]

MONTH_AND_DAY_TABLE = [
    (b'JANUARY', 'MONTH', 1), (b'FEBRUARY', 'MONTH', 2),
    (b'MARCH', 'MONTH', 3), (b'APRIL', 'MONTH', 4), (b'MAY', 'MONTH', 5),
    (b'JUNE', 'MONTH', 6), (b'JULY', 'MONTH', 7), (b'AUGUST', 'MONTH', 8),
    (b'SEPTEMBER', 'MONTH', 9), (b'SEPT', 'MONTH', 9),
    (b'OCTOBER', 'MONTH', 10), (b'NOVEMBER', 'MONTH', 11),
    (b'DECEMBER', 'MONTH', 12),
    (b'SUNDAY', 'DAY', 0), (b'MONDAY', 'DAY', 1), (b'TUESDAY', 'DAY', 2),
    (b'TUES', 'DAY', 2), (b'WEDNESDAY', 'DAY', 3), (b'WEDNES', 'DAY', 3),
    (b'THURSDAY', 'DAY', 4), (b'THUR', 'DAY', 4), (b'THURS', 'DAY', 4),
    (b'FRIDAY', 'DAY', 5), (b'SATURDAY', 'DAY', 6),
]

TIME_UNITS_TABLE = [
    (b'YEAR', 'YEAR_UNIT', 1), (b'MONTH', 'MONTH_UNIT', 1),
    (b'FORTNIGHT', 'DAY_UNIT', 14), (b'WEEK', 'DAY_UNIT', 7),
    (b'DAY', 'DAY_UNIT', 1), (b'HOUR', 'HOUR_UNIT', 1),
    (b'MINUTE', 'MINUTE_UNIT', 1), (b'MIN', 'MINUTE_UNIT', 1),
    (b'SECOND', 'SEC_UNIT', 1), (b'SEC', 'SEC_UNIT', 1),
]

RELATIVE_TIME_TABLE = [
    (b'TOMORROW', 'DAY_SHIFT', 1), (b'YESTERDAY', 'DAY_SHIFT', -1),
    (b'TODAY', 'DAY_SHIFT', 0), (b'NOW', 'DAY_SHIFT', 0),
    (b'LAST', 'ORDINAL', -1), (b'THIS', 'ORDINAL', 0),
    (b'NEXT', 'ORDINAL', 1), (b'FIRST', 'ORDINAL', 1),
    (b'THIRD', 'ORDINAL', 3), (b'FOURTH', 'ORDINAL', 4),
    (b'FIFTH', 'ORDINAL', 5), (b'SIXTH', 'ORDINAL', 6),
    (b'SEVENTH', 'ORDINAL', 7), (b'EIGHTH', 'ORDINAL', 8),
    (b'NINTH', 'ORDINAL', 9), (b'TENTH', 'ORDINAL', 10),
    (b'ELEVENTH', 'ORDINAL', 11), (b'TWELFTH', 'ORDINAL', 12),
    (b'AGO', 'AGO', -1), (b'HENCE', 'AGO', 1),
]

UNIVERSAL_TIME_ZONE_TABLE = [(b'GMT', 'ZONE', 0), (b'UT', 'ZONE', 0),
                             (b'UTC', 'ZONE', 0)]

TIME_ZONE_TABLE = [
    (b'WET', 'ZONE', HOUR(0)), (b'WEST', 'DAYZONE', HOUR(0)),
    (b'BST', 'DAYZONE', HOUR(0)), (b'ART', 'ZONE', -HOUR(3)),
    (b'BRT', 'ZONE', -HOUR(3)), (b'BRST', 'DAYZONE', -HOUR(3)),
    (b'NST', 'ZONE', -(HOUR(3) + 30 * 60)),
    (b'NDT', 'DAYZONE', -(HOUR(3) + 30 * 60)),
    (b'AST', 'ZONE', -HOUR(4)), (b'ADT', 'DAYZONE', -HOUR(4)),
    (b'CLT', 'ZONE', -HOUR(4)), (b'CLST', 'DAYZONE', -HOUR(4)),
    (b'EST', 'ZONE', -HOUR(5)), (b'EDT', 'DAYZONE', -HOUR(5)),
    (b'CST', 'ZONE', -HOUR(6)), (b'CDT', 'DAYZONE', -HOUR(6)),
    (b'MST', 'ZONE', -HOUR(7)), (b'MDT', 'DAYZONE', -HOUR(7)),
    (b'PST', 'ZONE', -HOUR(8)), (b'PDT', 'DAYZONE', -HOUR(8)),
    (b'AKST', 'ZONE', -HOUR(9)), (b'AKDT', 'DAYZONE', -HOUR(9)),
    (b'HST', 'ZONE', -HOUR(10)), (b'HAST', 'ZONE', -HOUR(10)),
    (b'HADT', 'DAYZONE', -HOUR(10)), (b'SST', 'ZONE', -HOUR(12)),
    (b'WAT', 'ZONE', HOUR(1)), (b'CET', 'ZONE', HOUR(1)),
    (b'CEST', 'DAYZONE', HOUR(1)), (b'MET', 'ZONE', HOUR(1)),
    (b'MEZ', 'ZONE', HOUR(1)), (b'MEST', 'DAYZONE', HOUR(1)),
    (b'MESZ', 'DAYZONE', HOUR(1)), (b'EET', 'ZONE', HOUR(2)),
    (b'EEST', 'DAYZONE', HOUR(2)), (b'CAT', 'ZONE', HOUR(2)),
    (b'SAST', 'ZONE', HOUR(2)), (b'EAT', 'ZONE', HOUR(3)),
    (b'MSK', 'ZONE', HOUR(3)), (b'MSD', 'DAYZONE', HOUR(3)),
    (b'IST', 'ZONE', HOUR(5) + 30 * 60), (b'SGT', 'ZONE', HOUR(8)),
    (b'KST', 'ZONE', HOUR(9)), (b'JST', 'ZONE', HOUR(9)),
    (b'GST', 'ZONE', HOUR(10)), (b'NZST', 'ZONE', HOUR(12)),
    (b'NZDT', 'DAYZONE', HOUR(12)),
]

MILITARY_TABLE = [
    (b'A', 'ZONE', -HOUR(1)), (b'B', 'ZONE', -HOUR(2)),
    (b'C', 'ZONE', -HOUR(3)), (b'D', 'ZONE', -HOUR(4)),
    (b'E', 'ZONE', -HOUR(5)), (b'F', 'ZONE', -HOUR(6)),
    (b'G', 'ZONE', -HOUR(7)), (b'H', 'ZONE', -HOUR(8)),
    (b'I', 'ZONE', -HOUR(9)), (b'K', 'ZONE', -HOUR(10)),
    (b'L', 'ZONE', -HOUR(11)), (b'M', 'ZONE', -HOUR(12)),
    (b'N', 'ZONE', HOUR(1)), (b'O', 'ZONE', HOUR(2)),
    (b'P', 'ZONE', HOUR(3)), (b'Q', 'ZONE', HOUR(4)),
    (b'R', 'ZONE', HOUR(5)), (b'S', 'ZONE', HOUR(6)),
    (b'T', 'T', 0), (b'U', 'ZONE', HOUR(8)),
    (b'V', 'ZONE', HOUR(9)), (b'W', 'ZONE', HOUR(10)),
    (b'X', 'ZONE', HOUR(11)), (b'Y', 'ZONE', HOUR(12)),
    (b'Z', 'ZONE', HOUR(0)),
]


def c_isspace(c):
    return c in (32, 9, 10, 11, 12, 13)


def c_isdigit(c):
    return 48 <= c <= 57


def c_isalpha(c):
    return 65 <= c <= 90 or 97 <= c <= 122


def lookup_zone(word, local_table):
    for name, typ, val in UNIVERSAL_TIME_ZONE_TABLE:
        if word == name:
            return typ, val
    for name, typ, val in local_table:
        if word == name:
            return typ, val
    for name, typ, val in TIME_ZONE_TABLE:
        if word == name:
            return typ, val
    return None


def lookup_word(word, local_table):
    word = word.upper()
    for name, typ, val in MERIDIAN_TABLE:
        if word == name:
            return typ, val
    wordlen = len(word)
    abbrev = wordlen == 3 or (wordlen == 4 and word[3:4] == b'.')
    for name, typ, val in MONTH_AND_DAY_TABLE:
        if (word[:3] == name[:3]) if abbrev else (word == name):
            return typ, val
    r = lookup_zone(word, local_table)
    if r:
        return r
    if word == b'DST':
        return 'DST', 0
    for name, typ, val in TIME_UNITS_TABLE:
        if word == name:
            return typ, val
    if word.endswith(b'S'):
        w2 = word[:-1]
        for name, typ, val in TIME_UNITS_TABLE:
            if w2 == name:
                return typ, val
    for name, typ, val in RELATIVE_TIME_TABLE:
        if word == name:
            return typ, val
    if wordlen == 1:
        for name, typ, val in MILITARY_TABLE:
            if word == name:
                return typ, val
    if b'.' in word:
        r = lookup_zone(word.replace(b'.', b''), local_table)
        if r:
            return r
    return None


class Tok(object):
    __slots__ = ('kind', 'val', 'digits', 'neg')

    def __init__(self, kind, val=0, digits=0, neg=False):
        self.kind = kind
        self.val = val
        self.digits = digits
        self.neg = neg


def lex(s, local_table):
    toks = []
    n = len(s)
    i = 0
    while True:
        while i < n and c_isspace(s[i]):
            i += 1
        if i >= n:
            toks.append(Tok('EOF'))
            return toks
        c = s[i]
        if c_isdigit(c) or c == 45 or c == 43:
            if c == 45 or c == 43:
                sign = -1 if c == 45 else 1
                i += 1
                while i < n and c_isspace(s[i]):
                    i += 1
                if not (i < n and c_isdigit(s[i])):
                    continue
            else:
                sign = 0
            p = i
            value = 0
            overflow = False
            while p < n and c_isdigit(s[p]):
                d = s[p] - 48
                value = value * 10 + (-d if sign < 0 else d)
                if not fits_i64(value):
                    overflow = True
                    break
                p += 1
            if overflow:
                toks.append(Tok('ERR'))
                toks.append(Tok('EOF'))
                return toks
            if (p < n and s[p] in (46, 44) and p + 1 < n
                    and c_isdigit(s[p + 1])):
                sec = value
                p += 1
                ns = s[p] - 48
                p += 1
                for _ in range(2, 10):
                    ns *= 10
                    if p < n and c_isdigit(s[p]):
                        ns += s[p] - 48
                        p += 1
                if sign < 0:
                    while p < n and c_isdigit(s[p]):
                        if s[p] != 48:
                            ns += 1
                            break
                        p += 1
                while p < n and c_isdigit(s[p]):
                    p += 1
                if sign < 0 and ns:
                    sec -= 1
                    if not fits_i64(sec):
                        toks.append(Tok('ERR'))
                        toks.append(Tok('EOF'))
                        return toks
                    ns = BILLION - ns
                toks.append(Tok('SDEC' if sign else 'UDEC', (sec, ns)))
                i = p
            else:
                toks.append(Tok('SNUM' if sign else 'UNUM', value, p - i,
                                sign < 0))
                i = p
            continue
        if c_isalpha(c):
            buf = bytearray()
            while True:
                if len(buf) < 19:
                    buf.append(c)
                i += 1
                if i >= n:
                    break
                c = s[i]
                if not (c_isalpha(c) or c == 46):
                    break
            r = lookup_word(bytes(buf), local_table)
            if r is None:
                toks.append(Tok('ERR'))
                toks.append(Tok('EOF'))
                return toks
            toks.append(Tok(r[0], r[1]))
            continue
        if c != 40:  # '('
            toks.append(Tok(chr(c) if c < 128 else 'CHR%d' % c))
            i += 1
            continue
        count = 0
        while True:
            if i >= n:
                toks.append(Tok('EOF'))
                return toks
            c = s[i]
            i += 1
            if c == 40:
                count += 1
            elif c == 41:
                count -= 1
            if count == 0:
                break


# ---------------------------------------------------------------------------
# Date string parser

class ParseFail(Exception):
    pass


class PC(object):
    pass


def new_rel():
    return {'year': 0, 'month': 0, 'day': 0, 'hour': 0, 'minutes': 0,
            'seconds': 0, 'ns': 0}


def apply_relative_time(pc, rel, factor):
    for k in ('ns', 'seconds', 'minutes', 'hour', 'day', 'month', 'year'):
        v = pc.rel[k] + rel[k] * (1 if factor >= 0 else -1)
        if k == 'ns':
            if not fits_int(v):
                raise ParseFail
        elif not fits_i64(v):
            raise ParseFail
        pc.rel[k] = v
    pc.rels_seen = True


def time_zone_hhmm(pc, s, mm):
    value = s.val
    if s.digits <= 2 and mm < 0:
        value *= 100
    if mm < 0:
        n_minutes = cdiv(value, 100) * 60 + cmod(value, 100)
    else:
        n_minutes = value * 60 + (-mm if s.neg else mm)
    if not (-24 * 60 <= n_minutes <= 24 * 60):
        raise ParseFail
    pc.time_zone = n_minutes * 60


def digits_to_date_time(pc, t):
    if (pc.dates_seen and not pc.year[1] and not pc.rels_seen
            and (pc.times_seen or 2 < t.digits)):
        pc.year = (t.val, t.digits)
    else:
        if 4 < t.digits:
            pc.dates_seen += 1
            pc.day = t.val % 100
            pc.month = (t.val // 100) % 100
            pc.year = (t.val // 10000, t.digits - 4)
        else:
            pc.times_seen += 1
            if t.digits <= 2:
                pc.hour = t.val
                pc.minutes = 0
            else:
                pc.hour = t.val // 100
                pc.minutes = t.val % 100
            pc.sec = 0
            pc.nsec = 0
            pc.meridian = MER24


def make_relunit(kind, n, unitval, ns=0):
    rel = new_rel()
    if kind == 'YEAR_UNIT':
        rel['year'] = n
    elif kind == 'MONTH_UNIT':
        rel['month'] = n
    elif kind == 'DAY_UNIT':
        v = n * unitval
        if not fits_i64(v):
            raise ParseFail
        rel['day'] = v
    elif kind == 'HOUR_UNIT':
        rel['hour'] = n
    elif kind == 'MINUTE_UNIT':
        rel['minutes'] = n
    else:
        rel['seconds'] = n
        rel['ns'] = ns
    return rel


class Parser(object):
    def __init__(self, toks, pc):
        self.toks = toks
        self.i = 0
        self.pc = pc

    def peek(self):
        return self.toks[self.i]

    def take(self):
        t = self.toks[self.i]
        if t.kind != 'EOF':
            self.i += 1
        return t

    def expect(self, *kinds):
        t = self.peek()
        if t.kind not in kinds:
            raise ParseFail
        return self.take()

    def parse(self):
        pc = self.pc
        t = self.peek()
        if t.kind == '@':
            self.take()
            t = self.take()
            if t.kind in ('UNUM', 'SNUM'):
                pc.ts = (t.val, 0)
            elif t.kind in ('UDEC', 'SDEC'):
                pc.ts = t.val
            else:
                raise ParseFail
            pc.timespec_seen = True
            if self.peek().kind != 'EOF':
                raise ParseFail
            return
        while self.peek().kind != 'EOF':
            self.item()

    def rel_tail(self, rel):
        t = self.peek()
        if t.kind == 'AGO':
            self.take()
            apply_relative_time(self.pc, rel, t.val)
        else:
            apply_relative_time(self.pc, rel, 1)

    def set_hhmmss(self, h, m, sec, ns):
        pc = self.pc
        pc.hour = h
        pc.minutes = m
        pc.sec = sec
        pc.nsec = ns

    def o_zone_offset(self):
        if self.peek().kind == 'SNUM':
            self.zone_offset(self.take())

    def zone_offset(self, s):
        mm = -1
        if self.peek().kind == ':':
            self.take()
            mm = self.expect('UNUM').val
        self.pc.zones_seen += 1
        time_zone_hhmm(self.pc, s, mm)

    def unsigned_seconds(self):
        t = self.expect('UNUM', 'UDEC')
        if t.kind == 'UNUM':
            return t.val, 0
        return t.val

    def iso_8601_time(self):
        pc = self.pc
        h = self.expect('UNUM')
        t = self.peek()
        if t.kind == 'SNUM':
            self.zone_offset(self.take())
            self.set_hhmmss(h.val, 0, 0, 0)
        elif t.kind == ':':
            self.take()
            m = self.expect('UNUM')
            if self.peek().kind == ':':
                self.take()
                sec, ns = self.unsigned_seconds()
                self.o_zone_offset()
                self.set_hhmmss(h.val, m.val, sec, ns)
            else:
                self.o_zone_offset()
                self.set_hhmmss(h.val, m.val, 0, 0)
        else:
            raise ParseFail
        pc.meridian = MER24

    def item(self):
        pc = self.pc
        t = self.take()
        k = t.kind
        if k == 'UNUM':
            n2 = self.peek()
            if n2.kind == 'MERIDIAN':
                self.take()
                self.set_hhmmss(t.val, 0, 0, 0)
                pc.meridian = n2.val
                pc.times_seen += 1
            elif n2.kind == ':':
                self.take()
                m = self.expect('UNUM')
                n4 = self.peek()
                if n4.kind == 'MERIDIAN':
                    self.take()
                    self.set_hhmmss(t.val, m.val, 0, 0)
                    pc.meridian = n4.val
                elif n4.kind == ':':
                    self.take()
                    sec, ns = self.unsigned_seconds()
                    n6 = self.peek()
                    if n6.kind == 'MERIDIAN':
                        self.take()
                        self.set_hhmmss(t.val, m.val, sec, ns)
                        pc.meridian = n6.val
                    else:
                        self.o_zone_offset()
                        self.set_hhmmss(t.val, m.val, sec, ns)
                        pc.meridian = MER24
                else:
                    self.o_zone_offset()
                    self.set_hhmmss(t.val, m.val, 0, 0)
                    pc.meridian = MER24
                pc.times_seen += 1
            elif n2.kind == 'SNUM':
                s = self.take()
                n3 = self.peek()
                if n3.kind == 'SNUM':
                    s2 = self.take()
                    pc.year = (t.val, t.digits)
                    pc.month = -s.val
                    pc.day = -s2.val
                    if self.peek().kind == 'T':
                        self.take()
                        self.iso_8601_time()
                        pc.times_seen += 1
                        pc.dates_seen += 1
                    else:
                        pc.dates_seen += 1
                elif n3.kind in UNITS:
                    u = self.take()
                    digits_to_date_time(pc, t)
                    apply_relative_time(pc, make_relunit(u.kind, s.val,
                                                         u.val), 1)
                else:
                    self.zone_offset(s)
                    self.set_hhmmss(t.val, 0, 0, 0)
                    pc.meridian = MER24
                    pc.times_seen += 1
            elif n2.kind == 'DAY':
                self.take()
                pc.day_ordinal = t.val
                pc.day_number = n2.val
                pc.days_seen += 1
            elif n2.kind == '/':
                self.take()
                b = self.expect('UNUM')
                if self.peek().kind == '/':
                    self.take()
                    c = self.expect('UNUM')
                    if 4 <= t.digits:
                        pc.year = (t.val, t.digits)
                        pc.month = b.val
                        pc.day = c.val
                    else:
                        pc.month = t.val
                        pc.day = b.val
                        pc.year = (c.val, c.digits)
                else:
                    pc.month = t.val
                    pc.day = b.val
                pc.dates_seen += 1
            elif n2.kind == 'MONTH':
                self.take()
                n3 = self.peek()
                pc.day = t.val
                pc.month = n2.val
                if n3.kind == 'SNUM':
                    self.take()
                    pc.year = (-n3.val, n3.digits)
                elif n3.kind == 'UNUM':
                    self.take()
                    pc.year = (n3.val, n3.digits)
                pc.dates_seen += 1
            elif n2.kind in UNITS:
                u = self.take()
                self.rel_tail(make_relunit(u.kind, t.val, u.val))
            else:
                digits_to_date_time(pc, t)
        elif k == 'SNUM':
            u = self.peek()
            if u.kind not in UNITS:
                raise ParseFail
            self.take()
            self.rel_tail(make_relunit(u.kind, t.val, u.val))
        elif k in ('UDEC', 'SDEC'):
            self.expect('SEC_UNIT')
            self.rel_tail(make_relunit('SEC_UNIT', t.val[0], 1, t.val[1]))
        elif k == 'ORDINAL':
            n2 = self.peek()
            if n2.kind == 'DAY':
                self.take()
                pc.day_ordinal = t.val
                pc.day_number = n2.val
                pc.days_seen += 1
            elif n2.kind in UNITS:
                u = self.take()
                self.rel_tail(make_relunit(u.kind, t.val, u.val))
            else:
                raise ParseFail
        elif k in UNITS:
            if k == 'DAY_UNIT':
                rel = make_relunit(k, 1, t.val)
            else:
                rel = make_relunit(k, 1, 1)
            self.rel_tail(rel)
        elif k == 'DAY_SHIFT':
            rel = new_rel()
            rel['day'] = t.val
            apply_relative_time(pc, rel, 1)
        elif k == 'DAY':
            if self.peek().kind == ',':
                self.take()
            pc.day_ordinal = 0
            pc.day_number = t.val
            pc.days_seen += 1
        elif k == 'MONTH':
            n2 = self.peek()
            if n2.kind == 'SNUM':
                self.take()
                n3 = self.expect('SNUM')
                pc.month = t.val
                pc.day = -n2.val
                pc.year = (-n3.val, n3.digits)
            elif n2.kind == 'UNUM':
                self.take()
                pc.month = t.val
                pc.day = n2.val
                if self.peek().kind == ',':
                    self.take()
                    y = self.expect('UNUM')
                    pc.year = (y.val, y.digits)
            else:
                raise ParseFail
            pc.dates_seen += 1
        elif k == 'ZONE':
            n2 = self.peek()
            if n2.kind == 'SNUM':
                s = self.take()
                n3 = self.peek()
                if n3.kind in UNITS:
                    u = self.take()
                    pc.time_zone = t.val
                    apply_relative_time(pc, make_relunit(u.kind, s.val,
                                                         u.val), 1)
                else:
                    mm = -1
                    if n3.kind == ':':
                        self.take()
                        mm = self.expect('UNUM').val
                    time_zone_hhmm(pc, s, mm)
                    pc.time_zone += t.val
            elif n2.kind == 'DST':
                self.take()
                pc.time_zone = t.val + 3600
            else:
                pc.time_zone = t.val
            pc.zones_seen += 1
        elif k == 'T':
            pc.time_zone = -HOUR(7)
            if self.peek().kind == 'SNUM':
                s = self.take()
                u = self.peek()
                if u.kind not in UNITS:
                    raise ParseFail
                self.take()
                apply_relative_time(pc, make_relunit(u.kind, s.val, u.val),
                                    1)
            pc.zones_seen += 1
        elif k == 'DAYZONE':
            pc.time_zone = t.val + 3600
            pc.zones_seen += 1
        else:
            raise ParseFail


def to_hour(hours, meridian):
    if meridian == MER24:
        return hours if 0 <= hours < 24 else -1
    if meridian == MERam:
        return hours if 0 < hours < 12 else (0 if hours == 12 else -1)
    return hours + 12 if 0 < hours < 12 else (12 if hours == 12 else -1)


def same_fields(tm0, tm):
    return (tm0[0] == tm.tm_year and tm0[1] == tm.mon and tm0[2] == tm.mday
            and tm0[3] == tm.hour and tm0[4] == tm.min and tm0[5] == tm.sec)


def parse_datetime(s, tz, now_ns):
    """Return (sec, nsec) or None."""
    if b'\0' in s:
        s = s[:s.index(b'\0')]
    p = 0
    n = len(s)
    while p < n and c_isspace(s[p]):
        p += 1
    if s[p:p + 4] == b'TZ="':
        q = p + 4
        buf = bytearray()
        while q < n:
            c = s[q]
            if c == 92:
                q += 1
                if not (q < n and s[q] in (92, 34)):
                    break
                buf.append(s[q])
            elif c == 34:
                tz = make_tz(bytes(buf))
                p = q + 1
                break
            else:
                buf.append(c)
            q += 1
    try:
        return _parse_body(s[p:], tz, now_ns)
    except ParseFail:
        return None


def _parse_body(s, tz, now_ns):
    now_sec, now_nsec = divmod(now_ns, BILLION)
    tmp = tz.localtime(now_sec)
    if tmp is None:
        raise ParseFail
    pc = PC()
    pc.year = (tmp.year, 0)
    pc.month = tmp.mon + 1
    pc.day = tmp.mday
    pc.hour = tmp.hour
    pc.minutes = tmp.min
    pc.sec = tmp.sec
    pc.nsec = now_nsec
    pc.meridian = MER24
    pc.rel = new_rel()
    pc.timespec_seen = False
    pc.rels_seen = False
    pc.dates_seen = 0
    pc.days_seen = 0
    pc.times_seen = 0
    pc.local_zones_seen = 0
    pc.dsts_seen = 0
    pc.zones_seen = 0
    pc.time_zone = 0
    pc.day_ordinal = 0
    pc.day_number = 0

    toks = lex(s, [])
    Parser(toks, pc).parse()

    if pc.timespec_seen:
        return pc.ts

    if 1 < (pc.times_seen | pc.dates_seen | pc.days_seen | pc.dsts_seen
            | (pc.local_zones_seen + pc.zones_seen)):
        raise ParseFail

    yv, yd = pc.year
    if 0 <= yv and yd == 2:
        yv += 2000 if yv < 69 else 1900
    tm_year = yv - 1900 if yv >= 0 else -1900 - yv
    if not fits_int(tm_year):
        raise ParseFail
    tm_mon = pc.month - 1
    tm_mday = pc.day
    if not (fits_int(tm_mon) and fits_int(tm_mday)):
        raise ParseFail
    if pc.times_seen or (pc.rels_seen and not pc.dates_seen
                         and not pc.days_seen):
        h = to_hour(pc.hour, pc.meridian)
        if h < 0:
            raise ParseFail
        mi = pc.minutes
        se = pc.sec
        nsec = pc.nsec
    else:
        h = mi = se = 0
        nsec = 0
    tm0 = (tm_year, tm_mon, tm_mday, h, mi, se)

    r = tz.mktime(*tm0)
    if r is None or not same_fields(tm0, r[1]):
        if not pc.zones_seen:
            raise ParseFail
        r = FixedTZ(pc.time_zone).mktime(*tm0)
        if r is None or not same_fields(tm0, r[1]):
            raise ParseFail
    start, tm = r

    if pc.days_seen and not pc.dates_seen:
        ordinal = pc.day_ordinal - (1 if (0 < pc.day_ordinal
                                          and tm.wday != pc.day_number)
                                    else 0)
        dayincr = ordinal * 7
        dayincr += (pc.day_number - tm.wday + 7) % 7
        mday = dayincr + tm.mday
        r = None
        if fits_i64(ordinal * 7) and fits_int(mday):
            r = tz.mktime(tm.tm_year, tm.mon, mday, tm.hour, tm.min, tm.sec)
        if r is None:
            raise ParseFail
        start, tm = r

    rel = pc.rel
    if rel['year'] or rel['month'] or rel['day']:
        year = tm.tm_year + rel['year']
        month = tm.mon + rel['month']
        day = tm.mday + rel['day']
        if not (fits_int(year) and fits_int(month) and fits_int(day)):
            raise ParseFail
        r = tz.mktime(year, month, day, tm0[3], tm0[4], tm0[5])
        if r is None:
            raise ParseFail
        start, tm = r

    if pc.zones_seen:
        delta = pc.time_zone - tm.gmtoff
        start -= delta
        if not fits_i64(start):
            raise ParseFail

    sum_ns = nsec + rel['ns']
    normalized_ns = sum_ns % BILLION
    d4 = (sum_ns - normalized_ns) // BILLION
    d1 = rel['hour'] * 3600
    if not fits_i64(d1):
        raise ParseFail
    t1 = start + d1
    if not fits_i64(t1):
        raise ParseFail
    d2 = rel['minutes'] * 60
    if not fits_i64(d2):
        raise ParseFail
    t2 = t1 + d2
    if not fits_i64(t2):
        raise ParseFail
    t3 = t2 + rel['seconds']
    if not fits_i64(t3):
        raise ParseFail
    t4 = t3 + d4
    if not fits_i64(t4):
        raise ParseFail
    return t4, normalized_ns


# ---------------------------------------------------------------------------
# strftime (gnulib nstrftime, C locale)

A_WKDAY = [b'Sun', b'Mon', b'Tue', b'Wed', b'Thu', b'Fri', b'Sat']
F_WKDAY = [b'Sunday', b'Monday', b'Tuesday', b'Wednesday', b'Thursday',
           b'Friday', b'Saturday']
A_MONTH = [b'Jan', b'Feb', b'Mar', b'Apr', b'May', b'Jun', b'Jul', b'Aug',
           b'Sep', b'Oct', b'Nov', b'Dec']
F_MONTH = [b'January', b'February', b'March', b'April', b'May', b'June',
           b'July', b'August', b'September', b'October', b'November',
           b'December']


def ascii_upper(b):
    return bytes(c - 32 if 97 <= c <= 122 else c for c in b)


def ascii_lower(b):
    return bytes(c + 32 if 65 <= c <= 90 else c for c in b)


def iso_week_days(yday, wday):
    big = (366 // 7 + 2) * 7
    return yday - (yday - wday + 4 + big) % 7 + 4 - 1


def glibc_underlying(fc, modifier, tm):
    """What glibc strftime produces for ' %<mod><fc>' in the C locale."""
    def two(v):
        return b'%02d' % v

    hour12 = tm.hour % 12 or 12
    tm_year = tm.tm_year
    yy = cmod(tm_year, 100)
    if yy < 0:
        yy = -yy if tm_year < -1900 else yy + 100
    Y = str(tm.year).encode()
    if fc == 'a':
        return A_WKDAY[tm.wday]
    if fc == 'A':
        return F_WKDAY[tm.wday]
    if fc in ('b', 'h'):
        return A_MONTH[tm.mon]
    if fc == 'B':
        return F_MONTH[tm.mon]
    if fc == 'p':
        return b'PM' if tm.hour >= 12 else b'AM'
    if fc == 'c':
        return b'%s %s %2d %s:%s:%s %s' % (
            A_WKDAY[tm.wday], A_MONTH[tm.mon], tm.mday, two(tm.hour),
            two(tm.min), two(tm.sec), Y)
    if fc == 'x':
        return b'%s/%s/%s' % (two(tm.mon + 1), two(tm.mday), two(yy))
    if fc == 'X':
        return b'%s:%s:%s' % (two(tm.hour), two(tm.min), two(tm.sec))
    if fc == 'r':
        return b'%s:%s:%s %s' % (two(hour12), two(tm.min), two(tm.sec),
                                 b'PM' if tm.hour >= 12 else b'AM')
    if fc == 'y':
        return two(yy)
    if fc == 'Y':
        return Y
    if fc == 'C':
        year = tm.year
        century = cdiv(year, 100) - (1 if cmod(year, 100) < 0 else 0)
        return b'%d' % century
    return b''


def nstrftime(fmt, tm, ns, upcase=False, yr_spec=0, width=-1):
    out = bytearray()
    n = len(fmt)
    i = 0
    hour12 = tm.hour
    if hour12 > 12:
        hour12 -= 12
    elif hour12 == 0:
        hour12 = 12
    tm_year = tm.tm_year

    while i < n:
        c = fmt[i]
        if c != 37:
            # literal character (width only possible via subformat width)
            if width > 0:
                out += b' ' * (width - 1)
            out.append(c)
            i += 1
            width = -1
            continue
        start = i
        pad = 0
        to_up = upcase
        to_low = False
        change_case = False
        i += 1
        while i < n:
            ch = fmt[i]
            if ch in (95, 45, 43, 48):  # _ - + 0
                pad = chr(ch)
                i += 1
            elif ch == 94:  # ^
                to_up = True
                i += 1
            elif ch == 35:  # #
                change_case = True
                i += 1
            else:
                break
        if i < n and c_isdigit(fmt[i]):
            width = 0
            while i < n and c_isdigit(fmt[i]):
                width = width * 10 + fmt[i] - 48
                if width > INT_MAX:
                    width = INT_MAX
                i += 1
        modifier = None
        if i < n and fmt[i] in (69, 79):
            modifier = chr(fmt[i])
            i += 1

        # helpers -------------------------------------------------------
        def pad_text(s, w, p):
            if p == '-' or w < 0 or len(s) >= w:
                return s
            fill = b'0' if p in ('0', '+') else b' '
            return fill * (w - len(s)) + s

        def cpy(s):
            if to_low:
                s = ascii_lower(s)
            elif to_up:
                s = ascii_upper(s)
            return pad_text(s, width, pad)

        def num_out(ds, neg, always, p, w, digits):
            if p == 0:
                p = '0'
            if w < 0:
                w = digits
            sign = b'-' if neg else (b'+' if always else b'')
            if p == '-':
                return sign + ds
            short = w - len(sign) - len(ds)
            if p == '_':
                return b' ' * max(0, short) + sign + ds
            return sign + b'0' * max(0, short) + ds

        def do_number(digits, value, p=None):
            pp = pad if p is None else p
            return num_out(b'%d' % abs(value), value < 0, False, pp, width,
                           digits)

        def do_spacepad(digits, value):
            pp = pad if pad != 0 else '_'
            return do_number(digits, value, pp)

        def do_yearish(digits, neg, u):
            pp = pad
            if pp == 0:
                pp = yr_spec
            always = (pp == '+' and (neg or
                                     (99 if digits == 2 else 9999) < u
                                     or digits < width))
            return num_out(b'%d' % u, neg, always, pp, width, digits)

        def do_tz(digits, mask, u, neg):
            buf = bytearray()
            while True:
                if mask & 1:
                    buf.append(58)
                mask >>= 1
                buf.append(48 + u % 10)
                u //= 10
                if u == 0 and mask == 0:
                    break
            buf.reverse()
            return num_out(bytes(buf), neg, True, pad, width, digits)

        def bad():
            return cpy(fmt[start:i + 1])

        if i >= n:
            # '%' (plus flags etc.) at end of format
            out += cpy(fmt[start:n])
            break

        fc = chr(fmt[i])
        res = None
        if fc == '%':
            res = bad() if modifier else pad_text(b'%', width, pad)
        elif fc in ('a', 'A'):
            if modifier:
                res = bad()
            else:
                if change_case:
                    to_up, to_low = True, False
                res = cpy(glibc_underlying(fc, modifier, tm))
        elif fc in ('b', 'h', 'B'):
            if change_case:
                to_up, to_low = True, False
            if modifier == 'E':
                res = bad()
            else:
                res = cpy(glibc_underlying(fc, modifier, tm))
        elif fc == 'c':
            if modifier == 'O':
                res = bad()
            else:
                res = cpy(glibc_underlying('c', modifier, tm))
        elif fc == 'C':
            if modifier == 'E':
                res = cpy(glibc_underlying('C', modifier, tm))
            else:
                neg = tm_year < -1900
                z = (not neg) and tm_year < 0
                century = cdiv(tm_year - 99 * z, 100) + 19
                res = do_yearish(2, neg, -century if neg else century)
        elif fc in ('x', 'X'):
            if modifier == 'O':
                res = bad()
            else:
                res = cpy(glibc_underlying(fc, modifier, tm))
        elif fc == 'D':
            if modifier:
                res = bad()
            else:
                sub = nstrftime(b'%m/%d/%y', tm, ns, to_up, pad, -1)
                res = pad_text(sub, width, pad)
        elif fc == 'd':
            res = bad() if modifier == 'E' else do_number(2, tm.mday)
        elif fc == 'e':
            res = bad() if modifier == 'E' else do_spacepad(2, tm.mday)
        elif fc == 'F':
            if modifier:
                res = bad()
            else:
                p2 = pad
                if pad == 0 and width < 0:
                    p2 = '+'
                    subwidth = 4
                else:
                    subwidth = width - 6
                    if subwidth < 0:
                        subwidth = 0
                sub = nstrftime(b'%Y-%m-%d', tm, ns, to_up, p2, subwidth)
                res = pad_text(sub, width, p2)
        elif fc == 'H':
            res = bad() if modifier == 'E' else do_number(2, tm.hour)
        elif fc == 'I':
            res = bad() if modifier == 'E' else do_number(2, hour12)
        elif fc == 'k':
            res = bad() if modifier == 'E' else do_spacepad(2, tm.hour)
        elif fc == 'l':
            res = bad() if modifier == 'E' else do_spacepad(2, hour12)
        elif fc == 'j':
            res = bad() if modifier == 'E' else do_number(3, tm.yday + 1)
        elif fc == 'M':
            res = bad() if modifier == 'E' else do_number(2, tm.min)
        elif fc == 'm':
            res = bad() if modifier == 'E' else do_number(2, tm.mon + 1)
        elif fc == 'N':
            if modifier == 'E':
                res = bad()
            else:
                w = width
                if w <= 0:
                    w = 9
                nn = ns
                ndigs = 9
                while w < ndigs or (1 < ndigs and nn % 10 == 0):
                    ndigs -= 1
                    nn //= 10
                ds = (b'%d' % nn).rjust(ndigs, b'0')[-ndigs:] if ndigs else b''
                p2 = pad if pad else '0'
                extra = w - ndigs
                if p2 == '-' or extra <= 0:
                    res = ds
                else:
                    res = ds + (b'0' if p2 in ('0', '+') else b' ') * extra
        elif fc == 'n':
            res = pad_text(b'\n', width, pad)
        elif fc == 't':
            res = pad_text(b'\t', width, pad)
        elif fc in ('p', 'P'):
            if fc == 'P':
                to_low = True
            if change_case:
                to_up, to_low = False, True
            res = cpy(glibc_underlying('p', modifier, tm))
        elif fc == 'q':
            res = do_number(1, ((tm.mon * 11) >> 5) + 1)
        elif fc == 'R':
            sub = nstrftime(b'%H:%M', tm, ns, to_up, pad, -1)
            res = pad_text(sub, width, pad)
        elif fc == 'T':
            sub = nstrftime(b'%H:%M:%S', tm, ns, to_up, pad, -1)
            res = pad_text(sub, width, pad)
        elif fc == 'r':
            res = cpy(glibc_underlying('r', modifier, tm))
        elif fc == 'S':
            res = bad() if modifier == 'E' else do_number(2, tm.sec)
        elif fc == 's':
            t = tm.t
            res = num_out(b'%d' % abs(t), t < 0, False, pad, width, 1)
        elif fc == 'u':
            res = do_number(1, (tm.wday - 1 + 7) % 7 + 1)
        elif fc == 'U':
            res = bad() if modifier == 'E' else \
                do_number(2, (tm.yday - tm.wday + 7) // 7)
        elif fc in ('V', 'g', 'G'):
            if modifier == 'E':
                res = bad()
            else:
                year = tm.year
                year_adjust = 0
                days = iso_week_days(tm.yday, tm.wday)
                if days < 0:
                    year_adjust = -1
                    days = iso_week_days(tm.yday + (365 + is_leap(year - 1)),
                                         tm.wday)
                else:
                    d = iso_week_days(tm.yday - (365 + is_leap(year)),
                                      tm.wday)
                    if 0 <= d:
                        year_adjust = 1
                        days = d
                if fc == 'g':
                    yy = cmod(cmod(tm_year, 100) + year_adjust, 100)
                    if yy < 0:
                        yy = -yy if tm_year < -1900 - year_adjust \
                            else yy + 100
                    res = do_yearish(2, False, yy)
                elif fc == 'G':
                    neg = tm_year < -1900 - year_adjust
                    v = tm.year + year_adjust
                    res = do_yearish(4, neg, abs(v))
                else:
                    res = do_number(2, days // 7 + 1)
        elif fc == 'W':
            res = bad() if modifier == 'E' else \
                do_number(2, (tm.yday - (tm.wday - 1 + 7) % 7 + 7) // 7)
        elif fc == 'w':
            res = bad() if modifier == 'E' else do_number(1, tm.wday)
        elif fc == 'Y':
            if modifier == 'E':
                res = cpy(glibc_underlying('Y', modifier, tm))
            elif modifier == 'O':
                res = bad()
            else:
                res = do_yearish(4, tm_year < -1900, abs(tm.year))
        elif fc == 'y':
            if modifier == 'E':
                res = cpy(glibc_underlying('y', modifier, tm))
            else:
                yy = cmod(tm_year, 100)
                if yy < 0:
                    yy = -yy if tm_year < -1900 else yy + 100
                res = do_yearish(2, False, yy)
        elif fc == 'Z':
            if change_case:
                to_up, to_low = False, True
            res = cpy(tm.zone)
        elif fc in (':', 'z'):
            colons = 0
            ok = True
            if fc == ':':
                colons = 1
                while i + colons < n and fmt[i + colons] == 58:
                    colons += 1
                if not (i + colons < n and fmt[i + colons] == 122):
                    ok = False
                    res = bad()
                else:
                    i += colons
            if ok:
                if tm.isdst < 0:
                    res = b''
                else:
                    diff = tm.gmtoff
                    neg = diff < 0 or (diff == 0 and tm.zone[:1] == b'-')
                    a = abs(diff)
                    hd = a // 3600
                    md = a // 60 % 60
                    sd = a % 60
                    if colons == 3:
                        if sd != 0:
                            colons = 2
                        elif md != 0:
                            colons = 1
                    if colons == 0:
                        res = do_tz(5, 0, hd * 100 + md, neg)
                    elif colons == 1:
                        res = do_tz(6, 4, hd * 100 + md, neg)
                    elif colons == 2:
                        res = do_tz(9, 0o24, hd * 10000 + md * 100 + sd, neg)
                    elif colons == 3:
                        res = do_tz(3, 0, hd, neg)
                    else:
                        res = bad()
        else:
            res = bad()
        out += res
        i += 1
        width = -1
    return bytes(out)


# ---------------------------------------------------------------------------
# date(1)

RFC_EMAIL_FORMAT = b'%a, %d %b %Y %H:%M:%S %z'

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

All options that specify the date to display are mutually exclusive.
I.e.: --date, --file, --reference, --resolution.

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
        self.code = code


def err(msg):
    try:
        sys.stderr.write('date: %s\n' % msg)
        sys.stderr.flush()
    except Exception:
        pass


def usage_fail(msg=None):
    if msg:
        err(msg)
    try:
        sys.stderr.write("Try 'date --help' for more information.\n")
    except Exception:
        pass
    raise Exit(1)


LONG_OPTS = [
    # name, has_arg (0 no, 1 required, 2 optional), key
    ('date', 1, 'd'),
    ('debug', 0, 'debug'),
    ('file', 1, 'f'),
    ('iso-8601', 2, 'I'),
    ('reference', 1, 'r'),
    ('resolution', 0, 'resolution'),
    ('rfc-email', 0, 'R'),
    ('rfc-822', 0, 'R'),
    ('rfc-2822', 0, 'R'),
    ('rfc-3339', 1, 'rfc3339'),
    ('set', 1, 's'),
    ('uct', 0, 'u'),
    ('utc', 0, 'u'),
    ('universal', 0, 'u'),
    ('help', 0, 'help'),
    ('version', 0, 'version'),
]

SHORT_OPTS = {'d': 1, 'f': 1, 'I': 2, 'r': 1, 'R': 0, 's': 1, 'u': 0}

TIME_SPEC_STRING = [b'hours', b'minutes', b'date', b'seconds', b'ns']
TIME_SPEC = ['hours', 'minutes', 'date', 'seconds', 'ns']


def argmatch(arg, strings, values):
    matchind = -1
    ambiguous = False
    for idx, s in enumerate(strings):
        if s.startswith(arg):
            if len(s) == len(arg):
                return values[idx]
            if matchind == -1:
                matchind = idx
            elif values[matchind] != values[idx]:
                ambiguous = True
    if ambiguous or matchind == -1:
        return None
    return values[matchind]


def getopt_events(args):
    """Yield (key, optarg) in order; operands collected separately."""
    events = []
    operands = []
    i = 0
    n = len(args)
    while i < n:
        a = args[i]
        if a == b'--':
            operands.extend(args[i + 1:])
            break
        if a.startswith(b'--'):
            body = a[2:]
            if b'=' in body:
                name, val = body.split(b'=', 1)
                has_val = True
            else:
                name, val, has_val = body, None, False
            try:
                sname = name.decode('ascii')
            except UnicodeDecodeError:
                sname = None
            match = None
            if sname is not None:
                for o in LONG_OPTS:
                    if o[0] == sname:
                        match = o
                        break
                if match is None and sname != '':
                    cands = [o for o in LONG_OPTS if o[0].startswith(sname)]
                    if cands:
                        first = cands[0]
                        if all(c[1] == first[1] and c[2] == first[2]
                               for c in cands):
                            match = first
                        else:
                            events.append(('error', "option '--%s' is "
                                           "ambiguous" % sname))
                            return events, operands
            if match is None:
                events.append(('error', 'unrecognized option'))
                return events, operands
            if match[1] == 0:
                if has_val:
                    events.append(('error', "option '--%s' doesn't allow an "
                                   "argument" % match[0]))
                    return events, operands
                events.append((match[2], None))
            elif match[1] == 1:
                if not has_val:
                    if i + 1 < n:
                        i += 1
                        val = args[i]
                    else:
                        events.append(('error', "option '--%s' requires an "
                                       "argument" % match[0]))
                        return events, operands
                events.append((match[2], val))
            else:
                events.append((match[2], val if has_val else None))
            i += 1
            continue
        if a.startswith(b'-') and len(a) > 1:
            j = 1
            while j < len(a):
                ch = chr(a[j])
                if ch not in SHORT_OPTS:
                    events.append(('error', "invalid option -- '%s'" % ch))
                    return events, operands
                kind = SHORT_OPTS[ch]
                if kind == 0:
                    events.append((ch, None))
                    j += 1
                    continue
                rest = a[j + 1:]
                if kind == 2:
                    events.append((ch, rest if rest else None))
                    break
                if rest:
                    events.append((ch, rest))
                elif i + 1 < n:
                    i += 1
                    events.append((ch, args[i]))
                else:
                    events.append(('error', "option requires an argument "
                                   "-- '%s'" % ch))
                    return events, operands
                break
            i += 1
            continue
        operands.append(a)
        i += 1
    return events, operands


def write_out(b):
    sys.stdout.buffer.write(b)


def show_date(fmt, when, tz):
    sec, nsec = when
    tm = tz.localtime(sec)
    if tm is None:
        err('time %d is out of range' % sec)
        return False
    return _show(fmt, tm, sec, nsec)


class TMS(TM):
    __slots__ = ('t',)


def _show(fmt, tm, sec, nsec):
    t2 = TMS()
    for k in TM.__slots__:
        setattr(t2, k, getattr(tm, k))
    t2.t = sec
    write_out(nstrftime(fmt, t2, nsec) + b'\n')
    return True


def adjust_resolution(fmt):
    b = bytearray(fmt)
    i = 0
    n = len(b)
    while i < n:
        if b[i] == 37:
            if i + 2 < n + 0 and i + 1 < n and b[i + 1] == 45 and \
                    i + 2 < n and b[i + 2] == 78:
                b[i + 1] = ord('9')
                i += 2
            elif i + 1 < n and b[i + 1] == 37:
                i += 1
        i += 1
    return bytes(b)


def posixtime(s, tz, now_ns):
    dot = s.find(b'.')
    length = len(s)
    if dot >= 0:
        length = dot
        if len(s) - length != 3:
            return None
    if not (8 <= length <= 12 and length % 2 == 0):
        return None
    for c in s[:length]:
        if not c_isdigit(c):
            return None
    pairs = [10 * (s[2 * k] - 48) + s[2 * k + 1] - 48
             for k in range(length // 2)]
    mon = pairs[0] - 1
    mday = pairs[1]
    hour = pairs[2]
    minute = pairs[3]
    rest = pairs[4:]
    if len(rest) == 1:
        tm_year = rest[0] + (100 if rest[0] <= 68 else 0)
    elif len(rest) == 2:
        tm_year = rest[0] * 100 + rest[1] - 1900
    else:
        now = tz.localtime(now_ns // BILLION)
        tm_year = now.tm_year
    if dot < 0:
        sec = 0
    elif c_isdigit(s[dot + 1]) and c_isdigit(s[dot + 2]):
        sec = 10 * (s[dot + 1] - 48) + s[dot + 2] - 48
    else:
        return None
    tm0 = (tm_year, mon, mday, hour, minute, sec)
    r = tz.mktime(*tm0)
    if r is None or not same_fields(tm0, r[1]):
        return None
    return r[0], 0


def main(argv):
    args = [os.fsencode(a) for a in argv]
    events, operands = getopt_events(args)

    datestr = None
    batch_file = None
    reference = None
    get_resolution = False
    set_datestr = None
    set_date = False
    fmt = None
    tzstring = os.environ.get('TZ')

    for key, val in events:
        new_format = None
        if key == 'error':
            usage_fail(val)
        elif key == 'd':
            datestr = val
        elif key == 'debug':
            pass
        elif key == 'f':
            batch_file = val
        elif key == 'resolution':
            get_resolution = True
        elif key == 'rfc3339':
            r = argmatch(val, TIME_SPEC_STRING[2:], TIME_SPEC[2:])
            if r is None:
                usage_fail("invalid argument for '--rfc-3339'")
            new_format = {'date': b'%Y-%m-%d',
                          'seconds': b'%Y-%m-%d %H:%M:%S%:z',
                          'ns': b'%Y-%m-%d %H:%M:%S.%N%:z'}[r]
        elif key == 'I':
            if val is None:
                r = 'date'
            else:
                r = argmatch(val, TIME_SPEC_STRING, TIME_SPEC)
                if r is None:
                    usage_fail("invalid argument for '--iso-8601'")
            new_format = {'date': b'%Y-%m-%d',
                          'seconds': b'%Y-%m-%dT%H:%M:%S%:z',
                          'ns': b'%Y-%m-%dT%H:%M:%S,%N%:z',
                          'hours': b'%Y-%m-%dT%H%:z',
                          'minutes': b'%Y-%m-%dT%H:%M%:z'}[r]
        elif key == 'r':
            reference = val
        elif key == 'R':
            new_format = RFC_EMAIL_FORMAT
        elif key == 's':
            set_datestr = val
            set_date = True
        elif key == 'u':
            tzstring = 'UTC0'
            os.environ['TZ'] = 'UTC0'
        elif key == 'help':
            sys.stdout.write(HELP_TEXT)
            sys.stdout.flush()
            raise Exit(0)
        elif key == 'version':
            sys.stdout.write(VERSION_TEXT)
            sys.stdout.flush()
            raise Exit(0)
        if new_format is not None:
            if fmt is not None:
                err('multiple output formats specified')
                raise Exit(1)
            fmt = new_format

    option_specified_date = ((datestr is not None) + (batch_file is not None)
                             + (reference is not None) + get_resolution)
    if option_specified_date > 1:
        usage_fail('the options to specify dates for printing are mutually '
                   'exclusive')
    if set_date and option_specified_date:
        usage_fail('the options to print and set the time may not be used '
                   'together')

    posix_operand = None
    if operands:
        if len(operands) > 1:
            usage_fail('extra operand')
        op = operands[0]
        if op.startswith(b'+'):
            if fmt is not None:
                err('multiple output formats specified')
                raise Exit(1)
            fmt = op[1:]
        elif set_date or option_specified_date:
            usage_fail('the argument lacks a leading +')
        else:
            posix_operand = op

    if fmt is None:
        if get_resolution:
            fmt = b'%s.%N'
        else:
            fmt = b'%a %b %e %H:%M:%S %Z %Y'

    fmt = adjust_resolution(fmt)
    tz = make_tz(tzstring)
    now_ns = time.time_ns()

    if batch_file is not None:
        ok = True
        try:
            if batch_file == b'-':
                data = sys.stdin.buffer.read()
            else:
                with open(batch_file, 'rb') as fh:
                    data = fh.read()
        except OSError as e:
            err('%s: %s' % (os.fsdecode(batch_file), e.strerror))
            raise Exit(1)
        lines = data.split(b'\n')
        if lines and lines[-1] == b'':
            lines.pop()
            lines = [ln + b'\n' for ln in lines]
        else:
            lines = [ln + b'\n' for ln in lines[:-1]] + lines[-1:]
        for line in lines:
            when = parse_datetime(line, tz, now_ns)
            if when is None:
                err('invalid date')
                ok = False
            else:
                ok &= show_date(fmt, when, tz)
            sys.stdout.flush()
        raise Exit(0 if ok else 1)

    ok = True
    when = None
    if not option_specified_date and not set_date:
        if posix_operand is not None:
            set_date = True
            when = posixtime(posix_operand, tz, now_ns)
        else:
            when = divmod(now_ns, BILLION)
    else:
        if reference is not None:
            try:
                st = os.stat(reference)
            except OSError as e:
                err('%s: %s' % (os.fsdecode(reference), e.strerror))
                raise Exit(1)
            when = divmod(st.st_mtime_ns, BILLION)
        elif get_resolution:
            when = (0, 1)
        else:
            if set_datestr is not None:
                datestr = set_datestr
            when = parse_datetime(datestr, tz, now_ns)
    if when is None:
        err('invalid date')
        raise Exit(1)
    if set_date:
        err('cannot set date: Operation not permitted')
        ok = False
    ok &= show_date(fmt, when, tz)
    raise Exit(0 if ok else 1)


def run():
    try:
        main(sys.argv[1:])
        code = 0
    except Exit as e:
        code = e.code
    try:
        sys.stdout.flush()
    except Exception:
        code = 1
    return code


if __name__ == "__main__":
    sys.exit(run())
