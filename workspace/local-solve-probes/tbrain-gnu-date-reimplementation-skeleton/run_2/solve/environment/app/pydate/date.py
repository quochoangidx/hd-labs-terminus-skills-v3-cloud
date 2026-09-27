"""pydate: a GNU date 9.1 replacement in pure Python (display only).

Usage: python3 /app/pydate/date.py [OPTION]... [+FORMAT]

The output time zone is always UTC0 (as with TZ=UTC0), the locale is C.
The date-string parser is a faithful re-implementation of gnulib's
parse-datetime.y (an LALR(1) grammar, conflicts resolved like Bison), and
the formatter follows gnulib's nstrftime.c.
"""

import os
import sys
import time

INT_MIN = -(1 << 31)
INT_MAX = (1 << 31) - 1
IMAX = (1 << 63) - 1
IMIN = -(1 << 63)
BILLION = 1000000000


class Abort(Exception):
    pass


def in_int(v):
    return INT_MIN <= v <= INT_MAX


def in_imax(v):
    return IMIN <= v <= IMAX


def wrap_int(v):
    v &= 0xFFFFFFFF
    return v - (1 << 32) if v >= (1 << 31) else v


def cdiv(a, b):
    q = abs(a) // abs(b)
    return q if (a >= 0) == (b >= 0) else -q


def cmod(a, b):
    return a - b * cdiv(a, b)


# ---------------------------------------------------------------------------
# Calendar arithmetic (proleptic Gregorian, arbitrary range)

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
    return (y + (m <= 2), m, d)


class TM(object):
    __slots__ = ("year", "mon", "mday", "hour", "min", "sec", "wday",
                 "yday", "isdst", "gmtoff", "zone", "tsec")

    def __init__(self):
        self.year = 70      # tm_year (years since 1900)
        self.mon = 0
        self.mday = 1
        self.hour = 0
        self.min = 0
        self.sec = 0
        self.wday = -1
        self.yday = -1
        self.isdst = 0
        self.gmtoff = 0
        self.zone = b"UTC"
        self.tsec = 0


def breakdown(t, off, zone, isdst=0):
    """Like localtime for a fixed offset; None if the year overflows int."""
    lt = t + off
    days = lt // 86400
    secs = lt - days * 86400
    y, m, d = civil_from_days(days)
    if not in_int(y - 1900):
        return None
    tm = TM()
    tm.year = y - 1900
    tm.mon = m - 1
    tm.mday = d
    tm.hour = secs // 3600
    tm.min = secs // 60 % 60
    tm.sec = secs % 60
    tm.wday = (days + 4) % 7
    tm.yday = days - days_from_civil(y, 1, 1)
    tm.isdst = isdst
    tm.gmtoff = off
    tm.zone = zone
    return tm


def local_seconds(tm):
    y = tm.year + 1900 + tm.mon // 12
    m = tm.mon % 12
    days = days_from_civil(y, m + 1, 1) + tm.mday - 1
    return days * 86400 + tm.hour * 3600 + tm.min * 60 + tm.sec


# ---------------------------------------------------------------------------
# Time zones

class FixedTZ(object):
    def __init__(self, off, name):
        self.off = off
        self.name = name

    def localtime(self, t):
        return breakdown(t, self.off, self.name)

    def mktime(self, tm):
        """Normalize TM in place; return time_t or None on overflow."""
        t = local_seconds(tm) - self.off
        if not in_imax(t):
            return None
        r = self.localtime(t)
        if r is None:
            return None
        for k in TM.__slots__:
            setattr(tm, k, getattr(r, k))
        return t


class ZoneInfoTZ(object):
    def __init__(self, zi):
        self.zi = zi

    def _info(self, t):
        import datetime
        try:
            if -62135596800 <= t <= 253402300799 - 86400 * 2:
                dt = datetime.datetime.fromtimestamp(t, self.zi)
            else:
                raise OverflowError
            off = int(dt.utcoffset().total_seconds())
            name = (dt.tzname() or "UTC").encode("ascii", "replace")
            dst = dt.dst()
            isdst = 1 if dst and dst.total_seconds() else 0
            return off, name, isdst
        except (OverflowError, ValueError, OSError):
            return 0, b"UTC", 0

    def localtime(self, t):
        off, name, isdst = self._info(t)
        return breakdown(t, off, name, isdst)

    def mktime(self, tm):
        ls = local_seconds(tm)
        off = self._info(ls)[0]
        t = ls - off
        for _ in range(3):
            off2 = self._info(t)[0]
            if ls - off2 == t:
                break
            t = ls - off2
        if not in_imax(t):
            return None
        r = self.localtime(t)
        if r is None:
            return None
        for k in TM.__slots__:
            setattr(tm, k, getattr(r, k))
        return t


UTC = FixedTZ(0, b"UTC")


def parse_posix_tz(s):
    """Very small POSIX TZ parser: returns a tz object (std offset only)."""
    try:
        txt = s.decode("ascii")
    except UnicodeDecodeError:
        return UTC
    if txt.startswith(":"):
        txt = txt[1:]
    i = 0
    n = len(txt)
    if i < n and txt[i] == "<":
        j = txt.find(">", i)
        if j < 0:
            return UTC
        name = txt[i + 1:j]
        i = j + 1
    else:
        j = i
        while j < n and txt[j].isalpha():
            j += 1
        name = txt[i:j]
        i = j
    if len(name) >= 3 and i < n and (txt[i] in "+-" or txt[i].isdigit()):
        sign = 1
        if txt[i] in "+-":
            sign = -1 if txt[i] == "-" else 1
            i += 1
        parts = []
        cur = ""
        while i < n and (txt[i].isdigit() or txt[i] == ":"):
            if txt[i] == ":":
                parts.append(cur)
                cur = ""
            else:
                cur += txt[i]
            i += 1
        parts.append(cur)
        try:
            vals = [int(p) if p else 0 for p in parts[:3]]
        except ValueError:
            return UTC
        while len(vals) < 3:
            vals.append(0)
        off = -sign * (vals[0] * 3600 + vals[1] * 60 + vals[2])
        if i == n:
            return FixedTZ(off, name.encode("ascii"))
    # Try the tz database.
    try:
        import zoneinfo
        return ZoneInfoTZ(zoneinfo.ZoneInfo(txt))
    except Exception:
        pass
    if name and i == n:
        return UTC
    return UTC


# ---------------------------------------------------------------------------
# parse-datetime: tables

def HOUR(x):
    return x * 3600


MERam, MERpm, MER24 = 0, 1, 2

meridian_table = [
    (b"AM", "tMERIDIAN", MERam), (b"A.M.", "tMERIDIAN", MERam),
    (b"PM", "tMERIDIAN", MERpm), (b"P.M.", "tMERIDIAN", MERpm),
]

month_and_day_table = [
    (b"JANUARY", "tMONTH", 1), (b"FEBRUARY", "tMONTH", 2),
    (b"MARCH", "tMONTH", 3), (b"APRIL", "tMONTH", 4),
    (b"MAY", "tMONTH", 5), (b"JUNE", "tMONTH", 6),
    (b"JULY", "tMONTH", 7), (b"AUGUST", "tMONTH", 8),
    (b"SEPTEMBER", "tMONTH", 9), (b"SEPT", "tMONTH", 9),
    (b"OCTOBER", "tMONTH", 10), (b"NOVEMBER", "tMONTH", 11),
    (b"DECEMBER", "tMONTH", 12),
    (b"SUNDAY", "tDAY", 0), (b"MONDAY", "tDAY", 1),
    (b"TUESDAY", "tDAY", 2), (b"TUES", "tDAY", 2),
    (b"WEDNESDAY", "tDAY", 3), (b"WEDNES", "tDAY", 3),
    (b"THURSDAY", "tDAY", 4), (b"THUR", "tDAY", 4),
    (b"THURS", "tDAY", 4), (b"FRIDAY", "tDAY", 5),
    (b"SATURDAY", "tDAY", 6),
]

time_units_table = [
    (b"YEAR", "tYEAR_UNIT", 1), (b"MONTH", "tMONTH_UNIT", 1),
    (b"FORTNIGHT", "tDAY_UNIT", 14), (b"WEEK", "tDAY_UNIT", 7),
    (b"DAY", "tDAY_UNIT", 1), (b"HOUR", "tHOUR_UNIT", 1),
    (b"MINUTE", "tMINUTE_UNIT", 1), (b"MIN", "tMINUTE_UNIT", 1),
    (b"SECOND", "tSEC_UNIT", 1), (b"SEC", "tSEC_UNIT", 1),
]

