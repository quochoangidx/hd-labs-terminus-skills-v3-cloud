"""pyfind: a GNU find 4.9.0 replacement in pure Python.

Usage: python3 /app/pyfind/find.py [starting-point...] [expression]
"""

import os
import re
import stat
import sys
import time

S_IFMT = stat.S_IFMT
DAYSECS = 86400
NS = 1000000000


class Die(Exception):
    """Fatal error: message to stderr, exit status 1."""


class Quit(Exception):
    """-quit was evaluated."""


class RegexError(Exception):
    pass


def warn(msg):
    try:
        sys.stderr.write("find: " + msg + "\n")
        sys.stderr.flush()
    except Exception:
        pass


def qname(b):
    if isinstance(b, bytes):
        b = os.fsdecode(b)
    return "‘" + b + "’"


class G:
    status = 0
    out = None
    depth_first = False
    maxdepth = None
    mindepth = 0
    start_len = 0
    start_path = b""
    prune = False
    now_ns = 0
    expr = None


def write(b):
    G.out.write(b)


# ---------------------------------------------------------------------------
# Character classes (C locale)

def _cls(pred):
    return frozenset(c for c in range(256) if pred(c))


def _isupper(c):
    return 65 <= c <= 90


def _islower(c):
    return 97 <= c <= 122


def _isdigit(c):
    return 48 <= c <= 57


def _isalpha(c):
    return _isupper(c) or _islower(c)


def _isalnum(c):
    return _isalpha(c) or _isdigit(c)


def _isspace(c):
    return c == 32 or 9 <= c <= 13


CLASSES = {
    b"alpha": _cls(_isalpha),
    b"upper": _cls(_isupper),
    b"lower": _cls(_islower),
    b"digit": _cls(_isdigit),
    b"xdigit": _cls(lambda c: _isdigit(c) or 65 <= c <= 70 or 97 <= c <= 102),
    b"space": _cls(_isspace),
    b"blank": _cls(lambda c: c in (32, 9)),
    b"alnum": _cls(_isalnum),
    b"punct": _cls(lambda c: 33 <= c <= 126 and not _isalnum(c)),
    b"print": _cls(lambda c: 32 <= c <= 126),
    b"graph": _cls(lambda c: 33 <= c <= 126),
    b"cntrl": _cls(lambda c: c < 32 or c == 127),
}
WORDSET = frozenset(c for c in range(256) if _isalnum(c) or c == 95)


def lower_byte(c):
    return c + 32 if 65 <= c <= 90 else c


def ident(c):
    return c


# ---------------------------------------------------------------------------
# fnmatch (glibc semantics, flags 0 or FNM_CASEFOLD)

_STAR = ("star",)
_ANY = ("any",)
_NEVER = ("never",)


def _glob_bracket(pat, i, fold):
    n = len(pat)

    def at(k):
        return pat[k] if k < n else 0

    p = i
    neg = False
    if at(p) == 33 or at(p) == 94:
        neg = True
        p += 1
    items = []
    never = False
    c = at(p)
    p += 1
    while True:
        normal = False
        if c == 92:
            if at(p) == 0:
                return (_NEVER, n)
            c = fold(at(p))
            p += 1
            normal = True
        elif c == 91 and at(p) == 58:
            startp = p
            q = p
            name = bytearray()
            ok = False
            while True:
                if len(name) >= 256:
                    return (_NEVER, n)
                q += 1
                cc = at(q)
                if cc == 58 and at(q + 1) == 93:
                    q += 2
                    ok = True
                    break
                if cc < 97 or cc >= 122:
                    break
                name.append(cc)
            if ok:
                cl = CLASSES.get(bytes(name))
                if cl is None:
                    never = True
                else:
                    items.append(("class", cl))
                p = q
                c = at(p)
                p += 1
            else:
                p = startp
                c = 91
                normal = True
        elif c == 0:
            return None
        else:
            c = fold(c)
            normal = True
        if normal:
            is_range = at(p) == 45 and at(p + 1) != 0 and at(p + 1) != 93
            if not is_range:
                items.append(("ch", c))
            cold = c
            c = at(p)
            p += 1
            if c == 45 and at(p) != 93:
                cend = at(p)
                p += 1
                if cend == 92:
                    cend = at(p)
                    p += 1
                if cend == 0:
                    return (_NEVER, n)
                items.append(("range", cold, fold(cend)))
                c = at(p)
                p += 1
        if c == 93:
            break
    if never:
        return (_NEVER, p)
    chars = set()
    ranges = []
    classes = []
    for it in items:
        if it[0] == "ch":
            chars.add(it[1])
        elif it[0] == "range":
            ranges.append((it[1], it[2]))
        else:
            classes.append(it[1])

    def match(orig, fc):
        r = fc in chars
        if not r:
            for lo, hi in ranges:
                if lo <= fc <= hi:
                    r = True
                    break
        if not r:
            for cl in classes:
                if orig in cl:
                    r = True
                    break
        return r != neg

    return (("set", match), p)


def compile_glob(pat, casefold):
    fold = lower_byte if casefold else ident
    toks = []
    i = 0
    n = len(pat)
    while i < n:
        c = pat[i]
        if c == 42:
            if not toks or toks[-1] is not _STAR:
                toks.append(_STAR)
            i += 1
        elif c == 63:
            toks.append(_ANY)
            i += 1
        elif c == 92:
            if i + 1 >= n:
                toks.append(_NEVER)
                i += 1
            else:
                toks.append(("lit", fold(pat[i + 1])))
                i += 2
        elif c == 91:
            r = _glob_bracket(pat, i + 1, fold)
            if r is None:
                toks.append(("lit", 91))
                i += 1
            else:
                toks.append(r[0])
                i = r[1]
        else:
            toks.append(("lit", fold(c)))
            i += 1
    # fast path: literal-only
    if all(t[0] == "lit" for t in toks):
        lit = bytes(t[1] for t in toks)
        if casefold:
            return lambda s: s.lower() == lit
        return lambda s: s == lit
    toks = tuple(toks)

    def matcher(s):
        return _glob_match(toks, s, fold)

    return matcher


