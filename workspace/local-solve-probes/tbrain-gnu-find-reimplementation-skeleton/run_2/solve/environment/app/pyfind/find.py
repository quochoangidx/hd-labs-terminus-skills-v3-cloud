"""pyfind: a GNU find 4.9.0 replacement in pure Python.

Usage: python3 /app/pyfind/find.py [starting-point...] [expression]

Internally every file name and pattern is handled as a latin-1 decoded
``str`` so that each character corresponds to exactly one byte, which is
how GNU find behaves under LC_ALL=C.
"""

import os
import re
import stat
import sys
import time

PROG = "find"


class FindError(Exception):
    """A fatal error detected while parsing the command line."""


def b2s(b):
    return b.decode("latin-1")


def s2b(s):
    return s.encode("latin-1")


def arg2s(a):
    return os.fsencode(a).decode("latin-1")


def err(msg):
    try:
        sys.stdout.flush()
    except Exception:
        pass
    sys.stderr.buffer.write(s2b(PROG + ": " + msg + "\n"))
    sys.stderr.flush()


def quote(s):
    return "'" + s + "'"


# ---------------------------------------------------------------------------
# glibc fnmatch port (flags: none, or FNM_CASEFOLD)
# ---------------------------------------------------------------------------

_CLASS_TESTS = {
    "alnum": lambda c: c.isascii() and c.isalnum(),
    "alpha": lambda c: c.isascii() and c.isalpha(),
    "blank": lambda c: c in " \t",
    "cntrl": lambda c: ord(c) < 32 or ord(c) == 127,
    "digit": lambda c: "0" <= c <= "9",
    "graph": lambda c: 33 <= ord(c) <= 126,
    "lower": lambda c: "a" <= c <= "z",
    "print": lambda c: 32 <= ord(c) <= 126,
    "punct": lambda c: 33 <= ord(c) <= 126 and not c.isalnum(),
    "space": lambda c: c in " \t\n\r\f\v",
    "upper": lambda c: "A" <= c <= "Z",
    "xdigit": lambda c: c in "0123456789abcdefABCDEF",
}

CHAR_CLASS_MAX_LENGTH = 256


def _fold_id(c):
    return c


def _fold_lower(c):
    if "A" <= c <= "Z":
        return chr(ord(c) + 32)
    return c


def fnmatch(pat, s, casefold=False):
    F = _fold_lower if casefold else _fold_id
    return _fnm(pat, 0, s, 0, F)


def _fnm(pat, p, s, n, F):
    L = len(pat)
    E = len(s)

    def at(i):
        return pat[i] if i < L else "\0"

    while p < L:
        c = F(pat[p])
        p += 1
        if c == "?":
            if n == E:
                return False
        elif c == "\\":
            c = at(p)
            p += 1
            if c == "\0":
                return False
            c = F(c)
            if n == E or F(s[n]) != c:
                return False
        elif c == "*":
            c = at(p)
            p += 1
            while c == "?" or c == "*":
                if c == "?":
                    if n == E:
                        return False
                    n += 1
                c = at(p)
                p += 1
            if c == "\0":
                return True
            if c == "[":
                p -= 1
                while n < E:
                    if _fnm(pat, p, s, n, F):
                        return True
                    n += 1
            else:
                if c == "\\":
                    c = at(p)
                c = F(c)
                p -= 1
                while n < E:
                    if F(s[n]) == c and _fnm(pat, p, s, n, F):
                        return True
                    n += 1
            return False
        elif c == "[":
            res = _bracket(pat, p, s, n, F, at)
            if res is None:
                return False
            kind, p2 = res
            if kind == "literal":
                # unterminated: treat '[' as normal character
                if n == E or F(s[n]) != "[":
                    return False
            elif kind == "nomatch":
                return False
            else:
                p = p2
        else:
            if n == E or c != F(s[n]):
                return False
        n += 1
    return n == E


def _bracket(pat, p, s, n, F, at):
    """Returns None (no match of whole pattern), ('literal', _) when the
    bracket is unterminated, ('nomatch', _) or ('ok', newp)."""
    E = len(s)
    if n == E:
        return None
    nt = at(p) == "!" or at(p) == "^"
    if nt:
        p += 1
    fn = F(s[n])
    c = at(p)
    p += 1
    matched = False
    while True:
        goto_normal = False
        if c == "\\":
            if at(p) == "\0":
                return None
            c = F(at(p))
            p += 1
            goto_normal = True
        elif c == "[" and at(p) == ":":
            startp = p
            name = ""
            is_class = True
            while True:
                if len(name) == CHAR_CLASS_MAX_LENGTH:
                    return None
                p += 1
                c = at(p)
                if c == ":" and at(p + 1) == "]":
                    p += 2
                    break
                if c < "a" or c >= "z":
                    p = startp
                    c = "["
                    is_class = False
                    break
                name += c
            if is_class:
                test = _CLASS_TESTS.get(name)
                if test is None:
                    return None
                if test(s[n]):
                    matched = True
                    break
                c = at(p)
                p += 1
                if c == "]":
                    break
                continue
            goto_normal = True
        elif c == "\0":
            return ("literal", None)
        else:
            c = F(c)
            goto_normal = True
        if goto_normal:
            is_range = at(p) == "-" and at(p + 1) != "\0" and at(p + 1) != "]"
            if not is_range and c == fn:
                matched = True
                break
            cold = c
            c = at(p)
            p += 1
            if c == "-" and at(p) != "]":
                cend = at(p)
                p += 1
                if cend == "\\":
                    cend = at(p)
                    p += 1
                if cend == "\0":
                    return None
                cend = F(cend)
                if cold <= fn <= cend:
                    matched = True
                    break
                c = at(p)
                p += 1
        if c == "]":
            break
    if not matched:
        if not nt:
            return ("nomatch", None)
        return ("ok", p)
    # skip the rest of the bracket
    while True:
        c = at(p)
        p += 1
        if c == "\0":
            return ("literal", None)
        if c == "\\":
            if at(p) == "\0":
                return None
            p += 1
        elif c == "[" and at(p) == ":":
            c1 = 0
            startp = p
            bad = False
            while True:
                p += 1
                c = at(p)
                c1 += 1
                if c1 == CHAR_CLASS_MAX_LENGTH:
                    return None
                if at(p) == ":" and at(p + 1) == "]":
                    break
                if c < "a" or c >= "z":
                    p = startp
                    bad = True
                    break
            if bad:
                continue
            p += 2
            c = at(p)
            p += 1
        elif c == "[" and at(p) == "=":
            p += 1
            c = at(p)
            if c == "\0":
                return None
            p += 1
            c = at(p)
            if c != "=" or at(p + 1) != "]":
                return None
            p += 2
            c = at(p)
            p += 1
        elif c == "[" and at(p) == ".":
            while True:
                p += 1
                c = at(p)
                if c == "\0":
                    return None
                if c == "." and at(p + 1) == "]":
                    break
            p += 2
            c = at(p)
            p += 1
        if c == "]":
            break
    if nt:
        return ("nomatch", None)
    return ("ok", p)