relative_time_table = [
    (b"TOMORROW", "tDAY_SHIFT", 1), (b"YESTERDAY", "tDAY_SHIFT", -1),
    (b"TODAY", "tDAY_SHIFT", 0), (b"NOW", "tDAY_SHIFT", 0),
    (b"LAST", "tORDINAL", -1), (b"THIS", "tORDINAL", 0),
    (b"NEXT", "tORDINAL", 1), (b"FIRST", "tORDINAL", 1),
    (b"THIRD", "tORDINAL", 3), (b"FOURTH", "tORDINAL", 4),
    (b"FIFTH", "tORDINAL", 5), (b"SIXTH", "tORDINAL", 6),
    (b"SEVENTH", "tORDINAL", 7), (b"EIGHTH", "tORDINAL", 8),
    (b"NINTH", "tORDINAL", 9), (b"TENTH", "tORDINAL", 10),
    (b"ELEVENTH", "tORDINAL", 11), (b"TWELFTH", "tORDINAL", 12),
    (b"AGO", "tAGO", -1), (b"HENCE", "tAGO", 1),
]

universal_time_zone_table = [
    (b"GMT", "tZONE", 0), (b"UT", "tZONE", 0), (b"UTC", "tZONE", 0),
]

time_zone_table = [
    (b"WET", "tZONE", HOUR(0)), (b"WEST", "tDAYZONE", HOUR(0)),
    (b"BST", "tDAYZONE", HOUR(0)), (b"ART", "tZONE", -HOUR(3)),
    (b"BRT", "tZONE", -HOUR(3)), (b"BRST", "tDAYZONE", -HOUR(3)),
    (b"NST", "tZONE", -(HOUR(3) + 30 * 60)),
    (b"NDT", "tDAYZONE", -(HOUR(3) + 30 * 60)),
    (b"AST", "tZONE", -HOUR(4)), (b"ADT", "tDAYZONE", -HOUR(4)),
    (b"CLT", "tZONE", -HOUR(4)), (b"CLST", "tDAYZONE", -HOUR(4)),
    (b"EST", "tZONE", -HOUR(5)), (b"EDT", "tDAYZONE", -HOUR(5)),
    (b"CST", "tZONE", -HOUR(6)), (b"CDT", "tDAYZONE", -HOUR(6)),
    (b"MST", "tZONE", -HOUR(7)), (b"MDT", "tDAYZONE", -HOUR(7)),
    (b"PST", "tZONE", -HOUR(8)), (b"PDT", "tDAYZONE", -HOUR(8)),
    (b"AKST", "tZONE", -HOUR(9)), (b"AKDT", "tDAYZONE", -HOUR(9)),
    (b"HST", "tZONE", -HOUR(10)), (b"HAST", "tZONE", -HOUR(10)),
    (b"HADT", "tDAYZONE", -HOUR(10)), (b"SST", "tZONE", -HOUR(12)),
    (b"WAT", "tZONE", HOUR(1)), (b"CET", "tZONE", HOUR(1)),
    (b"CEST", "tDAYZONE", HOUR(1)), (b"MET", "tZONE", HOUR(1)),
    (b"MEZ", "tZONE", HOUR(1)), (b"MEST", "tDAYZONE", HOUR(1)),
    (b"MESZ", "tDAYZONE", HOUR(1)), (b"EET", "tZONE", HOUR(2)),
    (b"EEST", "tDAYZONE", HOUR(2)), (b"CAT", "tZONE", HOUR(2)),
    (b"SAST", "tZONE", HOUR(2)), (b"EAT", "tZONE", HOUR(3)),
    (b"MSK", "tZONE", HOUR(3)), (b"MSD", "tDAYZONE", HOUR(3)),
    (b"IST", "tZONE", HOUR(5) + 30 * 60), (b"SGT", "tZONE", HOUR(8)),
    (b"KST", "tZONE", HOUR(9)), (b"JST", "tZONE", HOUR(9)),
    (b"GST", "tZONE", HOUR(10)), (b"NZST", "tZONE", HOUR(12)),
    (b"NZDT", "tDAYZONE", HOUR(12)),
]

military_table = [
    (b"A", "tZONE", HOUR(1)), (b"B", "tZONE", HOUR(2)),
    (b"C", "tZONE", HOUR(3)), (b"D", "tZONE", HOUR(4)),
    (b"E", "tZONE", HOUR(5)), (b"F", "tZONE", HOUR(6)),
    (b"G", "tZONE", HOUR(7)), (b"H", "tZONE", HOUR(8)),
    (b"I", "tZONE", HOUR(9)), (b"K", "tZONE", HOUR(10)),
    (b"L", "tZONE", HOUR(11)), (b"M", "tZONE", HOUR(12)),
    (b"N", "tZONE", -HOUR(1)), (b"O", "tZONE", -HOUR(2)),
    (b"P", "tZONE", -HOUR(3)), (b"Q", "tZONE", -HOUR(4)),
    (b"R", "tZONE", -HOUR(5)), (b"S", "tZONE", -HOUR(6)),
    (b"T", "T", 0), (b"U", "tZONE", -HOUR(8)),
    (b"V", "tZONE", -HOUR(9)), (b"W", "tZONE", -HOUR(10)),
    (b"X", "tZONE", -HOUR(11)), (b"Y", "tZONE", -HOUR(12)),
    (b"Z", "tZONE", HOUR(0)),
]


def lookup_zone(pc, name):
    for tp in universal_time_zone_table:
        if tp[0] == name:
            return tp
    for tp in pc.local_time_zone_table:
        if tp[0] == name:
            return tp
    for tp in time_zone_table:
        if tp[0] == name:
            return tp
    return None


def lookup_word(pc, word):
    word = word.upper()
    for tp in meridian_table:
        if tp[0] == word:
            return tp
    wordlen = len(word)
    abbrev = wordlen == 3 or (wordlen == 4 and word[3:4] == b".")
    for tp in month_and_day_table:
        if abbrev:
            if tp[0][:3] == word[:3]:
                return tp
        elif tp[0] == word:
            return tp
    tp = lookup_zone(pc, word)
    if tp:
        return tp
    if word == b"DST":
        return (b"DST", "tDST", 0)
    for tp in time_units_table:
        if tp[0] == word:
            return tp
    if word[-1:] == b"S":
        w2 = word[:-1]
        for tp in time_units_table:
            if tp[0] == w2:
                return tp
    for tp in relative_time_table:
        if tp[0] == word:
            return tp
    if wordlen == 1:
        for tp in military_table:
            if tp[0] == word:
                return tp
    if b"." in word:
        tp = lookup_zone(pc, word.replace(b".", b""))
        if tp:
            return tp
    return None


# ---------------------------------------------------------------------------
# Lexer

SPACE = b" \t\n\v\f\r"


def isdigit(c):
    return 48 <= c <= 57


def isalpha(c):
    return 65 <= c <= 90 or 97 <= c <= 122


class TextInt(object):
    __slots__ = ("negative", "value", "digits")

    def __init__(self, negative, value, digits):
        self.negative = negative
        self.value = value
        self.digits = digits


def yylex(pc):
    s = pc.s
    n = len(s)
    while True:
        i = pc.pos
        while i < n and s[i] in SPACE:
            i += 1
        pc.pos = i
        if i >= n:
            return ("$end", None)
        c = s[i]
        if isdigit(c) or c == 45 or c == 43:
            p = i
            if c == 45 or c == 43:
                sign = -1 if c == 45 else 1
                p += 1
                while p < n and s[p] in SPACE:
                    p += 1
                pc.pos = p
                if not (p < n and isdigit(s[p])):
                    continue
            else:
                sign = 0
            start = p
            value = 0
            while p < n and isdigit(s[p]):
                value = value * 10 + (-(s[p] - 48) if sign < 0 else s[p] - 48)
                if not in_imax(value):
                    return ("?", None)
                p += 1
            if p < n and s[p] in b".," and p + 1 < n and isdigit(s[p + 1]):
                sec = value
                p += 1
                ns = s[p] - 48
                p += 1
                for _ in range(2, 10):
                    ns *= 10
                    if p < n and isdigit(s[p]):
                        ns += s[p] - 48
                        p += 1
                if sign < 0:
                    while p < n and isdigit(s[p]):
                        if s[p] != 48:
                            ns += 1
                            break
                        p += 1
                while p < n and isdigit(s[p]):
                    p += 1
                if sign < 0 and ns:
                    if sec == IMIN:
                        return ("?", None)
                    sec -= 1
                    ns = BILLION - ns
                pc.pos = p
                return ("tSDECIMAL_NUMBER" if sign else "tUDECIMAL_NUMBER",
                        (sec, ns))
            pc.pos = p
            return ("tSNUMBER" if sign else "tUNUMBER",
                    TextInt(sign < 0, value, p - start))
        if isalpha(c):
            p = i
            buf = bytearray()
            while True:
                if len(buf) < 19:
                    buf.append(s[p])
                p += 1
                if not (p < n and (isalpha(s[p]) or s[p] == 46)):
                    break
            pc.pos = p
            tp = lookup_word(pc, bytes(buf))
            if not tp:
                return ("?", None)
            return (tp[1], tp[2])
        if c != 40:  # '('
            pc.pos = i + 1
            ch = chr(c)
            if ch in "@:,/":
                return (ch, None)
            return ("?", None)
        count = 0
        p = i
        while True:
            if p >= n:
                pc.pos = p
                return ("$end", None)
            c = s[p]
            p += 1
            if c == 40:
                count += 1
            elif c == 41:
                count -= 1
            if count == 0:
                break
        pc.pos = p