def _glob_match(toks, s, fold):
    n = len(s)
    nt = len(toks)
    ti = 0
    si = 0
    star_ti = -1
    star_si = 0
    while si < n:
        if ti < nt:
            t = toks[ti]
            if t is _STAR:
                star_ti = ti
                star_si = si
                ti += 1
                continue
            c = s[si]
            k = t[0]
            if k == "lit":
                ok = fold(c) == t[1]
            elif k == "any":
                ok = True
            elif k == "set":
                ok = t[1](c, fold(c))
            else:
                ok = False
            if ok:
                ti += 1
                si += 1
                continue
        if star_ti >= 0:
            star_si += 1
            si = star_si
            ti = star_ti + 1
            continue
        return False
    while ti < nt and toks[ti] is _STAR:
        ti += 1
    return ti == nt


# ---------------------------------------------------------------------------
# GNU regex -> Python re translation

def _set_to_py(members):
    members = sorted(set(members))
    if not members:
        return b"(?!)"
    if len(members) == 256:
        return b"(?s:.)"
    parts = []
    i = 0
    while i < len(members):
        j = i
        while j + 1 < len(members) and members[j + 1] == members[j] + 1:
            j += 1
        if j == i:
            parts.append(b"\\x%02x" % members[i])
        else:
            parts.append(b"\\x%02x-\\x%02x" % (members[i], members[j]))
        i = j + 1
    return b"[" + b"".join(parts) + b"]"


def _lit(c):
    return b"\\x%02x" % c


def _re_bracket(pat, i, kind, icase):
    n = len(pat)
    classes_ok = kind != "emacs"
    no_empty_ranges = kind != "emacs"
    tr = lower_byte if icase else ident

    def peek(k):
        if k >= n:
            return ("end", None, 0)
        c = pat[k]
        if c == 91 and k + 1 < n:
            c2 = pat[k + 1]
            if c2 == 46:
                return ("coll", None, 2)
            if c2 == 61:
                return ("equiv", None, 2)
            if c2 == 58 and classes_ok:
                return ("class", None, 2)
        if c == 45:
            return ("range", c, 1)
        if c == 93:
            return ("close", c, 1)
        if c == 94:
            return ("hat", c, 1)
        return ("char", tr(c), 1)

    def read_sym(k, typ):
        delim = {"coll": 46, "equiv": 61, "class": 58}[typ]
        name = bytearray()
        while True:
            if len(name) >= 32:
                raise RegexError("Unmatched [")
            if k >= n:
                raise RegexError("Unmatched [")
            ch = pat[k]
            k += 1
            if k >= n:
                raise RegexError("Unmatched [")
            if ch == delim and pat[k] == 93:
                k += 1
                break
            name.append(ch if typ == "class" else tr(ch))
        return bytes(name), k

    def elem(t, k, accept_hyphen):
        typ, val, ln = t
        k += ln
        if typ in ("coll", "equiv", "class"):
            name, k = read_sym(k, typ)
            return (typ, name), k
        if typ == "range" and not accept_hyphen:
            if peek(k)[0] != "close":
                raise RegexError("Invalid range end")
        return ("ch", val), k

    def elem_char(e):
        if e[0] == "ch":
            return e[1]
        if e[0] == "coll":
            if len(e[1]) != 1:
                raise RegexError("Invalid collation character")
            return e[1][0]
        raise RegexError("Invalid range end")

    members = set()
    neg = False
    t = peek(i)
    if t[0] == "hat":
        neg = True
        i += 1
        t = peek(i)
    if t[0] == "close":
        t = ("char", t[1], 1)
    first = True
    while True:
        if t[0] == "end":
            raise RegexError("Unmatched [")
        start, i = elem(t, i, first)
        first = False
        t = peek(i)
        is_range = False
        t2 = None
        if start[0] not in ("class", "equiv"):
            if t[0] == "end":
                raise RegexError("Unmatched [")
            if t[0] == "range":
                i2 = i + t[2]
                t2 = peek(i2)
                if t2[0] == "end":
                    raise RegexError("Unmatched [")
                if t2[0] == "close":
                    t = ("char", 45, 1)
                else:
                    is_range = True
                    i = i2
        if is_range:
            end, i = elem(t2, i, True)
            t = peek(i)
            s = elem_char(start)
            e = elem_char(end)
            if s > e:
                if no_empty_ranges:
                    raise RegexError("Invalid range end")
            else:
                members.update(range(s, e + 1))
        else:
            if start[0] == "ch":
                members.add(start[1])
            elif start[0] in ("coll", "equiv"):
                if len(start[1]) != 1:
                    raise RegexError("Invalid collation character")
                members.add(start[1][0])
            else:
                name = start[1]
                if icase and name in (b"upper", b"lower"):
                    name = b"alpha"
                cl = CLASSES.get(name)
                if cl is None:
                    raise RegexError("Invalid character class name")
                members.update(cl)
        if t[0] == "end":
            raise RegexError("Unmatched [")
        if t[0] == "close":
            i += 1
            break
    if neg:
        members = set(range(256)) - members
    return _set_to_py(members), i