# ---------------------------------------------------------------------------
# GNU regex -> Python re translation
# ---------------------------------------------------------------------------

RE_DUP_MAX = 0x7FFF


class RegexError(Exception):
    pass


SYNTAXES = {
    "emacs": dict(bk_parens=True, bk_vbar=True, intervals=False, bk_braces=True,
                  bk_plus_qm=False, indep_anchors=False, indep_ops=False,
                  invalid_ops=False, invalid_dup=False, char_classes=False,
                  no_empty_ranges=False, unmatched_rparen_ord=False),
    "posix-basic": dict(bk_parens=True, bk_vbar=True, intervals=True, bk_braces=True,
                        bk_plus_qm=True, indep_anchors=False, indep_ops=False,
                        invalid_ops=False, invalid_dup=True, char_classes=True,
                        no_empty_ranges=True, unmatched_rparen_ord=False),
    "posix-extended": dict(bk_parens=False, bk_vbar=False, intervals=True, bk_braces=False,
                           bk_plus_qm=False, indep_anchors=True, indep_ops=True,
                           invalid_ops=True, invalid_dup=False, char_classes=True,
                           no_empty_ranges=True, unmatched_rparen_ord=True),
}

SYNTAXES["findutils-default"] = SYNTAXES["emacs"]
SYNTAXES["posix-egrep"] = SYNTAXES["posix-extended"]
SYNTAXES["egrep"] = SYNTAXES["posix-extended"]
SYNTAXES["posix-awk"] = SYNTAXES["posix-extended"]
SYNTAXES["awk"] = SYNTAXES["posix-extended"]
SYNTAXES["gnu-awk"] = SYNTAXES["posix-extended"]
SYNTAXES["ed"] = SYNTAXES["posix-basic"]
SYNTAXES["sed"] = SYNTAXES["posix-basic"]
SYNTAXES["grep"] = SYNTAXES["posix-basic"]
SYNTAXES["posix-minimal-basic"] = SYNTAXES["posix-basic"]

_RX_CLASS_SETS = {}
for _name, _t in _CLASS_TESTS.items():
    _RX_CLASS_SETS[_name] = frozenset(i for i in range(256) if _t(chr(i)))


class _Tok:
    __slots__ = ("type", "c", "val", "len")

    def __init__(self, type_, c="", val=None, length=1):
        self.type = type_
        self.c = c
        self.val = val
        self.len = length