# ---------------------------------------------------------------------------
# Grammar (mirrors parse-datetime.y) and semantic actions

REL0 = (0, 0, 0, 0, 0, 0, 0)  # year, month, day, hour, minutes, seconds, ns


def rel_make(**kw):
    r = [0] * 7
    names = ("year", "month", "day", "hour", "minutes", "seconds", "ns")
    for k, v in kw.items():
        r[names.index(k)] = v
    return tuple(r)


def apply_relative_time(pc, rel, factor):
    cur = pc.rel
    out = []
    for idx in range(7):
        v = cur[idx] - rel[idx] if factor < 0 else cur[idx] + rel[idx]
        ok = in_int(v) if idx == 6 else in_imax(v)
        if not ok:
            raise Abort()
        out.append(v)
    pc.rel = tuple(out)
    pc.rels_seen = True


def set_hhmmss(pc, hour, minutes, sec, nsec):
    pc.hour = hour
    pc.minutes = minutes
    pc.seconds = (sec, nsec)


def time_zone_hhmm(pc, s, mm):
    value = s.value
    if s.digits <= 2 and mm < 0:
        value *= 100
    if mm < 0:
        n_minutes = cdiv(value, 100) * 60 + cmod(value, 100)
        overflow = False
    else:
        n_minutes = value * 60
        overflow = not in_imax(n_minutes)
        n_minutes = n_minutes - mm if s.negative else n_minutes + mm
        overflow = overflow or not in_imax(n_minutes)
    if overflow or not (-24 * 60 <= n_minutes <= 24 * 60):
        return False
    pc.time_zone = n_minutes * 60
    return True


def digits_to_date_time(pc, ti):
    if (pc.dates_seen and not pc.year.digits and not pc.rels_seen
            and (pc.times_seen or 2 < ti.digits)):
        pc.year = ti
    else:
        if 4 < ti.digits:
            pc.dates_seen += 1
            pc.day = cmod(ti.value, 100)
            pc.month = cmod(cdiv(ti.value, 100), 100)
            pc.year = TextInt(False, cdiv(ti.value, 10000), ti.digits - 4)
        else:
            pc.times_seen += 1
            if ti.digits <= 2:
                pc.hour = ti.value
                pc.minutes = 0
            else:
                pc.hour = cdiv(ti.value, 100)
                pc.minutes = cmod(ti.value, 100)
            pc.seconds = (0, 0)
            pc.meridian = MER24


def neg(v):
    r = -v
    if not in_imax(r):
        raise Abort()
    return r


def a_first(pc, v):
    return v[0] if v else None


def a_timespec(pc, v):
    pc.seconds = v[1]
    pc.timespec_seen = True


def a_inc(attr, attr2=None):
    def f(pc, v):
        setattr(pc, attr, getattr(pc, attr) + 1)
        if attr2:
            setattr(pc, attr2, getattr(pc, attr2) + 1)
    return f


def a_none(pc, v):
    return None


def a_time_mer1(pc, v):
    set_hhmmss(pc, v[0].value, 0, 0, 0)
    pc.meridian = v[1]


def a_time_mer2(pc, v):
    set_hhmmss(pc, v[0].value, v[2].value, 0, 0)
    pc.meridian = v[3]


def a_time_mer3(pc, v):
    set_hhmmss(pc, v[0].value, v[2].value, v[4][0], v[4][1])
    pc.meridian = v[5]


def a_iso_time1(pc, v):
    set_hhmmss(pc, v[0].value, 0, 0, 0)
    pc.meridian = MER24


def a_iso_time2(pc, v):
    set_hhmmss(pc, v[0].value, v[2].value, 0, 0)
    pc.meridian = MER24


def a_iso_time3(pc, v):
    set_hhmmss(pc, v[0].value, v[2].value, v[4][0], v[4][1])
    pc.meridian = MER24


def a_zone_offset(pc, v):
    pc.zones_seen += 1
    if not time_zone_hhmm(pc, v[0], v[1]):
        raise Abort()


def a_ocm_empty(pc, v):
    return -1


def a_ocm(pc, v):
    return v[1].value


def a_local_zone1(pc, v):
    pc.local_isdst = v[0]


def a_local_zone2(pc, v):
    pc.local_isdst = 1
    pc.dsts_seen += 1


def a_zone1(pc, v):
    pc.time_zone = v[0]


def a_zoneT(pc, v):
    pc.time_zone = -HOUR(7)


def a_zone_rel(pc, v):
    pc.time_zone = v[0]
    apply_relative_time(pc, v[1], 1)


def a_zoneT_rel(pc, v):
    pc.time_zone = -HOUR(7)
    apply_relative_time(pc, v[1], 1)


def a_zone_hhmm(pc, v):
    if not time_zone_hhmm(pc, v[1], v[2]):
        raise Abort()
    tz = pc.time_zone + v[0]
    if not in_int(tz):
        raise Abort()
    pc.time_zone = tz


def a_dayzone(pc, v):
    pc.time_zone = v[0] + 3600


def a_day1(pc, v):
    pc.day_ordinal = 0
    pc.day_number = v[0]


def a_day_ord(pc, v):
    pc.day_ordinal = v[0]
    pc.day_number = v[1]


def a_day_num(pc, v):
    pc.day_ordinal = v[0].value
    pc.day_number = v[1]


def a_date_md(pc, v):
    pc.month = v[0].value
    pc.day = v[2].value


def a_date_mdy(pc, v):
    if 4 <= v[0].digits:
        pc.year = v[0]
        pc.month = v[2].value
        pc.day = v[4].value
    else:
        pc.month = v[0].value
        pc.day = v[2].value
        pc.year = v[4]


def a_date_dmy_s(pc, v):
    pc.day = v[0].value
    pc.month = v[1]
    pc.year = TextInt(False, neg(v[2].value), v[2].digits)


def a_date_mdy_s(pc, v):
    pc.month = v[0]
    pc.day = neg(v[1].value)
    pc.year = TextInt(False, neg(v[2].value), v[2].digits)


def a_date_mon_day(pc, v):
    pc.month = v[0]
    pc.day = v[1].value


def a_date_mon_day_year(pc, v):
    pc.month = v[0]
    pc.day = v[1].value
    pc.year = v[3]


def a_date_day_mon(pc, v):
    pc.day = v[0].value
    pc.month = v[1]


def a_date_day_mon_year(pc, v):
    pc.day = v[0].value
    pc.month = v[1]
    pc.year = v[2]


def a_iso_date(pc, v):
    pc.year = v[0]
    pc.month = neg(v[1].value)
    pc.day = neg(v[2].value)


def a_rel_ago(pc, v):
    apply_relative_time(pc, v[0], v[1])


def a_rel(pc, v):
    apply_relative_time(pc, v[0], 1)


def ru(field, src):
    """Build a relunit action.  src: 'ord', 'num', 'one', 'dec', 'unit'."""
    def f(pc, v):
        if src == "ord":
            val = v[0]
        elif src == "num":
            val = v[0].value
        elif src == "one":
            val = 1
        elif src == "unit":
            val = v[0]
        if field == "day" and src in ("ord", "num"):
            val = val * v[1]
            if not in_imax(val):
                raise Abort()
        if src == "dec":
            return rel_make(seconds=v[0][0], ns=v[0][1])
        return rel_make(**{field: val})
    return f


def a_dayshift(pc, v):
    return rel_make(day=v[0])


def a_secs_num(pc, v):
    return (v[0].value, 0)


def a_number(pc, v):
    digits_to_date_time(pc, v[0])


def a_hybrid(pc, v):
    digits_to_date_time(pc, v[0])
    apply_relative_time(pc, v[1], 1)


U, S = "tUNUMBER", "tSNUMBER"