def _re_tokenize(pat, kind, icase):
    tr = lower_byte if icase else ident
    toks = []
    i = 0
    n = len(pat)
    ere = kind == "ere"
    bre = kind == "bre"
    while i < n:
        c = pat[i]
        if c == 92:
            if i + 1 >= n:
                raise RegexError("Trailing backslash")
            c2 = pat[i + 1]
            i += 2
            ch = chr(c2)
            if not ere and ch == "(":
                toks.append(("open",))
            elif not ere and ch == ")":
                toks.append(("close",))
            elif not ere and ch == "|":
                toks.append(("alt",))
            elif bre and ch == "{":
                toks.append(("ivopen",))
            elif bre and ch == "}":
                toks.append(("ivclose",))
            elif bre and ch == "+":
                toks.append(("plus",))
            elif bre and ch == "?":
                toks.append(("qmark",))
            elif ch in "123456789":
                toks.append(("backref", c2 - 48))
            elif ch == "w":
                toks.append(("set", _set_to_py(WORDSET)))
            elif ch == "W":
                toks.append(("set", _set_to_py(set(range(256)) - WORDSET)))
            elif ch == "s":
                toks.append(("set", _set_to_py(CLASSES[b"space"])))
            elif ch == "S":
                toks.append(("set", _set_to_py(set(range(256)) - CLASSES[b"space"])))
            elif ch == "`":
                toks.append(("anchor", b"\\A"))
            elif ch == "'":
                toks.append(("anchor", b"\\Z"))
            elif ch == "<":
                toks.append(("anchor", b"\\b(?=\\w)"))
            elif ch == ">":
                toks.append(("anchor", b"\\b(?<=\\w)"))
            elif ch == "b":
                toks.append(("anchor", b"\\b"))
            elif ch == "B":
                toks.append(("anchor", b"\\B"))
            else:
                toks.append(("char", tr(c2)))
            continue
        ch = chr(c)
        if ch == "[":
            py, i = _re_bracket(pat, i + 1, kind, icase)
            toks.append(("set", py))
            continue
        i += 1
        if ch == ".":
            toks.append(("any",))
        elif ch == "*":
            toks.append(("star",))
        elif ch == "+" and not bre:
            toks.append(("plus",))
        elif ch == "?" and not bre:
            toks.append(("qmark",))
        elif ere and ch == "{":
            toks.append(("ivopen",))
        elif ere and ch == "}":
            toks.append(("ivclose",))
        elif ere and ch == "(":
            toks.append(("open",))
        elif ere and ch == ")":
            toks.append(("close",))
        elif ere and ch == "|":
            toks.append(("alt",))
        elif ch == "^":
            toks.append(("caret",))
        elif ch == "$":
            toks.append(("dollar",))
        else:
            toks.append(("char", tr(c)))
    # resolve context-dependent anchors
    res = []
    for k, t in enumerate(toks):
        if t[0] == "caret":
            if ere or k == 0 or toks[k - 1][0] in ("open", "alt"):
                res.append(("anchor", b"\\A"))
            else:
                res.append(("char", 94))
        elif t[0] == "dollar":
            if ere or k == len(toks) - 1 or toks[k + 1][0] in ("alt", "close"):
                res.append(("anchor", b"\\Z"))
            else:
                res.append(("char", 36))
        else:
            res.append(t)
    return res


class _REParser:
    def __init__(self, toks, kind, dot):
        self.toks = toks
        self.kind = kind
        self.dot = dot
        self.pos = 0
        self.ngroups = 0
        self.completed = set()

    def tok(self):
        if self.pos < len(self.toks):
            return self.toks[self.pos]
        return ("end",)

    def _stop(self, t, nest):
        return t[0] in ("alt", "end") or (nest and t[0] == "close")

    def parse(self):
        r = self.parse_reg_exp(0)
        if self.tok()[0] != "end":
            raise RegexError("Unmatched ) or \\)")
        return r

    def parse_reg_exp(self, nest):
        t = self.tok()
        alts = [b"" if self._stop(t, nest) else self.parse_branch(nest)]
        while self.tok()[0] == "alt":
            self.pos += 1
            t = self.tok()
            alts.append(b"" if self._stop(t, nest) else self.parse_branch(nest))
        return b"|".join(alts)

    def parse_branch(self, nest):
        parts = [self.parse_expression(nest)]
        while not self._stop(self.tok(), nest):
            parts.append(self.parse_expression(nest))
        return b"".join(parts)

    def fetch_number(self):
        num = -1
        while True:
            self.pos += 1
            t = self.tok()
            if t[0] == "end":
                return -2, t
            if t[0] == "ivclose" or (t[0] == "char" and t[1] == 44):
                return num, t
            if t[0] != "char" or not (48 <= t[1] <= 57) or num == -2:
                num = -2
            elif num == -1:
                num = t[1] - 48
            else:
                num = min(32768, num * 10 + t[1] - 48)

    def parse_expression(self, nest):
        t = self.tok()
        typ = t[0]
        kind = self.kind
        if typ == "char":
            atom = _lit(t[1])
            self.pos += 1
        elif typ == "any":
            atom = self.dot
            self.pos += 1
        elif typ == "set":
            atom = t[1]
            self.pos += 1
        elif typ == "backref":
            if t[1] not in self.completed:
                raise RegexError("Invalid back reference")
            atom = b"(?:\\%d)" % t[1]
            self.pos += 1
        elif typ == "open":
            self.pos += 1
            self.ngroups += 1
            g = self.ngroups
            if self.tok()[0] == "close":
                inner = b""
            else:
                inner = self.parse_reg_exp(nest + 1)
                if self.tok()[0] != "close":
                    raise RegexError("Unmatched ( or \\(")
            self.pos += 1
            self.completed.add(g)
            atom = b"(" + inner + b")"
        elif typ == "anchor":
            self.pos += 1
            return t[1]
        elif typ in ("star", "plus", "qmark", "ivopen"):
            if kind == "ere":
                raise RegexError("Invalid preceding regular expression")
            if typ == "ivopen":
                raise RegexError("Invalid preceding regular expression")
            atom = _lit({"star": 42, "plus": 43, "qmark": 63}[typ])
            self.pos += 1
        elif typ == "close":
            if kind == "ere":
                atom = _lit(41)
                self.pos += 1
            else:
                raise RegexError("Unmatched ) or \\)")
        elif typ == "ivclose":
            atom = _lit(125)
            self.pos += 1
        else:
            raise RegexError("Invalid regular expression")
        while self.tok()[0] in ("star", "plus", "qmark", "ivopen"):
            d = self.tok()[0]
            if d == "star":
                q = b"*"
                self.pos += 1
            elif d == "plus":
                q = b"+"
                self.pos += 1
            elif d == "qmark":
                q = b"?"
                self.pos += 1
            else:
                start, tk = self.fetch_number()
                end = None
                if start == -1:
                    if tk[0] == "char" and tk[1] == 44:
                        start = 0
                    else:
                        raise RegexError("Invalid content of \\{\\}")
                if start != -2:
                    if tk[0] == "ivclose":
                        end = start
                    elif tk[0] == "char" and tk[1] == 44:
                        end, tk = self.fetch_number()
                    else:
                        end = -2
                if start == -2 or end == -2:
                    if tk[0] == "end":
                        raise RegexError("Unmatched \\{")
                    raise RegexError("Invalid content of \\{\\}")
                if (end != -1 and start > end) or tk[0] != "ivclose":
                    raise RegexError("Invalid content of \\{\\}")
                if (start if end == -1 else end) > 32767:
                    raise RegexError("Regular expression too big")
                self.pos += 1
                if end == -1:
                    q = b"{%d,}" % start
                else:
                    q = b"{%d,%d}" % (start, end)
            atom = b"(?:" + atom + b")" + q
            if kind == "bre" and self.tok()[0] in ("star", "ivopen"):
                raise RegexError("Invalid preceding regular expression")
        return atom