class RegexTranslator:
    def __init__(self, pattern, syntax, icase):
        self.pat = pattern
        self.sx = SYNTAXES[syntax]
        self.icase = icase
        self.pos = 0
        self.ngroups = 0
        self.completed = set()
        self.tok = None

    # -- tokenizer ---------------------------------------------------------
    def peek(self, pos, caret_here=False):
        pat = self.pat
        sx = self.sx
        if pos >= len(pat):
            return _Tok("END", "", None, 0)
        c = pat[pos]
        if c == "\\":
            if pos + 1 >= len(pat):
                return _Tok("BACKSLASH", "\\", None, 1)
            c2 = pat[pos + 1]
            t = _Tok("CHAR", c2, None, 2)
            if c2 == "|":
                if sx["bk_vbar"]:
                    t.type = "ALT"
            elif "1" <= c2 <= "9":
                t.type = "BACKREF"
                t.val = ord(c2) - ord("0")
            elif c2 == "<":
                t.type, t.val = "ANCHOR", "wordbeg"
            elif c2 == ">":
                t.type, t.val = "ANCHOR", "wordend"
            elif c2 == "b":
                t.type, t.val = "ANCHOR", "wordbound"
            elif c2 == "B":
                t.type, t.val = "ANCHOR", "notwordbound"
            elif c2 == "w":
                t.type, t.val = "CLASSOP", r"\w"
            elif c2 == "W":
                t.type, t.val = "CLASSOP", r"\W"
            elif c2 == "s":
                t.type, t.val = "CLASSOP", r"\s"
            elif c2 == "S":
                t.type, t.val = "CLASSOP", r"\S"
            elif c2 == "`":
                t.type, t.val = "ANCHOR", "bufbeg"
            elif c2 == "'":
                t.type, t.val = "ANCHOR", "bufend"
            elif c2 == "(":
                if sx["bk_parens"]:
                    t.type = "OPEN"
            elif c2 == ")":
                if sx["bk_parens"]:
                    t.type = "CLOSE"
            elif c2 == "+":
                if sx["bk_plus_qm"]:
                    t.type = "PLUS"
            elif c2 == "?":
                if sx["bk_plus_qm"]:
                    t.type = "QUESTION"
            elif c2 == "{":
                if sx["intervals"] and sx["bk_braces"]:
                    t.type = "OPEN_DUP"
            elif c2 == "}":
                if sx["intervals"] and sx["bk_braces"]:
                    t.type = "CLOSE_DUP"
            return t
        t = _Tok("CHAR", c, None, 1)
        if c == "|":
            if not sx["bk_vbar"]:
                t.type = "ALT"
        elif c == "*":
            t.type = "STAR"
        elif c == "+":
            if not sx["bk_plus_qm"]:
                t.type = "PLUS"
        elif c == "?":
            if not sx["bk_plus_qm"]:
                t.type = "QUESTION"
        elif c == "{":
            if sx["intervals"] and not sx["bk_braces"]:
                t.type = "OPEN_DUP"
        elif c == "}":
            if sx["intervals"] and not sx["bk_braces"]:
                t.type = "CLOSE_DUP"
        elif c == "(":
            if not sx["bk_parens"]:
                t.type = "OPEN"
        elif c == ")":
            if not sx["bk_parens"]:
                t.type = "CLOSE"
        elif c == "[":
            t.type = "BRACKET"
        elif c == ".":
            t.type = "PERIOD"
        elif c == "^":
            if not (sx["indep_anchors"] or caret_here) and pos != 0:
                return t
            t.type, t.val = "ANCHOR", "^"
        elif c == "$":
            if not sx["indep_anchors"] and pos + 1 != len(self.pat):
                nxt = self.peek(pos + 1)
                if nxt.type not in ("ALT", "CLOSE"):
                    return t
            t.type, t.val = "ANCHOR", "$"
        return t

    def fetch(self, caret_here=False):
        t = self.peek(self.pos, caret_here)
        self.pos += t.len
        self.tok = t
        return t

    # -- parser ------------------------------------------------------------
    def translate(self):
        self.fetch(caret_here=False)
        tree = self.parse_reg_exp(0)
        if self.tok.type != "END":
            raise RegexError("Unmatched ) or \\)")
        return tree

    def parse_reg_exp(self, nest):
        branches = [self.parse_branch(nest)]
        while self.tok.type == "ALT":
            self.fetch(caret_here=True)
            if self.tok.type not in ("ALT", "END") and not (nest and self.tok.type == "CLOSE"):
                branches.append(self.parse_branch(nest))
            else:
                branches.append("")
        if len(branches) == 1:
            return branches[0]
        return "(?:" + "|".join(branches) + ")"

    def parse_branch(self, nest):
        out = []
        while self.tok.type not in ("ALT", "END") and not (nest and self.tok.type == "CLOSE"):
            out.append(self.parse_expression(nest))
        return "".join(out)

    def parse_expression(self, nest):
        sx = self.sx
        t = self.tok
        typ = t.type
        if typ == "CHAR":
            tree = self.lit(t.c)
        elif typ == "PERIOD":
            tree = "(?s:.)"
        elif typ == "BRACKET":
            tree = self.parse_bracket()
        elif typ == "BACKREF":
            if t.val not in self.completed:
                raise RegexError("Invalid back reference")
            tree = "(?:\\%d)" % t.val
        elif typ == "OPEN":
            self.ngroups += 1
            gno = self.ngroups
            self.fetch(caret_here=True)
            if self.tok.type == "CLOSE":
                inner = ""
            else:
                inner = self.parse_reg_exp(nest + 1)
                if self.tok.type != "CLOSE":
                    raise RegexError("Unmatched ( or \\(")
            self.completed.add(gno)
            tree = "(" + inner + ")"
        elif typ == "CLASSOP":
            tree = t.val
        elif typ == "ANCHOR":
            a = t.val
            tree = {
                "^": "^",
                "$": "$",
                "wordbeg": r"\b(?=\w)",
                "wordend": r"\b(?<=\w)",
                "wordbound": r"\b",
                "notwordbound": r"\B",
                "bufbeg": r"\A",
                "bufend": r"\Z",
            }[a]
            self.fetch()
            return tree
        elif typ == "OPEN_DUP":
            if sx["invalid_dup"]:
                raise RegexError("Invalid preceding regular expression")
            if sx["invalid_ops"]:
                raise RegexError("Invalid preceding regular expression")
            tree = self.lit(t.c)
        elif typ in ("STAR", "PLUS", "QUESTION"):
            if sx["invalid_ops"] and not sx["invalid_dup"]:
                raise RegexError("Invalid preceding regular expression")
            if sx["indep_ops"]:
                self.fetch()
                return self.parse_expression(nest)
            tree = self.lit(t.c)
        elif typ == "CLOSE":
            if not sx["unmatched_rparen_ord"]:
                raise RegexError("Unmatched ) or \\)")
            tree = self.lit(t.c)
        elif typ == "CLOSE_DUP":
            tree = self.lit(t.c)
        elif typ == "BACKSLASH":
            raise RegexError("Trailing backslash")
        elif typ in ("END", "ALT"):
            return ""
        else:
            raise RegexError("internal")
        self.fetch()
        while self.tok.type in ("STAR", "PLUS", "QUESTION", "OPEN_DUP"):
            tree = self.parse_dup(tree)
            if sx["invalid_dup"] and self.tok.type in ("STAR", "OPEN_DUP"):
                raise RegexError("Invalid preceding regular expression")
        return tree

    def fetch_number(self):
        num = -1
        while True:
            t = self.fetch()
            c = t.c
            if t.type == "END":
                return -2
            if t.type == "CLOSE_DUP" or c == ",":
                break
            if t.type != "CHAR" or c < "0" or c > "9" or num == -2:
                num = -2
            elif num == -1:
                num = ord(c) - 48
            else:
                num = min(RE_DUP_MAX + 1, num * 10 + ord(c) - 48)
        return num

    def parse_dup(self, elem):
        t = self.tok
        if t.type == "OPEN_DUP":
            end = 0
            start = self.fetch_number()
            if start == -1:
                if self.tok.type == "CHAR" and self.tok.c == ",":
                    start = 0
                else:
                    raise RegexError("Invalid content of \\{\\}")
            if start != -2:
                if self.tok.type == "CLOSE_DUP":
                    end = start
                elif self.tok.type == "CHAR" and self.tok.c == ",":
                    end = self.fetch_number()
                else:
                    end = -2
            if start == -2 or end == -2:
                if self.tok.type == "END":
                    raise RegexError("Unmatched \\{")
                raise RegexError("Invalid content of \\{\\}")
            if (end != -1 and start > end) or self.tok.type != "CLOSE_DUP":
                raise RegexError("Invalid content of \\{\\}")
            if RE_DUP_MAX < (start if end == -1 else end):
                raise RegexError("Regular expression too big")
            if end == -1:
                q = "{%d,}" % start
            else:
                q = "{%d,%d}" % (start, end)
        elif t.type == "STAR":
            q = "*"
        elif t.type == "PLUS":
            q = "+"
        else:
            q = "?"
        self.fetch()
        return "(?:" + elem + ")" + q

    def lit(self, c):
        return re.escape(c)

    # -- bracket expressions -----------------------------------------------
    def peek_bracket(self, pos):
        pat = self.pat
        if pos >= len(pat):
            return ("END", "", 0)
        c = pat[pos]
        if c == "[":
            c2 = pat[pos + 1] if pos + 1 < len(pat) else "\0"
            if c2 == ".":
                return ("OPEN_COLL", c2, 2)
            if c2 == "=":
                return ("OPEN_EQUIV", c2, 2)
            if c2 == ":" and self.sx["char_classes"]:
                return ("OPEN_CLASS", c2, 2)
            return ("CHAR", c, 1)
        if c == "-":
            return ("RANGE", c, 1)
        if c == "]":
            return ("CLOSE", c, 1)
        if c == "^":
            return ("NONMATCH", c, 1)
        return ("CHAR", c, 1)

    def parse_bracket_symbol(self, tok):
        typ, delim, _ = tok
        pat = self.pat
        if self.pos >= len(pat):
            raise RegexError("Unmatched [")
        name = ""
        while True:
            if len(name) >= 32:
                raise RegexError("Unmatched [")
            ch = pat[self.pos]
            self.pos += 1
            if self.pos >= len(pat):
                raise RegexError("Unmatched [")
            if ch == delim and pat[self.pos] == "]":
                break
            name += ch
        self.pos += 1
        if typ == "OPEN_COLL":
            return ("COLL", name)
        if typ == "OPEN_EQUIV":
            return ("EQUIV", name)
        return ("CLASS", name)

    def parse_bracket_element(self, tok, accept_hyphen):
        typ, c, ln = tok
        self.pos += ln
        if typ in ("OPEN_COLL", "OPEN_EQUIV", "OPEN_CLASS"):
            return self.parse_bracket_symbol(tok)
        if typ == "RANGE" and not accept_hyphen:
            t2 = self.peek_bracket(self.pos)
            if t2[0] != "CLOSE":
                raise RegexError("Invalid range end")
        return ("SB", c)

    def _elem_char(self, elem):
        kind, v = elem
        if kind == "SB":
            ch = v
        elif kind == "COLL":
            if len(v) != 1:
                raise RegexError("Invalid collation character")
            ch = v
        else:
            raise RegexError("Invalid range end")
        if self.icase:
            ch = _fold_lower(ch)
        return ord(ch)

    def parse_bracket(self):
        members = set()
        non_match = False
        tok = self.peek_bracket(self.pos)
        if tok[0] == "NONMATCH":
            non_match = True
            self.pos += tok[2]
            tok = self.peek_bracket(self.pos)
            if tok[0] == "END":
                raise RegexError("Unmatched [")
        if tok[0] == "CLOSE":
            tok = ("CHAR", tok[1], tok[2])
        first = True
        while True:
            if tok[0] == "END":
                raise RegexError("Unmatched [")
            is_range = False
            start = self.parse_bracket_element(tok, first)
            first = False
            tok = self.peek_bracket(self.pos)
            tok2 = None
            if start[0] not in ("CLASS", "EQUIV"):
                if tok[0] == "END":
                    raise RegexError("Unmatched [")
                if tok[0] == "RANGE":
                    self.pos += tok[2]
                    tok2 = self.peek_bracket(self.pos)
                    if tok2[0] == "END":
                        raise RegexError("Unmatched [")
                    if tok2[0] == "CLOSE":
                        self.pos -= tok[2]
                        tok = ("CHAR", tok[1], tok[2])
                    else:
                        is_range = True
            if is_range:
                end = self.parse_bracket_element(tok2, True)
                tok = self.peek_bracket(self.pos)
                if start[0] in ("CLASS", "EQUIV") or end[0] in ("CLASS", "EQUIV"):
                    raise RegexError("Invalid range end")
                lo = self._elem_char(start)
                hi = self._elem_char(end)
                if lo > hi:
                    if self.sx["no_empty_ranges"]:
                        raise RegexError("Invalid range end")
                else:
                    members.update(range(lo, hi + 1))
            else:
                kind, v = start
                if kind == "SB":
                    members.add(ord(v))
                elif kind == "COLL":
                    if len(v) != 1:
                        raise RegexError("Invalid collation character")
                    members.add(ord(v))
                elif kind == "EQUIV":
                    if len(v) != 1:
                        raise RegexError("Invalid collation character")
                    members.add(ord(v))
                else:
                    name = v
                    if self.icase and name in ("upper", "lower"):
                        name = "alpha"
                    cs = _RX_CLASS_SETS.get(name)
                    if cs is None:
                        raise RegexError("Invalid character class name")
                    members.update(cs)
            if tok[0] == "END":
                raise RegexError("Unmatched [")
            if tok[0] == "CLOSE":
                self.pos += tok[2]
                break
        if not members:
            return "(?s:.)" if non_match else "(?!)"
        body = "".join("\\x%02x" % m for m in sorted(members))
        return ("[^" if non_match else "[") + body + "]"