RULES = [
    ("$accept", ["spec"], a_first),
    ("spec", ["timespec"], a_first),
    ("spec", ["items"], a_first),
    ("timespec", ["@", "seconds"], a_timespec),
    ("items", [], a_none),
    ("items", ["items", "item"], a_none),
    ("item", ["datetime"], a_inc("times_seen", "dates_seen")),
    ("item", ["time"], a_inc("times_seen")),
    ("item", ["local_zone"], a_inc("local_zones_seen")),
    ("item", ["zone"], a_inc("zones_seen")),
    ("item", ["date"], a_inc("dates_seen")),
    ("item", ["day"], a_inc("days_seen")),
    ("item", ["rel"], a_none),
    ("item", ["number"], a_none),
    ("item", ["hybrid"], a_none),
    ("datetime", ["iso_8601_datetime"], a_none),
    ("iso_8601_datetime", ["iso_8601_date", "T", "iso_8601_time"], a_none),
    ("time", [U, "tMERIDIAN"], a_time_mer1),
    ("time", [U, ":", U, "tMERIDIAN"], a_time_mer2),
    ("time", [U, ":", U, ":", "unsigned_seconds", "tMERIDIAN"], a_time_mer3),
    ("time", ["iso_8601_time"], a_none),
    ("iso_8601_time", [U, "zone_offset"], a_iso_time1),
    ("iso_8601_time", [U, ":", U, "o_zone_offset"], a_iso_time2),
    ("iso_8601_time", [U, ":", U, ":", "unsigned_seconds", "o_zone_offset"],
     a_iso_time3),
    ("o_zone_offset", [], a_none),
    ("o_zone_offset", ["zone_offset"], a_none),
    ("zone_offset", [S, "o_colon_minutes"], a_zone_offset),
    ("local_zone", ["tLOCAL_ZONE"], a_local_zone1),
    ("local_zone", ["tLOCAL_ZONE", "tDST"], a_local_zone2),
    ("zone", ["tZONE"], a_zone1),
    ("zone", ["T"], a_zoneT),
    ("zone", ["tZONE", "relunit_snumber"], a_zone_rel),
    ("zone", ["T", "relunit_snumber"], a_zoneT_rel),
    ("zone", ["tZONE", S, "o_colon_minutes"], a_zone_hhmm),
    ("zone", ["tDAYZONE"], a_dayzone),
    ("zone", ["tZONE", "tDST"], a_dayzone),
    ("day", ["tDAY"], a_day1),
    ("day", ["tDAY", ","], a_day1),
    ("day", ["tORDINAL", "tDAY"], a_day_ord),
    ("day", [U, "tDAY"], a_day_num),
    ("date", [U, "/", U], a_date_md),
    ("date", [U, "/", U, "/", U], a_date_mdy),
    ("date", [U, "tMONTH", S], a_date_dmy_s),
    ("date", ["tMONTH", S, S], a_date_mdy_s),
    ("date", ["tMONTH", U], a_date_mon_day),
    ("date", ["tMONTH", U, ",", U], a_date_mon_day_year),
    ("date", [U, "tMONTH"], a_date_day_mon),
    ("date", [U, "tMONTH", U], a_date_day_mon_year),
    ("date", ["iso_8601_date"], a_none),
    ("iso_8601_date", [U, S, S], a_iso_date),
    ("rel", ["relunit", "tAGO"], a_rel_ago),
    ("rel", ["relunit"], a_rel),
    ("rel", ["dayshift"], a_rel),
    ("relunit", ["tORDINAL", "tYEAR_UNIT"], ru("year", "ord")),
    ("relunit", [U, "tYEAR_UNIT"], ru("year", "num")),
    ("relunit", ["tYEAR_UNIT"], ru("year", "one")),
    ("relunit", ["tORDINAL", "tMONTH_UNIT"], ru("month", "ord")),
    ("relunit", [U, "tMONTH_UNIT"], ru("month", "num")),
    ("relunit", ["tMONTH_UNIT"], ru("month", "one")),
    ("relunit", ["tORDINAL", "tDAY_UNIT"], ru("day", "ord")),
    ("relunit", [U, "tDAY_UNIT"], ru("day", "num")),
    ("relunit", ["tDAY_UNIT"], ru("day", "unit")),
    ("relunit", ["tORDINAL", "tHOUR_UNIT"], ru("hour", "ord")),
    ("relunit", [U, "tHOUR_UNIT"], ru("hour", "num")),
    ("relunit", ["tHOUR_UNIT"], ru("hour", "one")),
    ("relunit", ["tORDINAL", "tMINUTE_UNIT"], ru("minutes", "ord")),
    ("relunit", [U, "tMINUTE_UNIT"], ru("minutes", "num")),
    ("relunit", ["tMINUTE_UNIT"], ru("minutes", "one")),
    ("relunit", ["tORDINAL", "tSEC_UNIT"], ru("seconds", "ord")),
    ("relunit", [U, "tSEC_UNIT"], ru("seconds", "num")),
    ("relunit", ["tSDECIMAL_NUMBER", "tSEC_UNIT"], ru("seconds", "dec")),
    ("relunit", ["tUDECIMAL_NUMBER", "tSEC_UNIT"], ru("seconds", "dec")),
    ("relunit", ["tSEC_UNIT"], ru("seconds", "one")),
    ("relunit", ["relunit_snumber"], a_first),
    ("relunit_snumber", [S, "tYEAR_UNIT"], ru("year", "num")),
    ("relunit_snumber", [S, "tMONTH_UNIT"], ru("month", "num")),
    ("relunit_snumber", [S, "tDAY_UNIT"], ru("day", "num")),
    ("relunit_snumber", [S, "tHOUR_UNIT"], ru("hour", "num")),
    ("relunit_snumber", [S, "tMINUTE_UNIT"], ru("minutes", "num")),
    ("relunit_snumber", [S, "tSEC_UNIT"], ru("seconds", "num")),
    ("dayshift", ["tDAY_SHIFT"], a_dayshift),
    ("seconds", ["signed_seconds"], a_first),
    ("seconds", ["unsigned_seconds"], a_first),
    ("signed_seconds", ["tSDECIMAL_NUMBER"], a_first),
    ("signed_seconds", [S], a_secs_num),
    ("unsigned_seconds", ["tUDECIMAL_NUMBER"], a_first),
    ("unsigned_seconds", [U], a_secs_num),
    ("number", [U], a_number),
    ("hybrid", [U, "relunit_snumber"], a_hybrid),
    ("o_colon_minutes", [], a_ocm_empty),
    ("o_colon_minutes", [":", U], a_ocm),
]


def build_lalr(rules):
    """LALR(1) tables; S/R conflicts -> shift, R/R -> earliest rule
    (Bison's default resolution)."""
    nonterms = set(r[0] for r in rules)
    by_lhs = {}
    for idx, r in enumerate(rules):
        by_lhs.setdefault(r[0], []).append(idx)
    rhs = [tuple(r[1]) for r in rules]
    lhs = [r[0] for r in rules]

    nullable = set()
    changed = True
    while changed:
        changed = False
        for i in range(len(rules)):
            if lhs[i] not in nullable and all(x in nullable for x in rhs[i]):
                nullable.add(lhs[i])
                changed = True
    first = {nt: set() for nt in nonterms}
    changed = True
    while changed:
        changed = False
        for i in range(len(rules)):
            f = first[lhs[i]]
            before = len(f)
            for x in rhs[i]:
                if x in nonterms:
                    f |= first[x]
                    if x not in nullable:
                        break
                else:
                    f.add(x)
                    break
            if len(f) != before:
                changed = True

    def first_seq(seq, la):
        out = set()
        for x in seq:
            if x in nonterms:
                out |= first[x]
                if x not in nullable:
                    return out
            else:
                out.add(x)
                return out
        out.add(la)
        return out

    def closure0(items):
        res = set(items)
        stack = list(items)
        while stack:
            r, d = stack.pop()
            if d < len(rhs[r]):
                x = rhs[r][d]
                if x in nonterms:
                    for r2 in by_lhs[x]:
                        it = (r2, 0)
                        if it not in res:
                            res.add(it)
                            stack.append(it)
        return res

    def closure1(items):
        # items: dict (r,d) -> set(lookaheads)
        res = {k: set(v) for k, v in items.items()}
        stack = [(k, la) for k, v in items.items() for la in v]
        while stack:
            (r, d), la = stack.pop()
            if d < len(rhs[r]):
                x = rhs[r][d]
                if x in nonterms:
                    las = first_seq(rhs[r][d + 1:], la)
                    for r2 in by_lhs[x]:
                        it = (r2, 0)
                        s = res.setdefault(it, set())
                        for a in las:
                            if a not in s:
                                s.add(a)
                                stack.append((it, a))
        return res

    kernels = [frozenset([(0, 0)])]
    index = {kernels[0]: 0}
    gotos = []
    i = 0
    while i < len(kernels):
        cl = closure0(kernels[i])
        trans = {}
        for r, d in cl:
            if d < len(rhs[r]):
                trans.setdefault(rhs[r][d], set()).add((r, d + 1))
        g = {}
        for x in sorted(trans):
            k = frozenset(trans[x])
            if k not in index:
                index[k] = len(kernels)
                kernels.append(k)
            g[x] = index[k]
        gotos.append(g)
        i += 1

    la = [{it: set() for it in k} for k in kernels]
    la[0][(0, 0)].add("$end")
    prop = {}
    for si, k in enumerate(kernels):
        for it in k:
            cl = closure1({it: {"#"}})
            for (r, d), las in cl.items():
                if d < len(rhs[r]):
                    x = rhs[r][d]
                    tgt = gotos[si][x]
                    nit = (r, d + 1)
                    for a in las:
                        if a == "#":
                            prop.setdefault((si, it), []).append((tgt, nit))
                        else:
                            la[tgt][nit].add(a)
    changed = True
    while changed:
        changed = False
        for (si, it), targets in prop.items():
            src = la[si][it]
            for tgt, nit in targets:
                dst = la[tgt][nit]
                if not src <= dst:
                    dst |= src
                    changed = True

    action = []
    goto_tab = []
    for si, k in enumerate(kernels):
        cl = closure1({it: la[si][it] for it in k})
        act = {}
        for x, tgt in gotos[si].items():
            if x not in nonterms:
                act[x] = ("s", tgt)
        for (r, d), las in cl.items():
            if d == len(rhs[r]):
                for a in las:
                    cur = act.get(a)
                    if cur is None:
                        act[a] = ("r", r)
                    else:
                        CONFLICTS.append((si, a, cur, r))
                        if cur[0] == "r" and r < cur[1]:
                            act[a] = ("r", r)
        action.append(act)
        goto_tab.append({x: t for x, t in gotos[si].items() if x in nonterms})
    return action, goto_tab