REGEX_TYPES = {
    "findutils-default": ("emacs", True),
    "emacs": ("emacs", False),
    "posix-basic": ("bre", True),
    "posix-extended": ("ere", True),
}


def compile_regex(pat, rtype, icase):
    kind, dotnl = REGEX_TYPES[rtype]
    dot = b"(?s:.)" if dotnl else b"[^\\n]"
    toks = _re_tokenize(pat, kind, icase)
    body = _REParser(toks, kind, dot).parse()
    try:
        return re.compile(b"(?:" + body + b")")
    except (re.error, OverflowError, RecursionError) as e:
        raise RegexError(str(e))


# ---------------------------------------------------------------------------
# Modes

S_ISUID, S_ISGID, S_ISVTX = 0o4000, 0o2000, 0o1000
S_IRWXU, S_IRWXG, S_IRWXO = 0o700, 0o070, 0o007
CHMOD_MODE_BITS = 0o7777


def mode_compile(s):
    if s and s[0] in "01234567":
        v = 0
        for ch in s:
            if ch not in "01234567":
                return None
            v = v * 8 + int(ch)
            if v > 0o7777:
                return None
        if len(s) < 5:
            mentioned = (v & (S_ISUID | S_ISGID)) | S_ISVTX | 0o777
        else:
            mentioned = CHMOD_MODE_BITS
        return [("=", "ord", CHMOD_MODE_BITS, v, mentioned)]
    changes = []
    i = 0
    n = len(s)
    while True:
        affected = 0
        while True:
            if i >= n:
                return None
            ch = s[i]
            if ch == "u":
                affected |= S_ISUID | S_IRWXU
            elif ch == "g":
                affected |= S_ISGID | S_IRWXG
            elif ch == "o":
                affected |= S_ISVTX | S_IRWXO
            elif ch == "a":
                affected |= CHMOD_MODE_BITS
            elif ch in "=+-":
                break
            else:
                return None
            i += 1
        while True:
            op = s[i]
            i += 1
            ch = s[i] if i < n else ""
            if ch == "u":
                value, flag, i = S_IRWXU, "copy", i + 1
                mentioned = 0
            elif ch == "g":
                value, flag, i = S_IRWXG, "copy", i + 1
                mentioned = 0
            elif ch == "o":
                value, flag, i = S_IRWXO, "copy", i + 1
                mentioned = 0
            else:
                value = 0
                flag = "ord"
                mentioned = 0
                while i < n:
                    ch = s[i]
                    if ch == "r":
                        value |= 0o444
                    elif ch == "w":
                        value |= 0o222
                    elif ch == "x":
                        value |= 0o111
                    elif ch == "X":
                        flag = "X"
                    elif ch == "s":
                        value |= S_ISUID | S_ISGID
                    elif ch == "t":
                        value |= S_ISVTX
                    else:
                        break
                    i += 1
            if not mentioned:
                mentioned = (affected & value) if affected else value
            changes.append((op, flag, affected, value, mentioned))
            if i < n and s[i] in "=+-":
                continue
            break
        if i < n and s[i] == ",":
            i += 1
            continue
        break
    if i != n:
        return None
    return changes


def mode_adjust(oldmode, is_dir, umask_value, changes):
    newmode = oldmode & CHMOD_MODE_BITS
    for op, flag, affected, value, mentioned in changes:
        omit_change = ((S_ISUID | S_ISGID) if is_dir else 0) & ~mentioned
        if flag == "copy":
            value &= newmode
            value |= ((0o444 if value & 0o444 else 0)
                      | (0o222 if value & 0o222 else 0)
                      | (0o111 if value & 0o111 else 0))
        elif flag == "X":
            if (newmode & 0o111) or is_dir:
                value |= 0o111
        value &= (affected if affected else ~umask_value) & ~omit_change
        if op == "=":
            preserved = ((~affected) if affected else 0) | omit_change
            newmode = (newmode & preserved) | value
        elif op == "+":
            newmode |= value
        else:
            newmode &= ~value
    return newmode & CHMOD_MODE_BITS


def filemode(m):
    fmt = S_IFMT(m)
    t = {stat.S_IFREG: "-", stat.S_IFDIR: "d", stat.S_IFLNK: "l",
         stat.S_IFCHR: "c", stat.S_IFBLK: "b", stat.S_IFIFO: "p",
         stat.S_IFSOCK: "s"}.get(fmt, "?")
    r = [t]
    r.append("r" if m & 0o400 else "-")
    r.append("w" if m & 0o200 else "-")
    if m & S_ISUID:
        r.append("s" if m & 0o100 else "S")
    else:
        r.append("x" if m & 0o100 else "-")
    r.append("r" if m & 0o040 else "-")
    r.append("w" if m & 0o020 else "-")
    if m & S_ISGID:
        r.append("s" if m & 0o010 else "S")
    else:
        r.append("x" if m & 0o010 else "-")
    r.append("r" if m & 0o004 else "-")
    r.append("w" if m & 0o002 else "-")
    if m & S_ISVTX:
        r.append("t" if m & 0o001 else "T")
    else:
        r.append("x" if m & 0o001 else "-")
    return "".join(r).encode()


def type_char(m):
    fmt = S_IFMT(m)
    return {stat.S_IFREG: "f", stat.S_IFDIR: "d", stat.S_IFLNK: "l",
            stat.S_IFCHR: "c", stat.S_IFBLK: "b", stat.S_IFIFO: "p",
            stat.S_IFSOCK: "s"}.get(fmt, "U")


# ---------------------------------------------------------------------------
# Path helpers

def base_len(p):
    n = len(p)
    while n > 1 and p[n - 1] == 47:
        n -= 1
    return n