def compile_regex(pattern, syntax, icase):
    tr = RegexTranslator(pattern, syntax, icase)
    py = tr.translate()
    flags = re.ASCII | re.MULTILINE
    if icase:
        flags |= re.IGNORECASE
    try:
        return re.compile(py, flags)
    except re.error as e:
        raise RegexError(str(e))


# ---------------------------------------------------------------------------
# file mode helpers
# ---------------------------------------------------------------------------

def mode_compile(s):
    if s and "0" <= s[0] < "8":
        v = 0
        for ch in s:
            if not ("0" <= ch < "8"):
                return None
            v = v * 8 + ord(ch) - 48
            if v > 0o7777:
                return None
        mentioned = ((v & 0o6000) | 0o1777) if len(s) < 5 else 0o7777
        return [("=", "ORD", 0o7777, v, mentioned)]
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
                affected |= 0o4700
            elif ch == "g":
                affected |= 0o2070
            elif ch == "o":
                affected |= 0o1007
            elif ch == "a":
                affected |= 0o7777
            elif ch in "=+-":
                break
            else:
                return None
            i += 1
        while True:
            op = s[i]
            i += 1
            if i < n and s[i] in "ugo":
                value = {"u": 0o700, "g": 0o070, "o": 0o007}[s[i]]
                flag = "COPY"
                i += 1
            else:
                value = 0
                flag = "ORD"
                while i < n and s[i] in "rwxXst":
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
                        value |= 0o6000
                    elif ch == "t":
                        value |= 0o1000
                    i += 1
            mentioned = (affected & value) if affected else value
            changes.append((op, flag, affected, value, mentioned))
            if not (i < n and s[i] in "=+-"):
                break
        if i < n and s[i] == ",":
            i += 1
            continue
        break
    if i != n:
        return None
    return changes


def mode_adjust(oldmode, is_dir, umask, changes):
    newmode = oldmode & 0o7777
    for op, flag, affected, value, mentioned in changes:
        omit = (0o6000 if is_dir else 0) & ~mentioned
        if flag == "COPY":
            value &= newmode
            value |= ((0o444 if value & 0o444 else 0)
                      | (0o222 if value & 0o222 else 0)
                      | (0o111 if value & 0o111 else 0))
        elif flag == "X":
            if (newmode & 0o111) or is_dir:
                value |= 0o111
        value &= (affected if affected else ~umask) & ~omit
        if op == "=":
            preserved = (~affected if affected else 0) | omit
            newmode = (newmode & preserved) | value
        elif op == "+":
            newmode |= value
        else:
            newmode &= ~value
        newmode &= 0o7777
    return newmode