_TABLES = None
CONFLICTS = []


def tables():
    global _TABLES
    if _TABLES is None:
        _TABLES = build_lalr(RULES)
    return _TABLES


def yyparse(pc):
    action, goto_tab = tables()
    states = [0]
    values = []
    tok = None
    try:
        while True:
            if tok is None:
                tok = yylex(pc)
            act = action[states[-1]].get(tok[0])
            if act is None:
                return False
            if act[0] == "s":
                states.append(act[1])
                values.append(tok[1])
                tok = None
            else:
                r = act[1]
                l, rhs, fn = RULES[r]
                n = len(rhs)
                args = values[len(values) - n:] if n else []
                if r == 0:
                    return True
                val = fn(pc, args)
                if n:
                    del states[-n:]
                    del values[-n:]
                states.append(goto_tab[states[-1]][l])
                values.append(val)
    except Abort:
        return False


# ---------------------------------------------------------------------------
# parse_datetime

class PC(object):
    pass


def to_tm_year(ty):
    year = ty.value
    if 0 <= year and ty.digits == 2:
        year += 2000 if year < 69 else 1900
    r = -1900 - year if year < 0 else year - 1900
    if not in_int(r):
        return None
    return r


def to_hour(hours, meridian):
    if meridian == MER24:
        return hours if 0 <= hours < 24 else -1
    if meridian == MERam:
        return hours if 0 < hours < 12 else (0 if hours == 12 else -1)
    return hours + 12 if 0 < hours < 12 else (12 if hours == 12 else -1)


def mktime_ok(tm0, tm1, ok):
    if not ok:
        return False
    return (tm0.sec == tm1.sec and tm0.min == tm1.min
            and tm0.hour == tm1.hour and tm0.mday == tm1.mday
            and tm0.mon == tm1.mon and tm0.year == tm1.year)


def copy_tm(tm):
    r = TM()
    for k in TM.__slots__:
        setattr(r, k, getattr(tm, k))
    return r


def parse_datetime(s, tz, now_ns):
    """Return (sec, nsec) or None."""
    nul = s.find(b"\0")
    if nul >= 0:
        s = s[:nul]
    now_sec = now_ns // BILLION
    start_ns = now_ns % BILLION
    p = 0
    while p < len(s) and s[p] in SPACE:
        p += 1
    s = s[p:]
    if s.startswith(b'TZ="'):
        base = 4
        i = base
        while i < len(s):
            c = s[i]
            if c == 92:  # backslash
                i += 1
                if not (i < len(s) and s[i] in b'\\"'):
                    break
            elif c == 34:
                out = bytearray()
                j = base
                while s[j] != 34:
                    if s[j] == 92:
                        j += 1
                    out.append(s[j])
                    j += 1
                tz = parse_posix_tz(bytes(out))
                s = s[i + 1:]
                break
            i += 1
    if s == b"":
        s = b"0"

    tmp = tz.localtime(now_sec)
    if tmp is None:
        return None
    pc = PC()
    pc.s = s
    pc.pos = 0
    pc.year = TextInt(False, tmp.year + 1900, 0)
    pc.month = tmp.mon + 1
    pc.day = tmp.mday
    pc.hour = tmp.hour
    pc.minutes = tmp.min
    pc.seconds = (tmp.sec, start_ns)
    pc.meridian = MER24
    pc.rel = REL0
    pc.timespec_seen = False
    pc.rels_seen = False
    pc.dates_seen = 0
    pc.days_seen = 0
    pc.times_seen = 0
    pc.local_zones_seen = 0
    pc.dsts_seen = 0
    pc.zones_seen = 0
    pc.local_isdst = 0
    pc.time_zone = 0
    pc.day_ordinal = 0
    pc.day_number = 0
    pc.local_time_zone_table = []
    if tmp.zone and not (tmp.zone.upper() in (b"GMT", b"UT", b"UTC")):
        pc.local_time_zone_table.append((tmp.zone.upper(), "tLOCAL_ZONE",
                                         tmp.isdst))

    if not yyparse(pc):
        return None

    if pc.timespec_seen:
        return pc.seconds

    if 1 < (pc.times_seen | pc.dates_seen | pc.days_seen | pc.dsts_seen
            | (pc.local_zones_seen + pc.zones_seen)):
        return None

    tm = TM()
    ty = to_tm_year(pc.year)
    if ty is None:
        return None
    tm.year = ty
    tm.mon = pc.month - 1
    tm.mday = pc.day
    if not (in_int(tm.mon) and in_int(tm.mday)):
        return None
    if pc.times_seen or (pc.rels_seen and not pc.dates_seen
                         and not pc.days_seen):
        h = to_hour(pc.hour, pc.meridian)
        if h < 0:
            return None
        tm.hour = h
        tm.min = wrap_int(pc.minutes)
        tm.sec = wrap_int(pc.seconds[0])
        sec_ns = pc.seconds[1]
    else:
        tm.hour = tm.min = tm.sec = 0
        sec_ns = 0

    tm0 = copy_tm(tm)
    tm.wday = -1
    start = tz.mktime(tm)
    if not mktime_ok(tm0, tm, start is not None):
        return None

    if pc.days_seen and not pc.dates_seen:
        tm.yday = -1
        day_ordinal = pc.day_ordinal - (
            1 if (0 < pc.day_ordinal and tm.wday != pc.day_number) else 0)
        dayincr = day_ordinal * 7
        ok = in_imax(dayincr)
        if ok:
            dayincr = (pc.day_number - tm.wday + 7) % 7 + dayincr
            ok = in_imax(dayincr)
        if ok:
            md = dayincr + tm.mday
            ok = in_int(md)
            if ok:
                tm.mday = md
                tm.isdst = -1
                start = tz.mktime(tm)
                if start is None:
                    tm.yday = -1
        if tm.yday < 0:
            return None

    rel = pc.rel
    if rel[0] or rel[1] or rel[2]:
        year = tm.year + rel[0]
        month = tm.mon + rel[1]
        day = tm.mday + rel[2]
        if not (in_int(year) and in_int(month) and in_int(day)):
            return None
        tm.year, tm.mon, tm.mday = year, month, day
        tm.hour, tm.min, tm.sec = tm0.hour, tm0.min, tm0.sec
        start = tz.mktime(tm)
        if start is None or start == -1:
            return None

    if pc.zones_seen:
        delta = pc.time_zone - tm.gmtoff
        t1 = start - delta
        if not (in_imax(delta) and in_imax(t1)):
            return None
        start = t1

    orig_ns = sec_ns
    sum_ns = orig_ns + rel[6]
    normalized_ns = sum_ns % BILLION
    d4 = (sum_ns - normalized_ns) // BILLION
    d1 = rel[3] * 3600
    if not in_imax(d1):
        return None
    t1 = start + d1
    if not in_imax(t1):
        return None
    d2 = rel[4] * 60
    if not in_imax(d2):
        return None
    t2 = t1 + d2
    if not in_imax(t2):
        return None
    t3 = t2 + rel[5]
    if not in_imax(t3):
        return None
    t4 = t3 + d4
    if not in_imax(t4):
        return None
    return (t4, normalized_ns)


# ---------------------------------------------------------------------------
# Formatting (gnulib nstrftime + glibc C-locale strftime underneath)