def base_name(p):
    i = 0
    while i < len(p) and p[i] == 47:
        i += 1
    base = i
    last_slash = False
    for k in range(i, len(p)):
        if p[k] == 47:
            last_slash = True
        elif last_slash:
            base = k
            last_slash = False
    b = p[base:]
    if not b:
        return p[:base_len(p)]
    n = base_len(b)
    if n < len(b) and b[n] == 47:
        n += 1
    return b[:n]


def name_for_match(p):
    b = base_name(p)
    if len(b) > 1:
        b = b[:base_len(b)]
    return b


# ---------------------------------------------------------------------------
# printf

def fmt_int(value, conv, flags, zero, width, prec):
    neg = value < 0
    v = -value if neg else value
    digits = str(v) if conv == "d" else "%o" % v
    if prec is not None:
        if prec == 0 and v == 0:
            digits = ""
        digits = digits.rjust(prec, "0")
    if conv == "o" and "#" in flags and not digits.startswith("0"):
        digits = "0" + digits
    if neg:
        sign = "-"
    elif conv == "d" and "+" in flags:
        sign = "+"
    elif conv == "d" and " " in flags:
        sign = " "
    else:
        sign = ""
    body = sign + digits
    if len(body) < width:
        if "-" in flags:
            body = body.ljust(width)
        elif zero and prec is None:
            body = sign + digits.rjust(width - len(sign), "0")
        else:
            body = body.rjust(width)
    return body.encode()


def fmt_str(s, flags, width, prec):
    if prec is not None:
        s = s[:prec]
    if len(s) < width:
        if "-" in flags:
            s = s + b" " * (width - len(s))
        else:
            s = b" " * (width - len(s)) + s
    return s


ESCAPES = {"a": 7, "b": 8, "f": 12, "n": 10, "r": 13, "t": 9, "v": 11, "\\": 92}
DIRECTIVES = "abcdDfFgGhHiklmMnpPsStuUyYZ"


def compile_printf(fmt):
    """Returns a list of segments."""
    segs = []
    lit = bytearray()
    i = 0
    n = len(fmt)
    while i < n:
        c = fmt[i]
        if c == 92:
            if i + 1 >= n:
                warn("warning: escape `\\' followed by nothing at all")
                lit.append(92)
                i += 1
                continue
            c2 = fmt[i + 1]
            if 48 <= c2 <= 55:
                v = 0
                j = i + 1
                k = 0
                while k < 3 and j < n and 48 <= fmt[j] <= 55:
                    v = v * 8 + fmt[j] - 48
                    j += 1
                    k += 1
                lit.append(v & 0xFF)
                i = j
                continue
            ch = chr(c2)
            if ch == "c":
                if lit:
                    segs.append(("lit", bytes(lit)))
                    lit = bytearray()
                segs.append(("stop",))
                i += 2
                # the rest of the format is ignored after \c
                return segs
            if ch in ESCAPES:
                lit.append(ESCAPES[ch])
                i += 2
                continue
            warn("warning: unrecognized escape `\\%s'" % ch)
            lit.append(92)
            lit.append(c2)
            i += 2
            continue
        if c == 37:
            if i + 1 >= n:
                raise Die("error: %s at end of format string" % "%")
            if fmt[i + 1] == 37:
                lit.append(37)
                i += 2
                continue
            j = i + 1
            flags = ""
            while j < n and chr(fmt[j]) in "-+ #":
                flags += chr(fmt[j])
                j += 1
            ws = j
            while j < n and 48 <= fmt[j] <= 57:
                j += 1
            wstr = fmt[ws:j].decode()
            prec = None
            if j < n and fmt[j] == 46:
                j += 1
                ps = j
                while j < n and 48 <= fmt[j] <= 57:
                    j += 1
                prec = int(fmt[ps:j]) if j > ps else 0
            d = chr(fmt[j]) if j < n else ""
            if d and d in DIRECTIVES:
                if lit:
                    segs.append(("lit", bytes(lit)))
                    lit = bytearray()
                zero = wstr.startswith("0")
                width = int(wstr) if wstr else 0
                segs.append(("fmt", d, flags, zero, width, prec, None))
                i = j + 1
                continue
            if d and d in "ABCT" and j + 1 < n:
                if lit:
                    segs.append(("lit", bytes(lit)))
                    lit = bytearray()
                zero = wstr.startswith("0")
                width = int(wstr) if wstr else 0
                segs.append(("fmt", d, flags, zero, width, prec, chr(fmt[j + 1])))
                i = j + 2
                continue
            # unrecognized: drop the '%', keep the rest as text
            warn("warning: unrecognized format directive `%%%s'" % d)
            i += 1
            continue
        lit.append(c)
        i += 1
    if lit:
        segs.append(("lit", bytes(lit)))
    return segs