def type_char(mode):
    if stat.S_ISREG(mode):
        return "f"
    if stat.S_ISDIR(mode):
        return "d"
    if stat.S_ISLNK(mode):
        return "l"
    if stat.S_ISCHR(mode):
        return "c"
    if stat.S_ISBLK(mode):
        return "b"
    if stat.S_ISFIFO(mode):
        return "p"
    if stat.S_ISSOCK(mode):
        return "s"
    return "U"


def mode_string(mode):
    t = type_char(mode)
    tc = {"f": "-", "U": "?"}.get(t, t)
    s = [tc]
    for (r, w, x, special, sch) in ((0o400, 0o200, 0o100, 0o4000, "s"),
                                    (0o040, 0o020, 0o010, 0o2000, "s"),
                                    (0o004, 0o002, 0o001, 0o1000, "t")):
        s.append("r" if mode & r else "-")
        s.append("w" if mode & w else "-")
        if mode & special:
            s.append(sch if mode & x else sch.upper())
        else:
            s.append("x" if mode & x else "-")
    return "".join(s)


# ---------------------------------------------------------------------------
# path helpers mirroring gnulib
# ---------------------------------------------------------------------------

def last_component(name):
    i = 0
    while i < len(name) and name[i] == "/":
        i += 1
    base = i
    last_was_slash = False
    for p in range(i, len(name)):
        if name[p] == "/":
            last_was_slash = True
        elif last_was_slash:
            base = p
            last_was_slash = False
    return name[base:]


def base_len(name):
    ln = len(name)
    while 1 < ln and name[ln - 1] == "/":
        ln -= 1
    return ln


def base_name(name):
    base = last_component(name)
    if not base:
        return name[:base_len(name)]
    ln = base_len(base)
    if ln < len(base) and base[ln] == "/":
        ln += 1
    return base[:ln]


def strip_trailing_slashes(name):
    base = last_component(name)
    if not base:
        base = name
        prefix = ""
    else:
        prefix = name[:len(name) - len(base)]
    return prefix + base[:base_len(base)]


# ---------------------------------------------------------------------------
# printf
# ---------------------------------------------------------------------------

def c_format(flags, width, prec, conv, val):
    left = "-" in flags
    zero = width.startswith("0")
    w = int(width) if width else 0
    if conv == "s":
        s = val
        if prec is not None:
            s = s[:prec]
        pad = w - len(s)
        if pad > 0:
            s = s + " " * pad if left else " " * pad + s
        return s
    v = int(val)
    neg = v < 0
    av = -v if neg else v
    if conv == "d":
        digits = str(av)
        sign = "-" if neg else ("+" if "+" in flags else (" " if " " in flags else ""))
    else:
        digits = "%o" % av
        sign = ""
    if prec is not None:
        if prec == 0 and av == 0:
            digits = ""
        if len(digits) < prec:
            digits = "0" * (prec - len(digits)) + digits
    if conv == "o" and "#" in flags and not digits.startswith("0"):
        digits = "0" + digits
    body = sign + digits
    pad = w - len(body)
    if pad > 0:
        if left:
            body = body + " " * pad
        elif zero and prec is None:
            body = sign + "0" * pad + digits
        else:
            body = " " * pad + body
    return body


def parse_printf(fmt):
    """Returns a list of segments: ('lit', str), ('dir', flags, width, prec, ch),
    ('stop',)."""
    segs = []
    lit = []
    i = 0
    n = len(fmt)
    while i < n:
        c = fmt[i]
        if c == "\\":
            if i + 1 < n and "0" <= fmt[i + 1] <= "7":
                v = 0
                k = 0
                j = i + 1
                while k < 3 and j < n and "0" <= fmt[j] <= "7":
                    v = v * 8 + ord(fmt[j]) - 48
                    j += 1
                    k += 1
                lit.append(chr(v & 0xFF))
                i = j
                continue
            nc = fmt[i + 1] if i + 1 < n else ""
            m = {"a": "\a", "b": "\b", "f": "\f", "n": "\n", "r": "\r",
                 "t": "\t", "v": "\v", "\\": "\\"}
            if nc in m and nc:
                lit.append(m[nc])
                i += 2
                continue
            if nc == "c":
                if lit:
                    segs.append(("lit", "".join(lit)))
                    lit = []
                segs.append(("stop",))
                return segs
            if nc == "":
                err("warning: escape `\\' followed by nothing at all")
                lit.append("\\")
                i += 1
                continue
            err("warning: unrecognized escape `\\%s'" % nc)
            lit.append("\\" + nc)
            i += 2
            continue
        if c == "%":
            if i + 1 >= n:
                raise FindError("error: % at end of format string")
            if fmt[i + 1] == "%":
                lit.append("%")
                i += 2
                continue
            j = i + 1
            while j < n and fmt[j] in "-+ #":
                j += 1
            flags = fmt[i + 1:j]
            k = j
            while k < n and fmt[k].isdigit() and fmt[k].isascii():
                k += 1
            width = fmt[j:k]
            prec = None
            if k < n and fmt[k] == ".":
                k2 = k + 1
                while k2 < n and fmt[k2].isdigit() and fmt[k2].isascii():
                    k2 += 1
                prec = int(fmt[k + 1:k2]) if k2 > k + 1 else 0
                k = k2
            ch = fmt[k] if k < n else ""
            if ch == "":
                raise FindError("error: % at end of format string")
            if ch in "abcdDfFgGhHiklmMnpPsStuUyYZ":
                if lit:
                    segs.append(("lit", "".join(lit)))
                    lit = []
                segs.append(("dir", flags, width, prec, ch))
                i = k + 1
                continue
            if ch in "ABCT" and k + 1 < n:
                if lit:
                    segs.append(("lit", "".join(lit)))
                    lit = []
                segs.append(("tdir", flags, width, prec, ch, fmt[k + 1]))
                i = k + 2
                continue
            err("warning: unrecognized format directive `%%%s'" % ch)
            i += 1
            continue
        lit.append(c)
        i += 1
    if lit:
        segs.append(("lit", "".join(lit)))
    return segs


# ---------------------------------------------------------------------------
# expression tree
# ---------------------------------------------------------------------------

class Quit(Exception):
    pass


class Ctx:
    __slots__ = ("path", "st", "depth", "root_arg", "root_len", "prune", "_empty")

    def __init__(self, path, st, depth, root_arg):
        self.path = path
        self.st = st
        self.depth = depth
        self.root_arg = root_arg
        self.prune = False
        self._empty = None


class Node:
    has_action = False

    def ev(self, c):
        raise NotImplementedError


class And(Node):
    def __init__(self, a, b):
        self.a, self.b = a, b

    def ev(self, c):
        return self.a.ev(c) and self.b.ev(c)