WDAY_ABBR = [b"Sun", b"Mon", b"Tue", b"Wed", b"Thu", b"Fri", b"Sat"]
WDAY_FULL = [b"Sunday", b"Monday", b"Tuesday", b"Wednesday", b"Thursday",
             b"Friday", b"Saturday"]
MON_ABBR = [b"Jan", b"Feb", b"Mar", b"Apr", b"May", b"Jun", b"Jul", b"Aug",
            b"Sep", b"Oct", b"Nov", b"Dec"]
MON_FULL = [b"January", b"February", b"March", b"April", b"May", b"June",
            b"July", b"August", b"September", b"October", b"November",
            b"December"]


def _g_num(v, digits, pad=b"0"):
    neg_ = v < 0
    s = str(-v if neg_ else v).encode()
    if neg_:
        s = b"-" + s
    if len(s) < digits:
        s = pad * (digits - len(s)) + s
    return s


def glibc_strftime(fmt, tm):
    """Minimal glibc strftime (C locale, no flags) used for the
    conversions gnulib delegates to the underlying strftime."""
    out = bytearray()
    i = 0
    n = len(fmt)
    hour12 = tm.hour % 12 or 12
    year = tm.year + 1900
    while i < n:
        c = fmt[i:i + 1]
        if c != b"%":
            out += c
            i += 1
            continue
        i += 1
        while i < n and fmt[i:i + 1] in (b"E", b"O"):
            i += 1
        c = fmt[i:i + 1]
        i += 1
        if c == b"a":
            out += WDAY_ABBR[tm.wday]
        elif c == b"A":
            out += WDAY_FULL[tm.wday]
        elif c in (b"b", b"h"):
            out += MON_ABBR[tm.mon]
        elif c == b"B":
            out += MON_FULL[tm.mon]
        elif c == b"c":
            out += glibc_strftime(b"%a %b %e %H:%M:%S %Y", tm)
        elif c == b"x":
            out += glibc_strftime(b"%m/%d/%y", tm)
        elif c == b"X":
            out += glibc_strftime(b"%H:%M:%S", tm)
        elif c == b"r":
            out += glibc_strftime(b"%I:%M:%S %p", tm)
        elif c == b"p":
            out += b"PM" if tm.hour >= 12 else b"AM"
        elif c == b"e":
            out += _g_num(tm.mday, 2, b" ")
        elif c == b"d":
            out += _g_num(tm.mday, 2)
        elif c == b"m":
            out += _g_num(tm.mon + 1, 2)
        elif c == b"H":
            out += _g_num(tm.hour, 2)
        elif c == b"I":
            out += _g_num(hour12, 2)
        elif c == b"M":
            out += _g_num(tm.min, 2)
        elif c == b"S":
            out += _g_num(tm.sec, 2)
        elif c == b"Y":
            out += _g_num(year, 1)
        elif c == b"C":
            out += _g_num(cdiv(year, 100) - (1 if cmod(year, 100) < 0 else 0),
                          1)
        elif c == b"y":
            out += _g_num((cmod(tm.year, 100) + 100) % 100, 2)
        else:
            out += b"%" + c
    return bytes(out)