def _ctime(ns):
    t = time.gmtime(ns // NS)
    return time.strftime("%a %b %d %H:%M:%S %Y", t).encode()


def _timefmt(ns, k):
    secs = ns // NS
    frac = ns % NS
    t = time.gmtime(secs)
    if k == "@":
        return ("%d.%010d" % (secs, frac * 10)).encode()
    if k == "+":
        return (time.strftime("%Y-%m-%d+%H:%M:%S", t) + ".%010d" % (frac * 10)).encode()
    if k == "S":
        return (time.strftime("%S", t) + ".%010d" % (frac * 10)).encode()
    if k == "T":
        return (time.strftime("%H:%M:%S", t) + ".%010d" % (frac * 10)).encode()
    try:
        return time.strftime("%" + k, t).encode()
    except ValueError:
        return b""


def run_printf(segs, path, st, depth):
    out = []
    for seg in segs:
        k = seg[0]
        if k == "lit":
            out.append(seg[1])
            continue
        if k == "stop":
            break
        _, d, flags, zero, width, prec, aux = seg
        if d == "d":
            out.append(fmt_int(depth, "d", flags, zero, width, prec))
            continue
        if d == "m":
            out.append(fmt_int(st.st_mode & 0o7777, "o", flags, zero, width, prec))
            continue
        if d == "p":
            s = path
        elif d == "P":
            s = path[G.start_len:]
            if s[:1] == b"/":
                s = s[1:]
        elif d == "f":
            s = base_name(path)
        elif d == "h":
            idx = path.rfind(b"/")
            s = b"." if idx < 0 else path[:idx]
        elif d == "H":
            s = G.start_path
        elif d == "s":
            s = str(st.st_size).encode()
        elif d == "y":
            s = type_char(st.st_mode).encode()
        elif d == "Y":
            if stat.S_ISLNK(st.st_mode):
                try:
                    s = type_char(os.stat(path).st_mode).encode()
                except OSError as e:
                    import errno
                    if e.errno == errno.ELOOP:
                        s = b"L"
                    elif e.errno == errno.ENOENT:
                        s = b"N"
                    else:
                        s = b"?"
            else:
                s = type_char(st.st_mode).encode()
        elif d == "M":
            s = filemode(st.st_mode)
        elif d == "l":
            if stat.S_ISLNK(st.st_mode):
                try:
                    s = os.readlink(path)
                except OSError:
                    s = b""
            else:
                s = b""
        elif d == "n":
            s = str(st.st_nlink).encode()
        elif d == "i":
            s = str(st.st_ino).encode()
        elif d == "U":
            s = str(st.st_uid).encode()
        elif d == "G":
            s = str(st.st_gid).encode()
        elif d == "u":
            try:
                import pwd
                s = pwd.getpwuid(st.st_uid).pw_name.encode()
            except Exception:
                s = str(st.st_uid).encode()
        elif d == "g":
            try:
                import grp
                s = grp.getgrgid(st.st_gid).gr_name.encode()
            except Exception:
                s = str(st.st_gid).encode()
        elif d == "k":
            s = str((st.st_blocks * 512 + 1023) // 1024).encode()
        elif d == "b":
            s = str(st.st_blocks).encode()
        elif d == "D":
            s = str(st.st_dev).encode()
        elif d == "S":
            s = (("%g" % (st.st_blocks * 512 / st.st_size)) if st.st_size else "1").encode()
        elif d == "F":
            s = b"unknown"
        elif d == "Z":
            s = b""
        elif d in "at":
            s = _ctime(st.st_atime_ns if d == "a" else st.st_mtime_ns)
        elif d == "c":
            s = _ctime(st.st_ctime_ns)
        elif d == "B":
            s = _ctime(st.st_mtime_ns) if aux is None else _timefmt(st.st_mtime_ns, aux)
        elif d in "ACT":
            ns = {"A": st.st_atime_ns, "C": st.st_ctime_ns, "T": st.st_mtime_ns}[d]
            s = _timefmt(ns, aux)
        else:
            s = b""
        out.append(fmt_str(s, flags, width, prec))
    write(b"".join(out))


# ---------------------------------------------------------------------------
# Expression parser

def get_comp(s):
    if s.startswith("+"):
        return "gt", s[1:]
    if s.startswith("-"):
        return "lt", s[1:]
    return "eq", s


_UINT_RE = re.compile(r"[ \t\n\v\f\r]*\+?[0-9]+\Z")
_FLOAT_RE = re.compile(r"[ \t\n\v\f\r]*[+-]?([0-9]+\.?[0-9]*|\.[0-9]+)([eE][+-]?[0-9]+)?\Z")


def parse_uint(s):
    if not _UINT_RE.match(s):
        return None
    return int(s.strip())


def cmp_num(kind, val, n):
    if kind == "gt":
        return val > n
    if kind == "lt":
        return val < n
    return val == n


class Parser:
    def __init__(self, toks):
        self.t = toks
        self.i = 0
        self.has_action = False
        self.regextype = "findutils-default"

    def peek(self):
        return self.t[self.i] if self.i < len(self.t) else None

    def arg(self, pred):
        if self.i >= len(self.t):
            raise Die("missing argument to `%s'" % pred)
        a = self.t[self.i]
        self.i += 1
        return a

    def parse(self):
        if not self.t:
            return None
        e = self.parse_comma()
        if self.i < len(self.t):
            tok = self.t[self.i]
            if tok == ")":
                raise Die("invalid expression; you have too many ')'")
            raise Die("invalid expression")
        return e

    def _need_operand(self, op):
        t = self.peek()
        if t is None or t in (")", ",", "-o", "-or", "-a", "-and"):
            raise Die("invalid expression; expected an expression after '%s'" % op)

    def parse_comma(self):
        left = self.parse_or()
        while self.peek() == ",":
            self.i += 1
            self._need_operand(",")
            right = self.parse_or()
            left = (lambda a, b: lambda p, s, d: (a(p, s, d), b(p, s, d))[1])(left, right)
        return left

    def parse_or(self):
        left = self.parse_and()
        while self.peek() in ("-o", "-or"):
            op = self.peek()
            self.i += 1
            self._need_operand(op)
            right = self.parse_and()
            left = (lambda a, b: lambda p, s, d: a(p, s, d) or b(p, s, d))(left, right)
        return left

    def parse_and(self):
        left = self.parse_not()
        while True:
            t = self.peek()
            if t in ("-a", "-and"):
                self.i += 1
                self._need_operand(t)
            elif t is None or t in (")", ",", "-o", "-or"):
                break
            right = self.parse_not()
            left = (lambda a, b: lambda p, s, d: a(p, s, d) and b(p, s, d))(left, right)
        return left

    def parse_not(self):
        t = self.peek()
        if t in ("!", "-not"):
            self.i += 1
            self._need_operand(t)
            e = self.parse_not()
            return lambda p, s, d: not e(p, s, d)
        return self.parse_primary()

    def parse_primary(self):
        t = self.peek()
        if t is None:
            raise Die("invalid expression")
        if t == "(":
            self.i += 1
            if self.peek() == ")":
                raise Die("invalid expression; empty parentheses are not allowed.")
            if self.peek() is None:
                raise Die("invalid expression; I was expecting to find a ')' somewhere but did not see one.")
            e = self.parse_comma()
            if self.peek() != ")":
                raise Die("invalid expression; I was expecting to find a ')' somewhere but did not see one.")
            self.i += 1
            return e
        if t in ("-a", "-and", "-o", "-or", ","):
            raise Die("invalid expression; you have used a binary operator '%s' with nothing before it." % t)
        if t == ")":
            raise Die("invalid expression; you have too many ')'")
        self.i += 1
        h = PRIMARIES.get(t)
        if h is None:
            if t.startswith("-"):
                raise Die("unknown predicate `%s'" % t)
            raise Die("paths must precede expression: `%s'" % t)
        return h(self, t)


def TRUE(p, s, d):
    return True


def FALSE(p, s, d):
    return False


def p_true(ps, name):
    return TRUE


def p_false(ps, name):
    return FALSE


def p_depth(ps, name):
    G.depth_first = True
    return TRUE


def p_noop(ps, name):
    return TRUE


def p_maxmin(ps, name):
    a = ps.arg(name)
    if not a or not all(c in "0123456789" for c in a):
        raise Die("Expected a positive decimal integer argument to %s, but got %s" % (name, qname(a)))
    v = int(a)
    if v > 2147483647:
        raise Die("Expected a positive decimal integer argument to %s, but got %s" % (name, qname(a)))
    if name == "-maxdepth":
        G.maxdepth = v
    else:
        G.mindepth = v
    return TRUE


def p_regextype(ps, name):
    a = ps.arg(name)
    if a not in REGEX_TYPES:
        raise Die("Unknown regular expression type %s" % qname(a))
    ps.regextype = a
    return TRUE


def p_name(ps, name):
    a = os.fsencode(ps.arg(name))
    m = compile_glob(a, name == "-iname")
    return lambda p, s, d: m(name_for_match(p))


def p_path(ps, name):
    a = os.fsencode(ps.arg(name))
    m = compile_glob(a, name in ("-ipath", "-iwholename"))
    return lambda p, s, d: m(p)


def p_lname(ps, name):
    a = os.fsencode(ps.arg(name))
    m = compile_glob(a, name == "-ilname")

    def f(p, s, d):
        if not stat.S_ISLNK(s.st_mode):
            return False
        try:
            return m(os.readlink(p))
        except OSError:
            return False
    return f


def p_regex(ps, name):
    a = os.fsencode(ps.arg(name))
    icase = name == "-iregex"
    try:
        rx = compile_regex(a, ps.regextype, icase)
    except RegexError as e:
        raise Die(str(e))
    except RecursionError:
        raise Die("Regular expression too big")
    if icase:
        return lambda p, s, d: rx.fullmatch(p.lower()) is not None
    return lambda p, s, d: rx.fullmatch(p) is not None


TYPE_BITS = {"f": stat.S_IFREG, "d": stat.S_IFDIR, "l": stat.S_IFLNK,
             "b": stat.S_IFBLK, "c": stat.S_IFCHR, "p": stat.S_IFIFO,
             "s": stat.S_IFSOCK, "D": -1}


def p_type(ps, name):
    a = ps.arg(name)
    if not a:
        raise Die("Arguments to %s should contain at least one letter" % name)
    wanted = set()
    i = 0
    while i < len(a):
        c = a[i]
        if c not in TYPE_BITS:
            raise Die("Unknown argument to %s: %s" % (name, c))
        if TYPE_BITS[c] in wanted:
            raise Die("Duplicate file type '%s' in the argument list to %s." % (c, name))
        wanted.add(TYPE_BITS[c])
        i += 1
        if i < len(a):
            if a[i] != ",":
                raise Die("Must separate multiple arguments to %s using: ','" % name)
            i += 1
            if i >= len(a):
                raise Die("Last file type in list argument to %s is missing, i.e., list is ending on: ','" % name)
    wanted = frozenset(wanted)
    return lambda p, s, d: S_IFMT(s.st_mode) in wanted


SIZE_UNITS = {"b": 512, "c": 1, "w": 2, "k": 1024, "M": 1048576, "G": 1073741824}


def p_size(ps, name):
    a = ps.arg(name)
    if not a:
        raise Die("invalid null argument to -size")
    suf = a[-1]
    if suf in SIZE_UNITS:
        unit = SIZE_UNITS[suf]
        num = a[:-1]
    elif suf in "0123456789":
        unit = 512
        num = a
    else:
        raise Die("invalid -size type `%s'" % suf)
    kind, rest = get_comp(num)
    v = parse_uint(rest)
    if v is None:
        raise Die("Invalid argument `%s' to -size" % a)

    def f(p, s, d):
        sz = s.st_size
        blocks = sz // unit + (1 if sz % unit else 0)
        return cmp_num(kind, blocks, v)
    return f


def p_links(ps, name):
    a = ps.arg(name)
    kind, rest = get_comp(a)
    v = parse_uint(rest)
    if v is None:
        raise Die("invalid argument `%s' to `%s'" % (a, name))
    return lambda p, s, d: cmp_num(kind, s.st_nlink, v)


def p_empty(ps, name):
    def f(p, s, d):
        m = s.st_mode
        if stat.S_ISREG(m):
            return s.st_size == 0
        if stat.S_ISDIR(m):
            try:
                with os.scandir(p) as it:
                    for _ in it:
                        return False
                return True
            except OSError as e:
                warn("%s: %s" % (qname(p), e.strerror))
                G.status = 1
                return False
        return False
    return f


def p_perm(ps, name):
    a = ps.arg(name)
    if a.startswith("-"):
        kind, ms = "all", a[1:]
    elif a.startswith("/"):
        kind, ms = "any", a[1:]
    else:
        kind, ms = "exact", a
    ch = mode_compile(ms)
    if ch is None:
        raise Die("invalid mode %s" % qname(a))
    vals = (mode_adjust(0, False, 0, ch), mode_adjust(0, True, 0, ch))

    def f(p, s, d):
        m = s.st_mode
        v = vals[1 if stat.S_ISDIR(m) else 0]
        if kind == "all":
            return (m & v) == v
        if kind == "any":
            if v == 0:
                return True
            return (m & v) != 0
        return (m & 0o7777) == v
    return f


def _parse_float(s):
    if not _FLOAT_RE.match(s):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _time_attr(name):
    c = name[1]
    return {"a": "st_atime_ns", "c": "st_ctime_ns", "m": "st_mtime_ns"}[c]


def _timewindow(attr, kind, ref_ns, window):
    def f(p, s, d):
        delta = (getattr(s, attr) - ref_ns) / 1e9
        if kind == "gt":
            return delta > 0.0
        if kind == "lt":
            return delta < 0.0
        return 0.0 < delta <= window
    return f


def _relative(arg, origin_ns, unit):
    kind, rest = get_comp(arg)
    kind = {"gt": "lt", "lt": "gt", "eq": "eq"}[kind]
    v = _parse_float(rest)
    if v is None:
        return None
    ref = origin_ns - int(round(v * unit * NS))
    return kind, ref


def p_xtime(ps, name):
    a = ps.arg(name)
    origin = G.now_ns - DAYSECS * NS
    k0, _ = get_comp(a)
    if k0 == "lt":
        origin += (DAYSECS - 1) * NS
    r = _relative(a, origin, DAYSECS)
    if r is None:
        raise Die("invalid argument `%s' to `%s'" % (a, name))
    return _timewindow(_time_attr(name), r[0], r[1], DAYSECS)


def p_xmin(ps, name):
    a = ps.arg(name)
    r = _relative(a, G.now_ns, 60)
    if r is None:
        raise Die("invalid argument `%s' to `%s'" % (a, name))
    return _timewindow(_time_attr(name), r[0], r[1], 60)


def p_newer(ps, name):
    a = ps.arg(name)
    try:
        rst = os.lstat(os.fsencode(a))
    except OSError as e:
        raise Die("%s: %s" % (qname(a), e.strerror))
    ref = rst.st_mtime_ns
    attr = {"-newer": "st_mtime_ns", "-anewer": "st_atime_ns", "-cnewer": "st_ctime_ns"}[name]
    return lambda p, s, d: getattr(s, attr) > ref


def p_print(ps, name):
    ps.has_action = True

    def f(p, s, d):
        write(p + b"\n")
        return True
    return f


def p_print0(ps, name):
    ps.has_action = True

    def f(p, s, d):
        write(p + b"\0")
        return True
    return f


def p_printf(ps, name):
    a = os.fsencode(ps.arg(name))
    ps.has_action = True
    segs = compile_printf(a)

    def f(p, s, d):
        run_printf(segs, p, s, d)
        return True
    return f


def p_prune(ps, name):
    def f(p, s, d):
        if not G.depth_first and stat.S_ISDIR(s.st_mode):
            G.prune = True
        return True
    return f


def p_quit(ps, name):
    def f(p, s, d):
        raise Quit()
    return f


PRIMARIES = {
    "-true": p_true, "-false": p_false,
    "-depth": p_depth, "-d": p_depth,
    "-maxdepth": p_maxmin, "-mindepth": p_maxmin,
    "-regextype": p_regextype,
    "-noleaf": p_noop, "-xdev": p_noop, "-mount": p_noop,
    "-ignore_readdir_race": p_noop, "-noignore_readdir_race": p_noop,
    "-warn": p_noop, "-nowarn": p_noop,
    "-name": p_name, "-iname": p_name,
    "-path": p_path, "-ipath": p_path, "-wholename": p_path, "-iwholename": p_path,
    "-lname": p_lname, "-ilname": p_lname,
    "-regex": p_regex, "-iregex": p_regex,
    "-type": p_type, "-size": p_size, "-links": p_links, "-empty": p_empty,
    "-perm": p_perm,
    "-mtime": p_xtime, "-atime": p_xtime, "-ctime": p_xtime,
    "-mmin": p_xmin, "-amin": p_xmin, "-cmin": p_xmin,
    "-newer": p_newer, "-anewer": p_newer, "-cnewer": p_newer,
    "-print": p_print, "-print0": p_print0, "-printf": p_printf,
    "-prune": p_prune, "-quit": p_quit,
}


# ---------------------------------------------------------------------------
# Traversal

def child_path(parent, name):
    if parent.endswith(b"/"):
        return parent + name
    return parent + b"/" + name


def descend(path, depth):
    try:
        with os.scandir(path) as it:
            names = [e.name for e in it]
    except OSError as e:
        warn("%s: %s" % (qname(path), e.strerror))
        G.status = 1
        return
    for name in names:
        cp = child_path(path, name)
        try:
            cst = os.lstat(cp)
        except OSError as e:
            warn("%s: %s" % (qname(cp), e.strerror))
            G.status = 1
            continue
        visit(cp, cst, depth + 1)


def visit(path, st, depth):
    isdir = stat.S_ISDIR(st.st_mode)
    maxd = G.maxdepth
    can_descend = isdir and (maxd is None or depth < maxd)
    if not G.depth_first:
        G.prune = False
        if depth >= G.mindepth:
            G.expr(path, st, depth)
        if can_descend and not G.prune:
            descend(path, depth)
    else:
        if can_descend:
            descend(path, depth)
        if depth >= G.mindepth:
            G.expr(path, st, depth)


def norm_start(p):
    n = len(p)
    if n > 2 and p[n - 1] == 47:
        while n > 1 and p[n - 2] == 47:
            n -= 1
    return p[:n]


def run_start(arg):
    G.start_len = len(arg)
    path = norm_start(arg)
    G.start_path = path
    try:
        st = os.lstat(path)
    except OSError as e:
        warn("%s: %s" % (qname(arg), e.strerror))
        G.status = 1
        return
    visit(path, st, 0)


def looks_like_expression(a):
    if a.startswith("-") and len(a) > 1:
        return True
    if a in ("(", "!"):
        return True
    return False


def main(argv):
    G.now_ns = time.time_ns()
    G.out = sys.stdout.buffer
    sys.setrecursionlimit(100000)
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--":
            i += 1
            break
        if a in ("-P", "-H", "-L"):
            i += 1
            continue
        if a.startswith("-O") and len(a) > 2:
            i += 1
            continue
        if a == "-D":
            i += 2
            continue
        break
    starts = []
    while i < len(argv) and not looks_like_expression(argv[i]):
        starts.append(argv[i])
        i += 1
    exprtoks = argv[i:]
    try:
        ps = Parser(exprtoks)
        e = ps.parse()
    except Die as ex:
        warn(str(ex))
        return 1
    if e is None:
        e = p_print(ps, "-print")
    elif not ps.has_action:
        pr = p_print(ps, "-print")
        e = (lambda a, b: lambda p, s, d: a(p, s, d) and b(p, s, d))(e, pr)
    G.expr = e
    if not starts:
        starts = ["."]
    try:
        for s in starts:
            run_start(os.fsencode(s))
    except Quit:
        pass
    except Die as ex:
        warn(str(ex))
        G.status = 1
    try:
        G.out.flush()
    except BrokenPipeError:
        pass
    return G.status


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