class Or(Node):
    def __init__(self, a, b):
        self.a, self.b = a, b

    def ev(self, c):
        return self.a.ev(c) or self.b.ev(c)


class Comma(Node):
    def __init__(self, a, b):
        self.a, self.b = a, b

    def ev(self, c):
        self.a.ev(c)
        return self.b.ev(c)


class Not(Node):
    def __init__(self, a):
        self.a = a

    def ev(self, c):
        return not self.a.ev(c)


class Const(Node):
    def __init__(self, v):
        self.v = v

    def ev(self, c):
        return self.v


class Fn(Node):
    def __init__(self, f):
        self.f = f

    def ev(self, c):
        return self.f(c)


class Finder:
    def __init__(self):
        self.out = bytearray()
        self.maxdepth = -1
        self.mindepth = 0
        self.depth_first = False
        self.regextype = "emacs"
        self.exit_status = 0
        self.start_ns = time.time_ns()
        self.has_action = False

    # -- output ------------------------------------------------------------
    def emit(self, s):
        self.out += s2b(s)
        if len(self.out) > 65536:
            self.flush()

    def flush(self):
        if self.out:
            sys.stdout.buffer.write(bytes(self.out))
            self.out = bytearray()
        sys.stdout.buffer.flush()

    # -- command-line parsing ----------------------------------------------
    def parse(self, args):
        self.args = args
        self.i = 0
        if not args:
            return None
        e = self.parse_comma()
        if self.i < len(args):
            a = args[self.i]
            if a == ")":
                raise FindError("invalid expression; you have too many ')'")
            raise FindError("invalid expression")
        return e

    def peek(self):
        return self.args[self.i] if self.i < len(self.args) else None

    def parse_comma(self):
        left = self.parse_or()
        while self.peek() == ",":
            self.i += 1
            if self.peek() is None or self.peek() in (")", ",", "-o", "-or", "-a", "-and"):
                raise FindError("invalid expression; expected expression after ','")
            right = self.parse_or()
            left = Comma(left, right)
        return left

    def parse_or(self):
        left = self.parse_and()
        while self.peek() in ("-o", "-or"):
            op = self.peek()
            self.i += 1
            if self.peek() is None or self.peek() in (")", ",", "-o", "-or", "-a", "-and"):
                raise FindError("invalid expression; you have used a binary operator '%s' with nothing after it." % op)
            right = self.parse_and()
            left = Or(left, right)
        return left

    def parse_and(self):
        left = self.parse_unary()
        while True:
            t = self.peek()
            if t is None or t in (")", ",", "-o", "-or"):
                return left
            if t in ("-a", "-and"):
                self.i += 1
                t2 = self.peek()
                if t2 is None or t2 in (")", ",", "-o", "-or", "-a", "-and"):
                    raise FindError("invalid expression; you have used a binary operator '%s' with nothing after it." % t)
            right = self.parse_unary()
            left = And(left, right)

    def parse_unary(self):
        t = self.peek()
        if t is None:
            raise FindError("invalid expression")
        if t in ("!", "-not"):
            self.i += 1
            t2 = self.peek()
            if t2 is None or t2 in (")", ",", "-o", "-or", "-a", "-and"):
                raise FindError("invalid expression; expected an expression after '%s'" % t)
            return Not(self.parse_unary())
        if t == "(":
            self.i += 1
            if self.peek() == ")":
                raise FindError("invalid expression; empty parentheses are not allowed.")
            if self.peek() is None:
                raise FindError("invalid expression; I was expecting to find a ')' somewhere but did not see one.")
            e = self.parse_comma()
            if self.peek() != ")":
                raise FindError("invalid expression; I was expecting to find a ')' somewhere but did not see one.")
            self.i += 1
            return e
        if t in (")",):
            raise FindError("invalid expression; you have too many ')'")
        if t in ("-a", "-and", "-o", "-or", ","):
            raise FindError("invalid expression; you have used a binary operator '%s' with nothing before it." % t)
        self.i += 1
        return self.primary(t)

    def arg(self, name):
        if self.i >= len(self.args):
            raise FindError("missing argument to `%s'" % name)
        a = self.args[self.i]
        self.i += 1
        return a

    def primary(self, t):
        if not t.startswith("-") or t == "-":
            raise FindError("paths must precede expression: `%s'" % t)
        name = t[1:]
        m = getattr(self, "p_" + name.replace("-", "_"), None) if name else None
        if m is None or name in ("",):
            raise FindError("unknown predicate `%s'" % t)
        return m(t)

    # options -------------------------------------------------------------
    def p_depth(self, t):
        self.depth_first = True
        return Const(True)

    def _depth_arg(self, t):
        a = self.arg(t)
        n = 0
        while n < len(a) and "0" <= a[n] <= "9":
            n += 1
        if n == 0 or n != len(a):
            raise FindError("Expected a positive decimal integer argument to %s, but got %s" % (t, quote(a)))
        return int(a)

    def p_maxdepth(self, t):
        self.maxdepth = self._depth_arg(t)
        return Const(True)

    def p_mindepth(self, t):
        self.mindepth = self._depth_arg(t)
        return Const(True)

    def p_regextype(self, t):
        a = self.arg(t)
        if a not in SYNTAXES:
            raise FindError("Unknown regular expression type %s" % quote(a))
        self.regextype = a
        return Const(True)

    # tests -----------------------------------------------------------------
    def p_true(self, t):
        return Const(True)

    def p_false(self, t):
        return Const(False)

    def _name(self, t, casefold):
        pat = self.arg(t)

        def f(c):
            base = strip_trailing_slashes(base_name(c.path))
            return fnmatch(pat, base, casefold)
        return Fn(f)

    def p_name(self, t):
        return self._name(t, False)

    def p_iname(self, t):
        return self._name(t, True)

    def _path(self, t, casefold):
        pat = self.arg(t)
        return Fn(lambda c: fnmatch(pat, c.path, casefold))

    def p_path(self, t):
        return self._path(t, False)

    def p_wholename(self, t):
        return self._path(t, False)

    def p_ipath(self, t):
        return self._path(t, True)

    def p_iwholename(self, t):
        return self._path(t, True)

    def _regex(self, t, icase):
        pat = self.arg(t)
        try:
            rx = compile_regex(pat, self.regextype, icase)
        except RegexError as e:
            raise FindError("%s" % e)
        return Fn(lambda c: rx.fullmatch(c.path) is not None)

    def p_regex(self, t):
        return self._regex(t, False)

    def p_iregex(self, t):
        return self._regex(t, True)

    def p_type(self, t):
        a = self.arg(t)
        if not a:
            raise FindError("Arguments to -type should contain at least one letter")
        types = set()
        i = 0
        while i < len(a):
            ch = a[i]
            if ch not in "bcdpflsD":
                raise FindError("Unknown argument to -type: %s" % ch)
            if ch in types:
                raise FindError("Duplicate file type '%s' in the argument list to -type" % ch)
            types.add(ch)
            i += 1
            if i < len(a):
                if a[i] != ",":
                    raise FindError("Must separate multiple arguments to -type using: ','")
                i += 1
                if i == len(a):
                    raise FindError("Last file type in list argument to -type is missing, i.e., list is ending on: ','")
        return Fn(lambda c: type_char(c.st.st_mode) in types)

    @staticmethod
    def _comp(s):
        if s.startswith("+"):
            return "gt", s[1:]
        if s.startswith("-"):
            return "lt", s[1:]
        return "eq", s

    @staticmethod
    def _uint(s):
        m = re.fullmatch(r"[ \t\n\v\f\r]*\+?([0-9]+)", s)
        if not m:
            return None
        return int(m.group(1))

    @staticmethod
    def _cmp(kind, a, b):
        if kind == "gt":
            return a > b
        if kind == "lt":
            return a < b
        return a == b

    def p_size(self, t):
        a = self.arg(t)
        if not a:
            raise FindError("invalid null argument to -size")
        suf = a[-1]
        units = {"b": 512, "c": 1, "k": 1024, "M": 1048576, "G": 1073741824, "w": 2}
        if suf in units:
            bs = units[suf]
            a2 = a[:-1]
        elif "0" <= suf <= "9":
            bs = 512
            a2 = a
        else:
            raise FindError("invalid -size type `%s'" % suf)
        kind, rest = self._comp(a2)
        num = self._uint(rest)
        if num is None:
            raise FindError("invalid argument `%s' to `-size'" % a)

        def f(c):
            sz = c.st.st_size
            v = sz // bs + (1 if sz % bs else 0)
            return self._cmp(kind, v, num)
        return Fn(f)

    def p_links(self, t):
        a = self.arg(t)
        kind, rest = self._comp(a)
        num = self._uint(rest)
        if num is None:
            raise FindError("invalid argument `%s' to `-links'" % a)
        return Fn(lambda c: self._cmp(kind, c.st.st_nlink, num))

    def p_empty(self, t):
        def f(c):
            mode = c.st.st_mode
            if stat.S_ISREG(mode):
                return c.st.st_size == 0
            if stat.S_ISDIR(mode):
                try:
                    with os.scandir(s2b(c.path)) as it:
                        for _ in it:
                            return False
                    return True
                except OSError as e:
                    err("cannot open %s: %s" % (quote(c.path), e.strerror))
                    self.exit_status = 1
                    return False
            return False
        return Fn(f)

    def p_perm(self, t):
        a = self.arg(t)
        kind = "exact"
        ms = a
        if a.startswith("-"):
            kind = "all"
            ms = a[1:]
        elif a.startswith("/"):
            kind = "any"
            ms = a[1:]
        ch = mode_compile(ms)
        if ch is None:
            raise FindError("invalid mode %s" % quote(a))
        v0 = mode_adjust(0, False, 0, ch)
        v1 = mode_adjust(0, True, 0, ch)

        def f(c):
            mode = c.st.st_mode
            pv = v1 if stat.S_ISDIR(mode) else v0
            if kind == "all":
                return (mode & pv) == pv
            if kind == "any":
                return pv == 0 or (mode & pv) != 0
            return (mode & 0o7777) == pv
        return Fn(f)

    _FLOAT_RE = re.compile(r"[ \t\n\v\f\r]*[+-]?(?:[0-9]+\.?[0-9]*|\.[0-9]+)(?:[eE][+-]?[0-9]+)?")

    def _reltime(self, t, a, origin_ns, unit):
        kind, rest = self._comp(a)
        if not self._FLOAT_RE.fullmatch(rest):
            raise FindError("invalid argument %s to %s" % (quote(a), t))
        val = float(rest)
        # invert the sense of the comparison
        inv = {"gt": "lt", "lt": "gt", "eq": "eq"}[kind]
        ref = origin_ns / 1e9 - val * unit
        return inv, ref

    def p_mtime(self, t):
        a = self.arg(t)
        origin = self.start_ns - 86400 * 10**9
        kind, _ = self._comp(a)
        if kind == "lt":
            origin += 86399 * 10**9
        inv, ref = self._reltime(t, a, origin, 86400.0)
        return Fn(lambda c: self._timewindow(c.st.st_mtime_ns, inv, ref, 86400.0))

    def p_mmin(self, t):
        a = self.arg(t)
        inv, ref = self._reltime(t, a, self.start_ns, 60.0)
        return Fn(lambda c: self._timewindow(c.st.st_mtime_ns, inv, ref, 60.0))

    @staticmethod
    def _timewindow(mt_ns, kind, ref, window):
        delta = mt_ns / 1e9 - ref
        if kind == "gt":
            return delta > 0.0
        if kind == "lt":
            return delta < 0.0
        return 0.0 < delta <= window

    def p_newer(self, t):
        a = self.arg(t)
        try:
            st = os.lstat(s2b(a))
        except OSError as e:
            raise FindError("%s: %s" % (quote(a), e.strerror))
        ref = st.st_mtime_ns
        return Fn(lambda c: c.st.st_mtime_ns > ref)

    # actions ---------------------------------------------------------------
    def p_print(self, t):
        self.has_action = True

        def f(c):
            self.emit(c.path + "\n")
            return True
        return Fn(f)

    def p_print0(self, t):
        self.has_action = True

        def f(c):
            self.emit(c.path + "\0")
            return True
        return Fn(f)

    def p_prune(self, t):
        def f(c):
            if not self.depth_first:
                c.prune = True
            return True
        return Fn(f)

    def p_quit(self, t):
        def f(c):
            raise Quit()
        return Fn(f)

    def p_printf(self, t):
        a = self.arg(t)
        self.has_action = True
        segs = parse_printf(a)
        return Fn(lambda c: self.do_printf(c, segs))

    def do_printf(self, c, segs):
        out = []
        for seg in segs:
            k = seg[0]
            if k == "lit":
                out.append(seg[1])
                continue
            if k == "stop":
                break
            if k == "tdir":
                out.append(self.time_dir(c, seg))
                continue
            _, flags, width, prec, ch = seg
            st = c.st
            conv = "s"
            if ch == "p":
                v = c.path
            elif ch == "f":
                v = base_name(c.path)
            elif ch == "h":
                idx = c.path.rfind("/")
                v = "." if idx < 0 else c.path[:idx]
            elif ch == "P":
                if c.depth > 0:
                    v = c.path[len(c.root_arg):]
                    if v.startswith("/"):
                        v = v[1:]
                else:
                    v = ""
            elif ch == "H":
                v = c.root_arg
            elif ch == "d":
                v = c.depth
                conv = "d"
            elif ch == "s":
                v = str(st.st_size)
            elif ch == "y":
                v = type_char(st.st_mode)
            elif ch == "Y":
                v = type_char(st.st_mode)
                if v == "l":
                    try:
                        v = type_char(os.stat(s2b(c.path)).st_mode)
                    except FileNotFoundError:
                        v = "N"
                    except OSError:
                        v = "?"
            elif ch == "m":
                v = st.st_mode & 0o7777
                conv = "o"
            elif ch == "M":
                v = mode_string(st.st_mode)
            elif ch == "l":
                v = ""
                if stat.S_ISLNK(st.st_mode):
                    try:
                        v = b2s(os.readlink(s2b(c.path)))
                    except OSError as e:
                        err("%s: %s" % (quote(c.path), e.strerror))
                        self.exit_status = 1
            elif ch == "n":
                v = str(st.st_nlink)
            elif ch == "i":
                v = str(st.st_ino)
            elif ch == "D":
                v = str(st.st_dev)
            elif ch == "b":
                v = str(getattr(st, "st_blocks", 0))
            elif ch == "k":
                v = str((getattr(st, "st_blocks", 0) + 1) // 2)
            elif ch == "U":
                v = str(st.st_uid)
            elif ch == "G":
                v = str(st.st_gid)
            elif ch == "u":
                try:
                    import pwd
                    v = pwd.getpwuid(st.st_uid).pw_name
                except Exception:
                    v = str(st.st_uid)
            elif ch == "g":
                try:
                    import grp
                    v = grp.getgrgid(st.st_gid).gr_name
                except Exception:
                    v = str(st.st_gid)
            elif ch in "act":
                ts = {"a": st.st_atime, "c": st.st_ctime, "t": st.st_mtime}[ch]
                v = time.strftime("%a %b %e %H:%M:%S %Y", time.gmtime(int(ts)))
            elif ch == "S":
                blocks = getattr(st, "st_blocks", 0)
                v = "%g" % ((blocks * 512.0) / st.st_size) if st.st_size else "1"
            elif ch == "F":
                v = "unknown"
            elif ch == "Z":
                v = ""
            else:
                v = ""
            out.append(c_format(flags, width, prec, conv, v))
        self.emit("".join(out))
        return True

    def time_dir(self, c, seg):
        _, flags, width, prec, ch, k = seg
        st = c.st
        ns = {"A": st.st_atime_ns, "C": st.st_ctime_ns, "T": st.st_mtime_ns,
              "B": st.st_mtime_ns}[ch]
        sec, frac = divmod(ns, 10**9)
        tm = time.gmtime(sec)
        if k == "@":
            v = "%d.%09d0" % (sec, frac)
        elif k == "S":
            v = "%02d.%09d0" % (tm.tm_sec, frac)
        elif k == "T":
            v = time.strftime("%H:%M:", tm) + "%02d.%09d0" % (tm.tm_sec, frac)
        elif k == "+":
            v = time.strftime("%Y-%m-%d+%H:%M:", tm) + "%02d.%09d0" % (tm.tm_sec, frac)
        elif k == "X":
            v = time.strftime("%H:%M:", tm) + "%02d.%09d0" % (tm.tm_sec, frac)
        else:
            try:
                v = time.strftime("%" + k, tm)
            except ValueError:
                v = ""
        return c_format(flags, width, prec, "s", v)

    # -- traversal -----------------------------------------------------------
    def run(self, starts, expr):
        for arg in starts:
            path = arg
            if not path:
                err("'': No such file or directory")
                self.exit_status = 1
                continue
            ln = len(path)
            if 2 < ln and path[-1] == "/":
                while 1 < ln and path[ln - 2] == "/":
                    ln -= 1
                path = path[:ln]
            try:
                st = os.lstat(s2b(path))
            except OSError as e:
                err("%s: %s" % (quote(arg), e.strerror))
                self.exit_status = 1
                continue
            self.visit(path, st, 0, arg, expr)

    def visit(self, path, st, depth, root_arg, expr):
        is_dir = stat.S_ISDIR(st.st_mode)
        c = Ctx(path, st, depth, root_arg)
        if not is_dir:
            if depth >= self.mindepth:
                expr.ev(c)
            return
        descend = not (self.maxdepth >= 0 and depth >= self.maxdepth)
        if not self.depth_first:
            if depth >= self.mindepth:
                expr.ev(c)
                if c.prune:
                    descend = False
        if descend:
            try:
                with os.scandir(s2b(path)) as it:
                    entries = list(it)
            except OSError as e:
                err("%s: %s" % (quote(path), e.strerror))
                self.exit_status = 1
                entries = []
            prefix = path if path.endswith("/") else path + "/"
            for ent in entries:
                cp = prefix + b2s(ent.name)
                try:
                    cst = ent.stat(follow_symlinks=False)
                except OSError as e:
                    err("%s: %s" % (quote(cp), e.strerror))
                    self.exit_status = 1
                    continue
                self.visit(cp, cst, depth + 1, root_arg, expr)
        if self.depth_first:
            if depth >= self.mindepth:
                expr.ev(c)


def looks_like_expression(arg, leading):
    if not arg:
        return False
    c = arg[0]
    if c == "-":
        return len(arg) > 1
    if c in "),":
        if len(arg) > 1:
            return False
        return not leading
    if c in "(!":
        return len(arg) == 1
    return False


def main(argv):
    args = [arg2s(a) for a in argv]
    sys.setrecursionlimit(100000)
    f = Finder()
    i = 0
    while i < len(args):
        a = args[i]
        if a == "-P" or (a.startswith("-O") and a[2:].isdigit()):
            i += 1
        elif a == "--":
            i += 1
            break
        else:
            break
    starts = []
    while i < len(args) and not looks_like_expression(args[i], True):
        starts.append(args[i])
        i += 1
    if not starts:
        starts = ["."]
    try:
        expr = f.parse(args[i:])
    except FindError as e:
        err(str(e))
        return 1
    if expr is None:
        expr = f.p_print("-print")
    elif not f.has_action:
        expr = And(expr, f.p_print("-print"))
    try:
        f.run(starts, expr)
    except Quit:
        pass
    try:
        f.flush()
    except BrokenPipeError:
        return 1
    return f.exit_status


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