def iso_week_days(yday, wday):
    big_enough_multiple_of_7 = (366 // 7 + 2) * 7
    return (yday - (yday - wday + 4 + big_enough_multiple_of_7) % 7 + 4 - 1)


def isleap(y):
    return y % 4 == 0 and (y % 100 != 0 or y % 400 == 0)


def fmt_internal(fmt, tm, ns, upcase, yr_spec, width_init):
    out = bytearray()
    n = len(fmt)
    hour12 = tm.hour
    if hour12 > 12:
        hour12 -= 12
    elif hour12 == 0:
        hour12 = 12
    zone = tm.zone or b""
    f = 0
    width = width_init
    while f < n:
        pad = 0
        to_lowcase = False
        to_uppcase = upcase
        change_case = False

        def width_add(w, data, padc):
            wd = 0 if padc == "-" or w < 0 else w
            if len(data) < wd:
                out.extend((b"0" if padc in ("0", "+") else b" ")
                           * (wd - len(data)))
            out.extend(data)

        def cpy(data):
            if to_lowcase:
                data = data.lower()
            elif to_uppcase:
                data = data.upper()
            width_add(width, data, pad)

        if fmt[f] != 37:
            width_add(width, fmt[f:f + 1], pad)
            f += 1
            width = -1
            continue

        start = f
        while True:
            f += 1
            ch = chr(fmt[f]) if f < n else "\0"
            if ch in "_-+0":
                pad = ch
                continue
            if ch == "^":
                to_uppcase = True
                continue
            if ch == "#":
                change_case = True
                continue
            break
        if f < n and isdigit(fmt[f]):
            width = 0
            while f < n and isdigit(fmt[f]):
                width = width * 10 + fmt[f] - 48
                if width > INT_MAX:
                    width = INT_MAX
                f += 1
        modifier = 0
        if f < n and fmt[f] in (69, 79):
            modifier = chr(fmt[f])
            f += 1
        fc = chr(fmt[f]) if f < n else "\0"

        # Numeric output state.
        num = None  # dict describing the numeric output
        kind = None  # 'bad', 'underlying', 'text', 'sub', None

        def bad():
            nonlocal f
            flen = 1
            while fmt[f + 1 - flen] != 37:
                flen += 1
            cpy(fmt[f + 1 - flen:f + 1])

        if fc == "\0":
            f -= 1
            bad()
        elif fc == "%":
            if modifier:
                bad()
            else:
                width_add(width, b"%", pad)
        elif fc in "aA":
            if modifier:
                bad()
            else:
                if change_case:
                    to_uppcase, to_lowcase = True, False
                cpy((WDAY_ABBR if fc == "a" else WDAY_FULL)[tm.wday])
        elif fc in "bh":
            if change_case:
                to_uppcase, to_lowcase = True, False
            if modifier == "E":
                bad()
            else:
                cpy(MON_ABBR[tm.mon])
        elif fc == "B":
            if modifier == "E":
                bad()
            else:
                if change_case:
                    to_uppcase, to_lowcase = True, False
                cpy(MON_FULL[tm.mon])
        elif fc in "cxX":
            if modifier == "O":
                bad()
            else:
                cpy(glibc_strftime(b"%" + (modifier.encode() if modifier
                                           else b"") + fc.encode(), tm))
        elif fc == "r":
            cpy(glibc_strftime(b"%r", tm))
        elif fc in "pP":
            if fc == "P":
                to_lowcase = True
            if change_case:
                to_uppcase, to_lowcase = False, True
            cpy(glibc_strftime(b"%p", tm))
        elif fc == "C":
            if modifier == "E":
                cpy(glibc_strftime(b"%EC", tm))
            else:
                negative_year = tm.year < -1900
                zero_thru_1899 = (not negative_year) and tm.year < 0
                century = cdiv(tm.year - 99 * zero_thru_1899, 100) + 19
                num = ("yearish", 2, negative_year,
                       -century if negative_year else century)
        elif fc == "y":
            if modifier == "E":
                cpy(glibc_strftime(b"%Ey", tm))
            else:
                yy = cmod(tm.year, 100)
                if yy < 0:
                    yy = -yy if tm.year < -1900 else yy + 100
                num = ("yearish", 2, False, yy)
        elif fc == "Y":
            if modifier == "E":
                cpy(glibc_strftime(b"%EY", tm))
            elif modifier == "O":
                bad()
            else:
                y = tm.year + 1900
                num = ("yearish", 4, tm.year < -1900, abs(y))
        elif fc in "DRT":
            if fc == "D" and modifier:
                bad()
            else:
                sub = {"D": b"%m/%d/%y", "R": b"%H:%M",
                       "T": b"%H:%M:%S"}[fc]
                data = fmt_internal(sub, tm, ns, to_uppcase, pad, -1)
                width_add(width, data, pad)
        elif fc == "F":
            if modifier:
                bad()
            else:
                if pad == 0 and width < 0:
                    pad = "+"
                    subwidth = 4
                else:
                    subwidth = max(width - 6, 0)
                data = fmt_internal(b"%Y-%m-%d", tm, ns, to_uppcase, pad,
                                    subwidth)
                width_add(width, data, pad)
        elif fc in "dHIMSUWjmwekl":
            if modifier == "E":
                bad()
            elif fc == "d":
                num = ("num", 2, tm.mday)
            elif fc == "e":
                num = ("space", 2, tm.mday)
            elif fc == "H":
                num = ("num", 2, tm.hour)
            elif fc == "I":
                num = ("num", 2, hour12)
            elif fc == "k":
                num = ("space", 2, tm.hour)
            elif fc == "l":
                num = ("space", 2, hour12)
            elif fc == "M":
                num = ("num", 2, tm.min)
            elif fc == "S":
                num = ("num", 2, tm.sec)
            elif fc == "U":
                num = ("num", 2, (tm.yday - tm.wday + 7) // 7)
            elif fc == "W":
                num = ("num", 2, (tm.yday - (tm.wday - 1 + 7) % 7 + 7) // 7)
            elif fc == "j":
                num = ("signed", 3, tm.yday < -1, abs(tm.yday + 1))
            elif fc == "m":
                num = ("signed", 2, tm.mon < -1, abs(tm.mon + 1))
            elif fc == "w":
                num = ("num", 1, tm.wday)
            else:
                bad()
        elif fc == "u":
            num = ("num", 1, (tm.wday - 1 + 7) % 7 + 1)
        elif fc == "q":
            num = ("num", 1, tm.mon // 3 + 1)
        elif fc in "VgG":
            if modifier == "E":
                bad()
            else:
                year = tm.year + (1900 % 400 if tm.year < 0
                                  else 1900 % 400 - 400)
                year_adjust = 0
                days = iso_week_days(tm.yday, tm.wday)
                if days < 0:
                    year_adjust = -1
                    days = iso_week_days(tm.yday + (365 + isleap(year - 1)),
                                         tm.wday)
                else:
                    d = iso_week_days(tm.yday - (365 + isleap(year)),
                                      tm.wday)
                    if 0 <= d:
                        year_adjust = 1
                        days = d
                if fc == "g":
                    yy = cmod(cmod(tm.year, 100) + year_adjust, 100)
                    if yy < 0:
                        yy = (-yy if tm.year < -1900 - year_adjust
                              else yy + 100)
                    num = ("yearish", 2, False, yy)
                elif fc == "G":
                    gy = tm.year + 1900 + year_adjust
                    num = ("yearish", 4, tm.year < -1900 - year_adjust,
                           abs(gy))
                else:
                    num = ("num", 2, days // 7 + 1)
        elif fc == "N":
            if modifier == "E":
                bad()
            else:
                nv = ns
                if width <= 0:
                    width = 9
                ndigs = 9
                while width < ndigs or (1 < ndigs and nv % 10 == 0):
                    ndigs -= 1
                    nv //= 10
                digs = str(nv).rjust(ndigs, "0").encode() if ndigs else b""
                if not pad:
                    pad = "0"
                width_add(0, digs, pad)
                width_add(width - ndigs, b"", pad)
        elif fc == "n":
            width_add(width, b"\n", pad)
        elif fc == "t":
            width_add(width, b"\t", pad)
        elif fc == "s":
            t = tm.tsec
            num = ("raw", 1, t < 0, abs(t))
        elif fc == "Z":
            if change_case:
                to_uppcase, to_lowcase = False, True
            cpy(zone)
        elif fc in ":z":
            colons = 0
            ok = True
            if fc == ":":
                colons = 1
                while f + colons < n and fmt[f + colons] == 58:
                    colons += 1
                if not (f + colons < n and fmt[f + colons] == 122):
                    bad()
                    ok = False
                else:
                    f += colons
            if ok and tm.isdst >= 0:
                diff = tm.gmtoff
                negative = diff < 0 or (diff == 0 and zone[:1] == b"-")
                ad = abs(diff)
                hour_diff = ad // 3600
                min_diff = ad // 60 % 60
                sec_diff = ad % 60
                if colons == 3:
                    if sec_diff != 0:
                        colons = 2
                    elif min_diff != 0:
                        colons = 1
                    else:
                        num = ("tz", 3, negative, hour_diff, 0)
                if colons == 0:
                    num = ("tz", 5, negative, hour_diff * 100 + min_diff, 0)
                elif colons == 1:
                    num = ("tz", 6, negative, hour_diff * 100 + min_diff, 4)
                elif colons == 2:
                    num = ("tz", 9, negative,
                           hour_diff * 10000 + min_diff * 100 + sec_diff,
                           0o24)
                elif colons > 3:
                    bad()
        else:
            bad()

        if num is not None:
            k = num[0]
            always_sign = False
            mask = 0
            if k == "num" or k == "space":
                if k == "space" and pad == 0:
                    pad = "_"
                digits = num[1]
                negative = num[2] < 0
                u = abs(num[2])
            elif k == "signed":
                digits, negative, u = num[1], num[2], num[3]
            elif k == "yearish":
                digits, negative, u = num[1], num[2], num[3]
                if pad == 0:
                    pad = yr_spec
                always_sign = (pad == "+" and (
                    negative or (99 if digits == 2 else 9999) < u
                    or digits < width))
            elif k == "tz":
                digits, negative, u, mask = num[1], num[2], num[3], num[4]
                always_sign = True
            else:  # raw (%s)
                digits, negative, u = num[1], num[2], num[3]
            # Render digits with colon mask.
            buf = []
            while True:
                if mask & 1:
                    buf.append(":")
                mask >>= 1
                buf.append(chr(48 + u % 10))
                u //= 10
                if u == 0 and mask == 0:
                    break
            body = "".join(reversed(buf)).encode()
            if pad == 0:
                pad = "0"
            if width < 0:
                width = digits
            sign_char = b"-" if negative else (b"+" if always_sign else b"")
            numlen = len(body)
            shortage = width - (1 if sign_char else 0) - numlen
            padding = 0 if pad == "-" or shortage <= 0 else shortage
            if sign_char:
                if pad == "_":
                    out.extend(b" " * padding)
                    width -= padding
                out.extend(sign_char)
                width -= 1
            cpy(body)

        f += 1
        width = -1
    return bytes(out)


def format_time(fmt, t, ns, tz):
    tm = tz.localtime(t)
    if tm is None:
        return None
    tm.tsec = t
    return fmt_internal(fmt, tm, ns, False, 0, -1)


# ---------------------------------------------------------------------------
# Command-line handling

PROG = "date"


def err(msg):
    try:
        sys.stderr.buffer.write(PROG.encode() + b": " + msg + b"\n")
        sys.stderr.flush()
    except Exception:
        pass


def quote(b):
    return b"'" + b.replace(b"'", b"'\\''") + b"'"


def usage_fail():
    err(b"Try 'date --help' for more information.")
    return 1


HELP_TEXT = """\
Usage: date [OPTION]... [+FORMAT]
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
      --help     display this help and exit
      --version  output version information and exit

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

VERSION_TEXT = """\
date (GNU coreutils) 9.1
Copyright (C) 2022 Free Software Foundation, Inc.
License GPLv3+: GNU GPL version 3 or later <https://gnu.org/licenses/gpl.html>.
This is free software: you are free to change and redistribute it.
There is NO WARRANTY, to the extent permitted by law.

Written by David MacKenzie.
"""

LONG_OPTS = [
    # name, has_arg (0 none, 1 required, 2 optional), key
    ("date", 1, "d"),
    ("debug", 0, "debug"),
    ("file", 1, "f"),
    ("iso-8601", 2, "I"),
    ("reference", 1, "r"),
    ("resolution", 0, "resolution"),
    ("rfc-email", 0, "R"),
    ("rfc-822", 0, "R"),
    ("rfc-2822", 0, "R"),
    ("rfc-3339", 1, "rfc-3339"),
    ("set", 1, "s"),
    ("uct", 0, "u"),
    ("utc", 0, "u"),
    ("universal", 0, "u"),
    ("help", 0, "help"),
    ("version", 0, "version"),
]
SHORT_OPTS = {"d": 1, "f": 1, "I": 2, "r": 1, "R": 0, "s": 1, "u": 0}


class UsageError(Exception):
    pass


def getopt_long(args):
    """GNU getopt_long with argument permutation.  Yields (key, arg)
    and finally returns operands via the list attribute."""
    opts = []
    operands = []
    i = 0
    n = len(args)
    while i < n:
        a = args[i]
        if a == b"--":
            operands.extend(args[i + 1:])
            break
        if a.startswith(b"--"):
            body = a[2:]
            if b"=" in body:
                name, val = body.split(b"=", 1)
                has_eq = True
            else:
                name, val, has_eq = body, None, False
            try:
                name_s = name.decode("ascii")
            except UnicodeDecodeError:
                name_s = "\x00"
            match = None
            for lo in LONG_OPTS:
                if lo[0] == name_s:
                    match = lo
                    break
            if match is None:
                cands = [lo for lo in LONG_OPTS if lo[0].startswith(name_s)]
                if not cands or not name_s:
                    err(b"unrecognized option '" + a + b"'")
                    raise UsageError()
                first = cands[0]
                for c in cands[1:]:
                    if c[1] != first[1] or c[2] != first[2]:
                        err(b"option '" + a + b"' is ambiguous")
                        raise UsageError()
                match = first
            if match[1] == 0:
                if has_eq:
                    err(b"option '--" + match[0].encode()
                        + b"' doesn't allow an argument")
                    raise UsageError()
                opts.append((match[2], None))
            elif match[1] == 1:
                if not has_eq:
                    if i + 1 < n:
                        i += 1
                        val = args[i]
                    else:
                        err(b"option '--" + match[0].encode()
                            + b"' requires an argument")
                        raise UsageError()
                opts.append((match[2], val))
            else:
                opts.append((match[2], val if has_eq else None))
            i += 1
            continue
        if a.startswith(b"-") and len(a) > 1:
            j = 1
            while j < len(a):
                ch = chr(a[j])
                if ch not in SHORT_OPTS:
                    err(b"invalid option -- '" + a[j:j + 1] + b"'")
                    raise UsageError()
                kind = SHORT_OPTS[ch]
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
                        opts.append((ch, args[i]))
                    else:
                        err(b"option requires an argument -- '"
                            + ch.encode() + b"'")
                        raise UsageError()
                else:
                    opts.append((ch, rest if rest else None))
                break
            i += 1
            continue
        operands.append(a)
        i += 1
    return opts, operands


TIME_SPEC_STRINGS = ["hours", "minutes", "date", "seconds", "ns"]
ISO_FORMATS = {
    "date": b"%Y-%m-%d",
    "seconds": b"%Y-%m-%dT%H:%M:%S%:z",
    "ns": b"%Y-%m-%dT%H:%M:%S,%N%:z",
    "hours": b"%Y-%m-%dT%H%:z",
    "minutes": b"%Y-%m-%dT%H:%M%:z",
}
RFC3339_FORMATS = {
    "date": b"%Y-%m-%d",
    "seconds": b"%Y-%m-%d %H:%M:%S%:z",
    "ns": b"%Y-%m-%d %H:%M:%S.%N%:z",
}
RFC_EMAIL = b"%a, %d %b %Y %H:%M:%S %z"


def argmatch(arg, choices, optname):
    try:
        s = arg.decode("ascii")
    except UnicodeDecodeError:
        s = None
    if s is not None:
        if s in choices:
            return s
        cands = [c for c in choices if c.startswith(s)]
        if len(cands) == 1:
            return cands[0]
        if len(cands) > 1:
            err(b"ambiguous argument " + quote(arg) + b" for " + optname)
            raise UsageError()
    err(b"invalid argument " + quote(arg) + b" for " + optname)
    raise UsageError()


def posixtime(s, tz, now_sec):
    dot = s.find(b".")
    digits = s if dot < 0 else s[:dot]
    ln = len(digits)
    if not (8 <= ln <= 12 and ln % 2 == 0):
        return None
    if not all(isdigit(c) for c in digits):
        return None
    pairs = [int(digits[k:k + 2]) for k in range(0, ln, 2)]
    tm = TM()
    tm.mon = pairs[0] - 1
    tm.mday = pairs[1]
    tm.hour = pairs[2]
    tm.min = pairs[3]
    rest = pairs[4:]
    if len(rest) == 0:
        now = tz.localtime(now_sec)
        tm.year = now.year
    elif len(rest) == 1:
        tm.year = rest[0] + (100 if rest[0] < 69 else 0)
    else:
        tm.year = rest[0] * 100 + rest[1] - 1900
    if dot < 0:
        tm.sec = 0
    else:
        sec = s[dot + 1:]
        if len(sec) == 2 and all(isdigit(c) for c in sec):
            tm.sec = int(sec)
        else:
            return None
    tm0 = copy_tm(tm)
    t = tz.mktime(tm)
    if not mktime_ok(tm0, tm, t is not None):
        return None
    return t


def show_date(fmt, sec, ns, tz, out):
    data = format_time(fmt, sec, ns, tz)
    if data is None:
        err(b"time " + quote(str(sec).encode()) + b" is out of range")
        return False
    out.write(data + b"\n")
    return True


def adjust_resolution(fmt):
    out = bytearray(fmt)
    i = 0
    changed = False
    while i < len(fmt):
        if fmt[i] == 37:
            if fmt[i + 1:i + 3] == b"-N":
                out[i + 1] = ord("9")
                changed = True
                i += 2
            elif fmt[i + 1:i + 2] == b"%":
                i += 1
        i += 1
    return bytes(out) if changed else fmt


def main(argv):
    out = sys.stdout.buffer
    try:
        return run(argv, out)
    except UsageError:
        return usage_fail()
    finally:
        try:
            out.flush()
        except Exception:
            pass


def run(argv, out):
    args = [os.fsencode(a) for a in argv]
    opts, operands = getopt_long(args)
    datestr = None
    batch_file = None
    reference = None
    get_resolution = False
    set_datestr = None
    set_date = False
    fmt = None
    for key, val in opts:
        new_format = None
        if key == "d":
            datestr = val
        elif key == "debug":
            pass
        elif key == "f":
            batch_file = val
        elif key == "resolution":
            get_resolution = True
        elif key == "rfc-3339":
            spec = argmatch(val, ["date", "seconds", "ns"], b"'--rfc-3339'")
            new_format = RFC3339_FORMATS[spec]
        elif key == "I":
            if val is None:
                new_format = ISO_FORMATS["date"]
            else:
                spec = argmatch(val, TIME_SPEC_STRINGS, b"'--iso-8601'")
                new_format = ISO_FORMATS[spec]
        elif key == "r":
            reference = val
        elif key == "R":
            new_format = RFC_EMAIL
        elif key == "s":
            set_datestr = val
            set_date = True
        elif key == "u":
            pass
        elif key == "help":
            out.write(HELP_TEXT.encode())
            return 0
        elif key == "version":
            out.write(VERSION_TEXT.encode())
            return 0
        if new_format is not None:
            if fmt is not None:
                err(b"multiple output formats specified")
                return 1
            fmt = new_format

    option_specified_date = ((datestr is not None) + (batch_file is not None)
                             + (reference is not None) + get_resolution)
    if option_specified_date > 1:
        err(b"the options to specify dates for printing are mutually "
            b"exclusive")
        raise UsageError()
    if set_date and option_specified_date:
        err(b"the options to print and set the time may not be used "
            b"together")
        raise UsageError()
    if len(operands) > 1:
        err(b"extra operand " + quote(operands[1]))
        raise UsageError()
    if len(operands) == 1:
        if operands[0][:1] == b"+":
            if fmt is not None:
                err(b"multiple output formats specified")
                return 1
            fmt = operands[0][1:]
        elif set_date or option_specified_date:
            err(b"the argument " + quote(operands[0]) + b" lacks a leading "
                b"'+';\nwhen using an option to specify date(s), any "
                b"non-option\nargument must be a format string beginning "
                b"with '+'")
            raise UsageError()
    if fmt is None:
        fmt = b"%s.%N" if get_resolution else b"%a %b %e %H:%M:%S %Z %Y"
    fmt = adjust_resolution(fmt)

    tz = UTC
    now_ns = time.time_ns()

    if batch_file is not None:
        if batch_file == b"-":
            stream = sys.stdin.buffer
        else:
            try:
                stream = open(batch_file, "rb")
            except OSError as e:
                err(batch_file + b": " + (e.strerror or "error").encode())
                return 1
        ok = True
        with stream:
            data = stream.read()
        lines = data.split(b"\n")
        if lines and lines[-1] == b"":
            lines.pop()
            lines = [l + b"\n" for l in lines]
        else:
            lines = [l + b"\n" for l in lines[:-1]] + lines[-1:]
        for line in lines:
            r = parse_datetime(line, tz, now_ns)
            if r is None:
                shown = line[:-1] if line.endswith(b"\n") else line
                nul = shown.find(b"\0")
                if nul >= 0:
                    shown = shown[:nul]
                err(b"invalid date " + quote(shown))
                ok = False
            else:
                ok &= show_date(fmt, r[0], r[1], tz, out)
        return 0 if ok else 1

    ok = True
    valid = True
    when = (now_ns // BILLION, now_ns % BILLION)
    if not option_specified_date and not set_date:
        if operands:
            set_date = True
            datestr = operands[0]
            t = posixtime(datestr, tz, now_ns // BILLION)
            if t is None:
                valid = False
            else:
                when = (t, 0)
    else:
        if reference is not None:
            try:
                st = os.stat(reference)
            except OSError as e:
                err(reference + b": " + (e.strerror or "error").encode())
                return 1
            mt = st.st_mtime_ns
            when = (mt // BILLION, mt % BILLION)
        elif get_resolution:
            when = (0, 1)
        else:
            if set_datestr is not None:
                datestr = set_datestr
            r = parse_datetime(datestr, tz, now_ns)
            if r is None:
                valid = False
            else:
                when = r
    if not valid:
        err(b"invalid date " + quote(datestr))
        return 1
    if set_date:
        err(b"cannot set date: Operation not permitted")
        ok = False
    ok &= show_date(fmt, when[0], when[1], tz, out)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
