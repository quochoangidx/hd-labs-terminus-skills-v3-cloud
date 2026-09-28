"""pyfind: a GNU find 4.9.0 replacement in pure Python.

Usage: python3 /app/pyfind/find.py [starting-point...] [expression]

Symbolic links are never followed (the default -P behaviour).  All paths,
names and patterns are handled as bytes so that arbitrary file names are
reproduced exactly.
"""

import os
import re
import stat
import sys
import time

PROG = "find"


class FindError(Exception):
    """A fatal error: message goes to stderr and find exits with status 1."""


class Quit(Exception):
    pass


def warn(msg):
    try:
        sys.stderr.write("%s: %s\n" % (PROG, msg))
        sys.stderr.flush()
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Character helpers (C locale)
# ---------------------------------------------------------------------------

def c_lower(b):
    return b + 32 if 65 <= b <= 90 else b


def c_upper(b):
    return b - 32 if 97 <= b <= 122 else b


def _isalpha(b):
    return 65 <= b <= 90 or 97 <= b <= 122


def _isdigit(b):
    return 48 <= b <= 57


CLASS_TESTS = {
    b"alnum": lambda b: _isalpha(b) or _isdigit(b),
    b"alpha": _isalpha,
    b"blank": lambda b: b in (32, 9),
    b"cntrl": lambda b: b < 32 or b == 127,
    b"digit": _isdigit,
    b"graph": lambda b: 33 <= b <= 126,
    b"lower": lambda b: 97 <= b <= 122,
    b"print": lambda b: 32 <= b <= 126,
    b"punct": lambda b: 33 <= b <= 126 and not (_isalpha(b) or _isdigit(b)),
    b"space": lambda b: b in (32, 9, 10, 11, 12, 13),
    b"upper": lambda b: 65 <= b <= 90,
    b"xdigit": lambda b: _isdigit(b) or 65 <= b <= 70 or 97 <= b <= 102,
}

ANY_BYTE = "[\\x00-\\xff]"
NEVER = "(?!)"


def byte_set_re(members):
    """Python regex (str) for a set of byte values."""
    members = sorted(set(members))
    if not members:
        return NEVER
    if len(members) == 256:
        return ANY_BYTE
    parts = []
    i = 0
    n = len(members)
    while i < n:
        j = i
        while j + 1 < n and members[j + 1] == members[j] + 1:
            j += 1
        if j == i:
            parts.append("\\x%02x" % members[i])
        else:
            parts.append("\\x%02x-\\x%02x" % (members[i], members[j]))
        i = j + 1
    return "[" + "".join(parts) + "]"


# ---------------------------------------------------------------------------
# fnmatch (glibc semantics, flags 0 or FNM_CASEFOLD)
# ---------------------------------------------------------------------------

def _fn_scan_bracket(pat, p, fold):
    n = len(pat)

    def at(k):
        return pat[k] if k < n else 0

    F = c_lower if fold else (lambda x: x)
    neg = at(p) in (33, 94)
    if neg:
        p += 1
    items = []
    c = at(p)
    p += 1
    while True:
        normal = False
        if c == 92:
            if at(p) == 0:
                return ("never",)
            c = F(at(p))
            p += 1
            normal = True
        elif c == 91 and at(p) == 58:
            startp = p
            name = bytearray()
            qq = p
            ok = False
            while True:
                if len(name) == 256:
                    return ("never",)
                qq += 1
                cc = at(qq)
                if cc == 58 and at(qq + 1) == 93:
                    qq += 2
                    ok = True
                    break
                if cc < 97 or cc >= 122:
                    break
                name.append(cc)
            if ok:
                p = qq
                items.append(("class", bytes(name)))
                c = at(p)
                p += 1
                if c == 93:
                    break
                continue
            p = startp
            c = 91
            normal = True
        elif c == 0:
            return ("unterminated", items, neg)
        else:
            c = F(c)
            normal = True
        if normal:
            is_range = at(p) == 45 and at(p + 1) != 0 and at(p + 1) != 93
            if not is_range:
                items.append(("char", c))
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
                    return ("never",)
                items.append(("range", cold, F(cend)))
                c = at(p)
                p += 1
        if c == 93:
            break
    return ("ok", items, neg, p)


def _fn_eval_items(items, b, fold):
    fn = c_lower(b) if fold else b
    for it in items:
        k = it[0]
        if k == "char":
            if it[1] == fn:
                return "match"
        elif k == "range":
            if it[1] <= fn <= it[2]:
                return "match"
        else:
            t = CLASS_TESTS.get(it[1])
            if t is None:
                return "fail"
            if t(b):
                return "match"
    return "nomatch"


def _fn_lit(c, fold):
    if fold and _isalpha(c):
        return "[\\x%02x\\x%02x]" % (c_lower(c), c_upper(c))
    return "\\x%02x" % c


_fn_cache = {}


def fnmatch_compile(pat, fold):
    key = (pat, fold)
    r = _fn_cache.get(key)
    if r is not None:
        return r
    out = []
    i = 0
    n = len(pat)
    while i < n:
        c = pat[i]
        if c == 42:
            while i < n and pat[i] == 42:
                i += 1
            out.append(ANY_BYTE + "*")
            continue
        if c == 63:
            out.append(ANY_BYTE)
            i += 1
        elif c == 92:
            if i + 1 >= n:
                out.append(NEVER)
                i += 1
            else:
                out.append(_fn_lit(pat[i + 1], fold))
                i += 2
        elif c == 91:
            res = _fn_scan_bracket(pat, i + 1, fold)
            if res[0] == "never":
                out.append(NEVER)
                break
            if res[0] == "unterminated":
                if _fn_eval_items(res[1], 91, fold) == "nomatch":
                    out.append(_fn_lit(91, fold))
                else:
                    out.append(NEVER)
                i += 1
            else:
                items, neg, end = res[1], res[2], res[3]
                members = []
                for b in range(256):
                    r2 = _fn_eval_items(items, b, fold)
                    if r2 == "match":
                        ok = not neg
                    elif r2 == "fail":
                        ok = False
                    else:
                        ok = neg
                    if ok:
                        members.append(b)
                out.append(byte_set_re(members))
                i = end
        else:
            out.append(_fn_lit(c, fold))
            i += 1
    rx = re.compile(("".join(out)).encode("ascii"), re.DOTALL)
    _fn_cache[key] = rx
    return rx


# ---------------------------------------------------------------------------
# GNU regex -> Python re translation
# ---------------------------------------------------------------------------

RE_BACKSLASH_ESCAPE_IN_LISTS = 1
RE_BK_PLUS_QM = 1 << 1
RE_CHAR_CLASSES = 1 << 2
RE_CONTEXT_INDEP_ANCHORS = 1 << 3
RE_CONTEXT_INDEP_OPS = 1 << 4
RE_CONTEXT_INVALID_OPS = 1 << 5
RE_DOT_NEWLINE = 1 << 6
RE_DOT_NOT_NULL = 1 << 7
RE_HAT_LISTS_NOT_NEWLINE = 1 << 8
RE_INTERVALS = 1 << 9
RE_LIMITED_OPS = 1 << 10
RE_NEWLINE_ALT = 1 << 11
RE_NO_BK_BRACES = 1 << 12
RE_NO_BK_PARENS = 1 << 13
RE_NO_BK_REFS = 1 << 14
RE_NO_BK_VBAR = 1 << 15
RE_NO_EMPTY_RANGES = 1 << 16
RE_UNMATCHED_RIGHT_PAREN_ORD = 1 << 17
RE_NO_POSIX_BACKTRACKING = 1 << 18
RE_NO_GNU_OPS = 1 << 19
RE_DEBUG = 1 << 20
RE_INVALID_INTERVAL_ORD = 1 << 21
RE_ICASE = 1 << 22
RE_CARET_ANCHORS_HERE = 1 << 23
RE_CONTEXT_INVALID_DUP = 1 << 24
RE_NO_SUB = 1 << 25

_POSIX_COMMON = (RE_CHAR_CLASSES | RE_DOT_NEWLINE | RE_DOT_NOT_NULL
                 | RE_INTERVALS | RE_NO_EMPTY_RANGES)
_POSIX_BASIC = _POSIX_COMMON | RE_BK_PLUS_QM | RE_CONTEXT_INVALID_DUP
_POSIX_EXTENDED = (_POSIX_COMMON | RE_CONTEXT_INDEP_ANCHORS
                   | RE_CONTEXT_INDEP_OPS | RE_NO_BK_BRACES
                   | RE_NO_BK_PARENS | RE_NO_BK_VBAR
                   | RE_CONTEXT_INVALID_OPS | RE_UNMATCHED_RIGHT_PAREN_ORD)
_EMACS = 0
_AWK = (RE_BACKSLASH_ESCAPE_IN_LISTS | RE_DOT_NOT_NULL | RE_NO_BK_PARENS
        | RE_NO_BK_REFS | RE_NO_BK_VBAR | RE_NO_EMPTY_RANGES
        | RE_DOT_NEWLINE | RE_CONTEXT_INDEP_ANCHORS | RE_CHAR_CLASSES
        | RE_UNMATCHED_RIGHT_PAREN_ORD | RE_NO_GNU_OPS)
_GNU_AWK = ((_POSIX_EXTENDED | RE_BACKSLASH_ESCAPE_IN_LISTS
             | RE_INVALID_INTERVAL_ORD)
            & ~(RE_DOT_NOT_NULL | RE_CONTEXT_INDEP_OPS
                | RE_CONTEXT_INVALID_OPS))
_POSIX_AWK = (_POSIX_EXTENDED | RE_BACKSLASH_ESCAPE_IN_LISTS | RE_INTERVALS
              | RE_NO_GNU_OPS | RE_INVALID_INTERVAL_ORD)
_GREP = (_POSIX_BASIC | RE_NEWLINE_ALT) & ~(RE_CONTEXT_INVALID_DUP
                                             | RE_DOT_NOT_NULL)
_EGREP = ((_POSIX_EXTENDED | RE_INVALID_INTERVAL_ORD | RE_NEWLINE_ALT)
          & ~(RE_CONTEXT_INVALID_OPS | RE_DOT_NOT_NULL))

REGEX_TYPES = {
    "findutils-default": _EMACS | RE_DOT_NEWLINE,
    "ed": None,
    "emacs": _EMACS,
    "gnu-awk": _GNU_AWK,
    "grep": _GREP,
    "posix-awk": _POSIX_AWK,
    "awk": _AWK,
    "posix-basic": _POSIX_BASIC,
    "posix-egrep": _EGREP,
    "egrep": _EGREP,
    "posix-extended": _POSIX_EXTENDED,
    "posix-minimal-basic": None,
    "sed": None,
}

(T_CHAR, T_ALT, T_STAR, T_PLUS, T_QMARK, T_OPEN_DUP, T_CLOSE_DUP, T_OPEN_SUB,
 T_CLOSE_SUB, T_BRACKET, T_PERIOD, T_ANCHOR, T_BACKREF, T_WORD, T_NOTWORD,
 T_SPACE, T_NOTSPACE, T_BACKSLASH, T_END) = range(19)

(B_CHAR, B_RANGE, B_CLOSE, B_NONMATCH, B_COLL, B_EQUIV, B_CLASS,
 B_END) = range(8)


class RegexError(Exception):
    pass


class GnuRegex:
    def __init__(self, pattern, syntax):
        self.orig = pattern
        self.icase = bool(syntax & RE_ICASE)
        if self.icase:
            self.p = bytes(c_upper(b) for b in pattern)
        else:
            self.p = pattern
        self.n = len(pattern)
        self.syntax = syntax
        self.i = 0
        self.nsub = 0
        self.completed = set()
        self.tok = None

    # -- tokenizer ---------------------------------------------------------
    def peek_token(self, i, syntax):
        p = self.p
        n = self.n
        if i >= n:
            return (T_END, 0, 0, None)
        c = p[i]
        if c == 92:
            if i + 1 >= n:
                return (T_BACKSLASH, c, 1, None)
            c2 = self.orig[i + 1]
            t = T_CHAR
            extra = None
            gnu = not (syntax & RE_NO_GNU_OPS)
            if c2 == 124:  # |
                if not (syntax & RE_LIMITED_OPS) and not (syntax & RE_NO_BK_VBAR):
                    t = T_ALT
            elif 49 <= c2 <= 57:
                if not (syntax & RE_NO_BK_REFS):
                    t = T_BACKREF
                    extra = c2 - 49
            elif c2 == 60 and gnu:
                t, extra = T_ANCHOR, "WORD_FIRST"
            elif c2 == 62 and gnu:
                t, extra = T_ANCHOR, "WORD_LAST"
            elif c2 == 98 and gnu:
                t, extra = T_ANCHOR, "WORD_DELIM"
            elif c2 == 66 and gnu:
                t, extra = T_ANCHOR, "NOT_WORD_DELIM"
            elif c2 == 119 and gnu:
                t = T_WORD
            elif c2 == 87 and gnu:
                t = T_NOTWORD
            elif c2 == 115 and gnu:
                t = T_SPACE
            elif c2 == 83 and gnu:
                t = T_NOTSPACE
            elif c2 == 96 and gnu:
                t, extra = T_ANCHOR, "BUF_FIRST"
            elif c2 == 39 and gnu:
                t, extra = T_ANCHOR, "BUF_LAST"
            elif c2 == 40:
                if not (syntax & RE_NO_BK_PARENS):
                    t = T_OPEN_SUB
            elif c2 == 41:
                if not (syntax & RE_NO_BK_PARENS):
                    t = T_CLOSE_SUB
            elif c2 == 43:
                if not (syntax & RE_LIMITED_OPS) and (syntax & RE_BK_PLUS_QM):
                    t = T_PLUS
            elif c2 == 63:
                if not (syntax & RE_LIMITED_OPS) and (syntax & RE_BK_PLUS_QM):
                    t = T_QMARK
            elif c2 == 123:
                if (syntax & RE_INTERVALS) and not (syntax & RE_NO_BK_BRACES):
                    t = T_OPEN_DUP
            elif c2 == 125:
                if (syntax & RE_INTERVALS) and not (syntax & RE_NO_BK_BRACES):
                    t = T_CLOSE_DUP
            return (t, c2, 2, extra)
        t = T_CHAR
        extra = None
        if c == 10:
            if syntax & RE_NEWLINE_ALT:
                t = T_ALT
        elif c == 124:
            if not (syntax & RE_LIMITED_OPS) and (syntax & RE_NO_BK_VBAR):
                t = T_ALT
        elif c == 42:
            t = T_STAR
        elif c == 43:
            if not (syntax & RE_LIMITED_OPS) and not (syntax & RE_BK_PLUS_QM):
                t = T_PLUS
        elif c == 63:
            if not (syntax & RE_LIMITED_OPS) and not (syntax & RE_BK_PLUS_QM):
                t = T_QMARK
        elif c == 123:
            if (syntax & RE_INTERVALS) and (syntax & RE_NO_BK_BRACES):
                t = T_OPEN_DUP
        elif c == 125:
            if (syntax & RE_INTERVALS) and (syntax & RE_NO_BK_BRACES):
                t = T_CLOSE_DUP
        elif c == 40:
            if syntax & RE_NO_BK_PARENS:
                t = T_OPEN_SUB
        elif c == 41:
            if syntax & RE_NO_BK_PARENS:
                t = T_CLOSE_SUB
        elif c == 91:
            t = T_BRACKET
        elif c == 46:
            t = T_PERIOD
        elif c == 94:
            anchor = True
            if (not (syntax & (RE_CONTEXT_INDEP_ANCHORS | RE_CARET_ANCHORS_HERE))
                    and i != 0):
                prev = p[i - 1]
                if not (syntax & RE_NEWLINE_ALT) or prev != 10:
                    anchor = False
            if anchor:
                t, extra = T_ANCHOR, "LINE_FIRST"
        elif c == 36:
            anchor = True
            if not (syntax & RE_CONTEXT_INDEP_ANCHORS) and i + 1 != n:
                nxt = self.peek_token(i + 1, syntax)
                if nxt[0] not in (T_ALT, T_CLOSE_SUB):
                    anchor = False
            if anchor:
                t, extra = T_ANCHOR, "LINE_LAST"
        return (t, c, 1, extra)

    def fetch(self, syntax):
        tok = self.peek_token(self.i, syntax)
        self.i += tok[2]
        self.tok = tok
        return tok

    # -- parser ------------------------------------------------------------
    def parse(self):
        syntax = self.syntax
        self.fetch(syntax | RE_CARET_ANCHORS_HERE)
        tree = self.parse_reg_exp(syntax, 0)
        if self.tok[0] != T_END:
            raise RegexError("Unmatched ) or \\)")
        return tree

    def parse_reg_exp(self, syntax, nest):
        initial = set(self.completed)
        branches = [self.parse_branch(syntax, nest)]
        while self.tok[0] == T_ALT:
            self.fetch(syntax | RE_CARET_ANCHORS_HERE)
            t = self.tok[0]
            if t != T_ALT and t != T_END and (nest == 0 or t != T_CLOSE_SUB):
                accumulated = set(self.completed)
                self.completed = set(initial)
                br = self.parse_branch(syntax, nest)
                self.completed |= accumulated
            else:
                br = None
            branches.append(br)
        if len(branches) == 1:
            return branches[0]
        return ("alt", branches)

    def parse_branch(self, syntax, nest):
        parts = []
        e = self.parse_expression(syntax, nest)
        if e is not None:
            parts.append(e)
        while True:
            t = self.tok[0]
            if t == T_ALT or t == T_END or (nest != 0 and t == T_CLOSE_SUB):
                break
            e = self.parse_expression(syntax, nest)
            if e is not None:
                parts.append(e)
        if not parts:
            return None
        if len(parts) == 1:
            return parts[0]
        return ("cat", parts)

    def parse_expression(self, syntax, nest):
        tok = self.tok
        t = tok[0]
        tree = None
        if t == T_CHAR:
            tree = ("char", tok[1])
        elif t == T_OPEN_SUB:
            tree = self.parse_sub_exp(syntax, nest + 1)
        elif t == T_BRACKET:
            tree = self.parse_bracket(syntax)
        elif t == T_BACKREF:
            if tok[3] not in self.completed:
                raise RegexError("Invalid back reference")
            tree = ("backref", tok[3])
        elif t in (T_OPEN_DUP, T_STAR, T_PLUS, T_QMARK, T_CLOSE_SUB,
                   T_CLOSE_DUP):
            if t == T_OPEN_DUP and (syntax & RE_CONTEXT_INVALID_DUP):
                raise RegexError("Invalid preceding regular expression")
            if t in (T_OPEN_DUP, T_STAR, T_PLUS, T_QMARK):
                if ((syntax & RE_CONTEXT_INVALID_OPS)
                        and not (syntax & RE_CONTEXT_INVALID_DUP)):
                    raise RegexError("Invalid preceding regular expression")
                elif syntax & RE_CONTEXT_INDEP_OPS:
                    self.fetch(syntax)
                    return self.parse_expression(syntax, nest)
            if t == T_CLOSE_SUB and not (syntax & RE_UNMATCHED_RIGHT_PAREN_ORD):
                raise RegexError("Unmatched ) or \\)")
            tree = ("char", tok[1])
        elif t == T_ANCHOR:
            tree = ("anchor", tok[3])
            self.fetch(syntax)
            return tree
        elif t == T_PERIOD:
            tree = ("any",)
        elif t in (T_WORD, T_NOTWORD):
            m = [b for b in range(256)
                 if _isalpha(b) or _isdigit(b) or b == 95]
            if t == T_NOTWORD:
                s = set(m)
                m = [b for b in range(256) if b not in s]
            tree = ("set", m)
        elif t in (T_SPACE, T_NOTSPACE):
            m = [b for b in range(256) if CLASS_TESTS[b"space"](b)]
            if t == T_NOTSPACE:
                s = set(m)
                m = [b for b in range(256) if b not in s]
            tree = ("set", m)
        elif t == T_ALT or t == T_END:
            return None
        elif t == T_BACKSLASH:
            raise RegexError("Trailing backslash")
        else:
            return None
        self.fetch(syntax)
        while self.tok[0] in (T_STAR, T_PLUS, T_QMARK, T_OPEN_DUP):
            tree = self.parse_dup_op(tree, syntax)
            if ((syntax & RE_CONTEXT_INVALID_DUP)
                    and self.tok[0] in (T_STAR, T_OPEN_DUP)):
                raise RegexError("Invalid preceding regular expression")
        return tree

    def parse_sub_exp(self, syntax, nest):
        cur = self.nsub
        self.nsub += 1
        self.fetch(syntax | RE_CARET_ANCHORS_HERE)
        if self.tok[0] == T_CLOSE_SUB:
            tree = None
        else:
            tree = self.parse_reg_exp(syntax, nest)
            if self.tok[0] != T_CLOSE_SUB:
                raise RegexError("Unmatched ( or \\(")
        if cur <= 8:
            self.completed.add(cur)
        return ("group", cur, tree)

    def fetch_number(self, syntax):
        num = -1
        while True:
            tok = self.fetch(syntax)
            c = tok[1]
            if tok[0] == T_END:
                return -2
            if tok[0] == T_CLOSE_DUP or c == 44:
                break
            if tok[0] != T_CHAR or c < 48 or c > 57 or num == -2:
                num = -2
            elif num == -1:
                num = c - 48
            else:
                num = min(0x8000, num * 10 + c - 48)
        return num

    def parse_dup_op(self, elem, syntax):
        tok = self.tok
        start_idx = self.i
        if tok[0] == T_OPEN_DUP:
            end = 0
            start = self.fetch_number(syntax)
            if start == -1:
                if self.tok[0] == T_CHAR and self.tok[1] == 44:
                    start = 0
                else:
                    raise RegexError("Invalid content of \\{\\}")
            if start != -2:
                if self.tok[0] == T_CLOSE_DUP:
                    end = start
                elif self.tok[0] == T_CHAR and self.tok[1] == 44:
                    end = self.fetch_number(syntax)
                else:
                    end = -2
            if start == -2 or end == -2:
                if not (syntax & RE_INVALID_INTERVAL_ORD):
                    if self.tok[0] == T_END:
                        raise RegexError("Unmatched \\{")
                    raise RegexError("Invalid content of \\{\\}")
                self.i = start_idx
                self.tok = (T_CHAR, tok[1], tok[2], None)
                return elem
            if (end != -1 and start > end) or self.tok[0] != T_CLOSE_DUP:
                raise RegexError("Invalid content of \\{\\}")
            if (start if end == -1 else end) > 0x7fff:
                raise RegexError("Regular expression too big")
        else:
            start = 1 if tok[0] == T_PLUS else 0
            end = 1 if tok[0] == T_QMARK else -1
        self.fetch(syntax)
        if elem is None:
            return None
        return ("dup", elem, start, end)

    # -- bracket expressions -----------------------------------------------
    def peek_bracket(self, syntax):
        i = self.i
        p = self.p
        n = self.n
        if i >= n:
            return (B_END, 0, 0)
        c = p[i]
        if c == 92 and (syntax & RE_BACKSLASH_ESCAPE_IN_LISTS) and i + 1 < n:
            return (B_CHAR, self.orig[i + 1], 2)
        if c == 91:
            c2 = p[i + 1] if i + 1 < n else 0
            if c2 == 46:
                return (B_COLL, c2, 2)
            if c2 == 61:
                return (B_EQUIV, c2, 2)
            if c2 == 58 and (syntax & RE_CHAR_CLASSES):
                return (B_CLASS, c2, 2)
            return (B_CHAR, c, 1)
        if c == 45:
            return (B_RANGE, c, 1)
        if c == 93:
            return (B_CLOSE, c, 1)
        if c == 94:
            return (B_NONMATCH, c, 1)
        return (B_CHAR, c, 1)

    def parse_bracket_element(self, tok, syntax, accept_hyphen):
        self.i += tok[2]
        if tok[0] in (B_COLL, B_EQUIV, B_CLASS):
            return self.parse_bracket_symbol(tok)
        if tok[0] == B_RANGE and not accept_hyphen:
            t2 = self.peek_bracket(syntax)
            if t2[0] != B_CLOSE:
                raise RegexError("Invalid range end")
        return ("sb", tok[1])

    def parse_bracket_symbol(self, tok):
        delim = tok[1]
        if self.i >= self.n:
            raise RegexError("Unmatched [, [^, [:, [., or [=")
        name = bytearray()
        src = self.orig if tok[0] == B_CLASS else self.p
        while True:
            if len(name) >= 32:
                raise RegexError("Unmatched [, [^, [:, [., or [=")
            ch = src[self.i]
            self.i += 1
            if self.i >= self.n:
                raise RegexError("Unmatched [, [^, [:, [., or [=")
            if ch == delim and self.p[self.i] == 93:
                break
            name.append(ch)
        self.i += 1
        kind = {B_COLL: "coll", B_EQUIV: "equiv", B_CLASS: "class"}[tok[0]]
        return (kind, bytes(name))

    def parse_bracket(self, syntax):
        members = set()
        classes = []
        non_match = False
        tok = self.peek_bracket(syntax)
        if tok[0] == B_NONMATCH:
            non_match = True
            if syntax & RE_HAT_LISTS_NOT_NEWLINE:
                members.add(10)
            self.i += tok[2]
            tok = self.peek_bracket(syntax)
        if tok[0] == B_CLOSE:
            tok = (B_CHAR, tok[1], tok[2])
        first = True
        while True:
            start_elem = self.parse_bracket_element(tok, syntax, first)
            first = False
            tok = self.peek_bracket(syntax)
            is_range = False
            tok2 = None
            if start_elem[0] not in ("class", "equiv"):
                if tok[0] == B_END:
                    raise RegexError("Unmatched [, [^, [:, [., or [=")
                if tok[0] == B_RANGE:
                    self.i += tok[2]
                    tok2 = self.peek_bracket(syntax)
                    if tok2[0] == B_END:
                        raise RegexError("Unmatched [, [^, [:, [., or [=")
                    if tok2[0] == B_CLOSE:
                        self.i -= tok[2]
                        tok = (B_CHAR, tok[1], tok[2])
                    else:
                        is_range = True
            if is_range:
                end_elem = self.parse_bracket_element(tok2, syntax, True)
                tok = self.peek_bracket(syntax)
                lo = self._range_point(start_elem)
                hi = self._range_point(end_elem)
                if (syntax & RE_NO_EMPTY_RANGES) and lo > hi:
                    raise RegexError("Invalid range end")
                for b in range(lo, hi + 1):
                    members.add(b)
            else:
                k = start_elem[0]
                if k == "sb":
                    members.add(start_elem[1])
                elif k in ("coll", "equiv"):
                    if len(start_elem[1]) != 1:
                        raise RegexError("Invalid collation character")
                    members.add(start_elem[1][0])
                else:
                    name = start_elem[1]
                    if (syntax & RE_ICASE) and name in (b"upper", b"lower"):
                        name = b"alpha"
                    if name not in CLASS_TESTS:
                        raise RegexError("Invalid character class name")
                    classes.append(CLASS_TESTS[name])
            if tok[0] == B_END:
                raise RegexError("Unmatched [, [^, [:, [., or [=")
            if tok[0] == B_CLOSE:
                break
        self.i += tok[2]
        result = []
        for b in range(256):
            x = c_upper(b) if self.icase else b
            m = x in members or any(f(x) for f in classes)
            if m != non_match:
                result.append(b)
        return ("set", result)

    def _range_point(self, elem):
        k = elem[0]
        if k in ("class", "equiv"):
            raise RegexError("Invalid range end")
        if k == "coll":
            if len(elem[1]) != 1:
                raise RegexError("Invalid collation character")
            return elem[1][0]
        return elem[1]

    # -- emission ----------------------------------------------------------
    def emit(self, node):
        if node is None:
            return ""
        k = node[0]
        if k == "char":
            return "\\x%02x" % node[1]
        if k == "any":
            if self.syntax & RE_DOT_NEWLINE:
                return "[^\\x00]" if self.syntax & RE_DOT_NOT_NULL else ANY_BYTE
            return "[^\\n\\x00]" if self.syntax & RE_DOT_NOT_NULL else "[^\\n]"
        if k == "set":
            return byte_set_re(node[1])
        if k == "anchor":
            a = node[1]
            return {
                "LINE_FIRST": "^",
                "LINE_LAST": "$",
                "BUF_FIRST": "\\A",
                "BUF_LAST": "\\Z",
                "WORD_DELIM": "\\b",
                "NOT_WORD_DELIM": "\\B",
                "WORD_FIRST": "(?<!\\w)(?=\\w)",
                "WORD_LAST": "(?<=\\w)(?!\\w)",
            }[a]
        if k == "backref":
            return "(?:\\%d)" % (node[1] + 1)
        if k == "group":
            return "(" + self.emit(node[2]) + ")"
        if k == "cat":
            return "".join(self.emit(x) for x in node[1])
        if k == "alt":
            return "(?:" + "|".join(self.emit(x) for x in node[1]) + ")"
        if k == "dup":
            inner = self.emit(node[1])
            lo, hi = node[2], node[3]
            if hi == -1:
                q_ = "{%d,}" % lo
            else:
                q_ = "{%d,%d}" % (lo, hi)
            return "(?:" + inner + ")" + q_
        raise RegexError("internal")

    def compile(self):
        tree = self.parse()
        src = self.emit(tree)
        flags = re.MULTILINE
        if self.icase:
            flags |= re.IGNORECASE
        try:
            return re.compile(src.encode("ascii"), flags)
        except re.error as e:
            raise RegexError(str(e))
        except (OverflowError, RecursionError) as e:
            raise RegexError(str(e))


# ---------------------------------------------------------------------------
# chmod-style mode parsing (gnulib modechange)
# ---------------------------------------------------------------------------

S_ISUID, S_ISGID, S_ISVTX = 0o4000, 0o2000, 0o1000
S_IRWXU, S_IRWXG, S_IRWXO = 0o700, 0o070, 0o007
CHMOD_MODE_BITS = 0o7777


def mode_compile(s):
    n = len(s)

    def ch(i):
        return s[i] if i < n else 0

    if n and 48 <= s[0] < 56:
        octal = 0
        p = 0
        while p < n and 48 <= s[p] < 56:
            octal = octal * 8 + s[p] - 48
            p += 1
            if octal > 0o7777:
                return None
        if p != n:
            return None
        mode = octal
        if p < 5:
            mentioned = (mode & (S_ISUID | S_ISGID)) | S_ISVTX | 0o777
        else:
            mentioned = CHMOD_MODE_BITS
        return [("=", "ord", CHMOD_MODE_BITS, mode, mentioned)]
    changes = []
    p = 0
    while True:
        affected = 0
        while True:
            c = ch(p)
            if c == 117:
                affected |= S_ISUID | S_IRWXU
            elif c == 103:
                affected |= S_ISGID | S_IRWXG
            elif c == 111:
                affected |= S_ISVTX | S_IRWXO
            elif c == 97:
                affected |= CHMOD_MODE_BITS
            elif c in (61, 43, 45):
                break
            else:
                return None
            p += 1
        while True:
            op = chr(ch(p))
            p += 1
            mentioned = 0
            flag = "copy"
            c = ch(p)
            if 48 <= c < 56:
                octal = 0
                while 48 <= ch(p) < 56:
                    octal = octal * 8 + ch(p) - 48
                    p += 1
                    if octal > 0o7777:
                        return None
                if affected or (ch(p) and ch(p) != 44):
                    return None
                affected = mentioned = CHMOD_MODE_BITS
                value = octal
                flag = "ord"
            elif c == 117:
                value = S_IRWXU
                p += 1
            elif c == 103:
                value = S_IRWXG
                p += 1
            elif c == 111:
                value = S_IRWXO
                p += 1
            else:
                value = 0
                flag = "ord"
                while True:
                    c = ch(p)
                    if c == 114:
                        value |= 0o444
                    elif c == 119:
                        value |= 0o222
                    elif c == 120:
                        value |= 0o111
                    elif c == 88:
                        flag = "X"
                    elif c == 115:
                        value |= S_ISUID | S_ISGID
                    elif c == 116:
                        value |= S_ISVTX
                    else:
                        break
                    p += 1
            if mentioned:
                ment = mentioned
            elif affected:
                ment = affected & value
            else:
                ment = value
            changes.append((op, flag, affected, value, ment))
            if ch(p) not in (61, 43, 45):
                break
        if ch(p) != 44:
            break
        p += 1
    if p >= n:
        return changes
    return None


def mode_adjust(oldmode, is_dir, umask_value, changes):
    newmode = oldmode & CHMOD_MODE_BITS
    for op, flag, affected, value, mentioned in changes:
        omit_change = ((S_ISUID | S_ISGID) if is_dir else 0) & ~mentioned
        if flag == "copy":
            value &= newmode
            v = 0
            if value & 0o444:
                v |= 0o444
            if value & 0o222:
                v |= 0o222
            if value & 0o111:
                v |= 0o111
            value |= v
        elif flag == "X":
            if (newmode & 0o111) or is_dir:
                value |= 0o111
        value &= (affected if affected else ~umask_value) & ~omit_change
        if op == "=":
            preserved = (~affected if affected else 0) | omit_change
            newmode = (newmode & preserved) | value
        elif op == "+":
            newmode |= value
        elif op == "-":
            newmode &= ~value
        newmode &= 0o7777
    return newmode & 0o7777


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

def base_len(s):
    n = len(s)
    while n > 1 and s[n - 1] == 47:
        n -= 1
    return n


def base_name(p):
    i = 0
    n = len(p)
    while i < n and p[i] == 47:
        i += 1
    base = i
    saw_slash = False
    for j in range(i, n):
        if p[j] == 47:
            saw_slash = True
        elif saw_slash:
            base = j
            saw_slash = False
    comp = p[base:]
    if not comp:
        return p[:base_len(p)]
    length = base_len(comp)
    if length < len(comp) and comp[length] == 47:
        length += 1
    return comp[:length]


def strip_trailing_slashes(s):
    n = len(s)
    while n > 1 and s[n - 1] == 47:
        n -= 1
    return s[:n]


def filemode_string(mode):
    if stat.S_ISREG(mode):
        t = "-"
    elif stat.S_ISDIR(mode):
        t = "d"
    elif stat.S_ISLNK(mode):
        t = "l"
    elif stat.S_ISCHR(mode):
        t = "c"
    elif stat.S_ISBLK(mode):
        t = "b"
    elif stat.S_ISFIFO(mode):
        t = "p"
    elif stat.S_ISSOCK(mode):
        t = "s"
    else:
        t = "?"
    r = [t]
    r.append("r" if mode & 0o400 else "-")
    r.append("w" if mode & 0o200 else "-")
    if mode & S_ISUID:
        r.append("s" if mode & 0o100 else "S")
    else:
        r.append("x" if mode & 0o100 else "-")
    r.append("r" if mode & 0o040 else "-")
    r.append("w" if mode & 0o020 else "-")
    if mode & S_ISGID:
        r.append("s" if mode & 0o010 else "S")
    else:
        r.append("x" if mode & 0o010 else "-")
    r.append("r" if mode & 0o004 else "-")
    r.append("w" if mode & 0o002 else "-")
    if mode & S_ISVTX:
        r.append("t" if mode & 0o001 else "T")
    else:
        r.append("x" if mode & 0o001 else "-")
    return "".join(r)


def type_letter(mode):
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


# ---------------------------------------------------------------------------
# Traversal entries
# ---------------------------------------------------------------------------

class Ent:
    __slots__ = ("path", "depth", "st", "name", "start", "_empty")

    def __init__(self, path, depth, st, name, start):
        self.path = path
        self.depth = depth
        self.st = st
        self.name = name  # name used for -name tests
        self.start = start
        self._empty = None


# ---------------------------------------------------------------------------
# printf
# ---------------------------------------------------------------------------

WEEKDAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep",
          "Oct", "Nov", "Dec"]

PRINTF_DIRECTIVES = b"abcdDfFgGhHiklmMnpPsStuUyYZ"


def parse_spec(spec):
    """Parse a C printf spec (flags, width, precision) -> (flags, w, prec)."""
    flags = set()
    i = 0
    n = len(spec)
    while i < n and chr(spec[i]) in "-+ #0":
        flags.add(chr(spec[i]))
        i += 1
    w = 0
    while i < n and _isdigit(spec[i]):
        w = w * 10 + spec[i] - 48
        i += 1
    prec = None
    if i < n and spec[i] == 46:
        i += 1
        prec = 0
        while i < n and _isdigit(spec[i]):
            prec = prec * 10 + spec[i] - 48
            i += 1
    return flags, w, prec


def fmt_str(s, spec):
    flags, w, prec = spec
    if prec is not None:
        s = s[:prec]
    if w and len(s) < w:
        pad = b" " * (w - len(s))
        s = s + pad if "-" in flags else pad + s
    return s


def fmt_int(val, spec, conv):
    flags, w, prec = spec
    neg = val < 0
    a = -val if neg else val
    digits = ("%o" % a) if conv == "o" else str(a)
    if prec is not None:
        if prec == 0 and a == 0:
            digits = ""
        elif len(digits) < prec:
            digits = "0" * (prec - len(digits)) + digits
    if conv == "o" and "#" in flags and not digits.startswith("0"):
        digits = "0" + digits
    sign = ""
    if conv == "d":
        if neg:
            sign = "-"
        elif "+" in flags:
            sign = "+"
        elif " " in flags:
            sign = " "
    body = sign + digits
    if w and len(body) < w:
        if "-" in flags:
            body = body + " " * (w - len(body))
        elif "0" in flags and prec is None:
            body = sign + "0" * (w - len(body)) + digits
        else:
            body = " " * (w - len(body)) + body
    return body.encode()


def fmt_float_g(val, spec_bytes):
    try:
        return (("%" + spec_bytes.decode("ascii") + "g") % val).encode()
    except Exception:
        return ("%g" % val).encode()


ESCAPES = {97: 7, 98: 8, 102: 12, 110: 10, 114: 13, 116: 9, 118: 11, 92: 92}


def parse_printf_format(fmt):
    """Return list of segments: ('plain', bytes) | ('fmt', spec, conv, aux,
    rawspec) | ('stop',)."""
    segs = []
    buf = bytearray()
    i = 0
    n = len(fmt)

    def flush():
        if buf:
            segs.append(("plain", bytes(buf)))
            del buf[:]

    while i < n:
        c = fmt[i]
        if c == 92:
            if i + 1 >= n:
                warn("warning: escape `\\' followed by nothing at all")
                buf.append(92)
                i += 1
                continue
            d = fmt[i + 1]
            if 48 <= d <= 55:
                j = i + 1
                val = 0
                k = 0
                while k < 3 and j < n and 48 <= fmt[j] <= 55:
                    val = val * 8 + fmt[j] - 48
                    j += 1
                    k += 1
                buf.append(val & 0xFF)
                i = j
            elif d in ESCAPES:
                buf.append(ESCAPES[d])
                i += 2
            elif d == 99:  # \c
                flush()
                segs.append(("stop",))
                return segs
            else:
                warn("warning: unrecognized escape `\\%c'" % d)
                buf.append(92)
                buf.append(d)
                i += 2
        elif c == 37:
            if i + 1 >= n:
                raise FindError("error: %s at end of format string" % "%")
            if fmt[i + 1] == 37:
                buf.append(37)
                i += 2
                continue
            j = i + 1
            while j < n and fmt[j] in b"-+ #":
                j += 1
            while j < n and _isdigit(fmt[j]):
                j += 1
            if j < n and fmt[j] == 46:
                j += 1
                while j < n and _isdigit(fmt[j]):
                    j += 1
            if j < n and fmt[j] in PRINTF_DIRECTIVES:
                flush()
                raw = fmt[i + 1:j]
                segs.append(("fmt", parse_spec(raw), chr(fmt[j]), None, raw))
                i = j + 1
            elif j < n and fmt[j] in b"ABCT" and j + 1 < n:
                flush()
                raw = fmt[i + 1:j]
                segs.append(("fmt", parse_spec(raw), chr(fmt[j]),
                             chr(fmt[j + 1]), raw))
                i = j + 2
            else:
                if j < n:
                    warn("warning: unrecognized format directive `%%%c'"
                         % fmt[j])
                i += 1
        else:
            buf.append(c)
            i += 1
    flush()
    return segs


def ctime_format(sec, nsec):
    tm = time.localtime(sec)
    return ("%3s %3s %2d %02d:%02d:%02d.%09d0 %04d" % (
        WEEKDAYS[(tm.tm_wday + 1) % 7], MONTHS[tm.tm_mon - 1], tm.tm_mday,
        tm.tm_hour, tm.tm_min, tm.tm_sec, nsec, tm.tm_year)).encode()


def format_date(sec, nsec, kind):
    if kind == "+":
        fmt = "%F+%T"
        need_ns = True
    else:
        fmt = "%" + kind
        need_ns = kind in "STX@"
    ns = (".%09d0" % nsec) if need_ns else ""
    if kind != "@":
        try:
            tm = time.localtime(sec)
            s = time.strftime(fmt, tm)
            return (s + ns).encode("latin-1", "replace")
        except Exception:
            pass
    return (str(sec) + ns).encode()


_mount_cache = None


def fs_type(dev):
    global _mount_cache
    if _mount_cache is None:
        _mount_cache = {}
        try:
            with open("/proc/self/mountinfo", "rb") as f:
                for line in f:
                    parts = line.split()
                    try:
                        mm = parts[2].split(b":")
                        key = (int(mm[0]), int(mm[1]))
                        sep = parts.index(b"-")
                        _mount_cache[key] = parts[sep + 1]
                    except Exception:
                        continue
        except OSError:
            pass
    return _mount_cache.get((os.major(dev), os.minor(dev)), b"unknown")


def ceil_div(a, b):
    return -((-a) // b)


# ---------------------------------------------------------------------------
# The find engine
# ---------------------------------------------------------------------------

class Find:
    def __init__(self):
        self.status = 0
        self.out = []
        self.outlen = 0
        self.depth_first = False
        self.maxdepth = -1
        self.mindepth = -1
        self.regex_syntax = REGEX_TYPES["findutils-default"]
        now = time.time_ns()
        self.start_sec = now // 1000000000
        self.start_nsec = now % 1000000000
        self.cur_day_start = (self.start_sec - 86400, self.start_nsec)
        self.full_days = False
        self.has_action = False
        self.stop_level = False
        self.uid_cache = {}
        self.gid_cache = {}

    # -- output --
    def write(self, b):
        self.out.append(b)
        self.outlen += len(b)
        if self.outlen > 65536:
            self.flush()

    def flush(self):
        if self.out:
            data = b"".join(self.out)
            self.out = []
            self.outlen = 0
            try:
                sys.stdout.buffer.write(data)
                sys.stdout.buffer.flush()
            except BrokenPipeError:
                raise
        else:
            try:
                sys.stdout.buffer.flush()
            except Exception:
                pass

    # -- expression parsing --
    def parse_expression(self, args):
        self.args = args
        self.pos = 0
        if not args:
            return None
        tree = self.p_comma()
        if self.pos < len(args):
            tok = args[self.pos]
            if tok == b")":
                raise FindError("invalid expression; you have too many ')'")
            raise FindError("unexpected extra predicate '%s'" % os.fsdecode(tok))
        return tree

    def peek(self):
        if self.pos < len(self.args):
            return self.args[self.pos]
        return None

    def take(self):
        t = self.args[self.pos]
        self.pos += 1
        return t

    def p_comma(self):
        left = self.p_or()
        while self.peek() == b",":
            self.take()
            if self.peek() is None or self.peek() == b")":
                raise FindError("invalid expression; expected expression "
                                "after ','")
            right = self.p_or()
            left = self.mk_comma(left, right)
        return left

    def p_or(self):
        left = self.p_and()
        while self.peek() in (b"-o", b"-or"):
            op = self.take()
            nxt = self.peek()
            if nxt is None or nxt in (b")", b",", b"-o", b"-or", b"-a",
                                      b"-and"):
                raise FindError("invalid expression; you have used a binary "
                                "operator '%s' with nothing after it."
                                % os.fsdecode(op))
            right = self.p_and()
            left = self.mk_or(left, right)
        return left

    def p_and(self):
        left = self.p_not()
        while True:
            t = self.peek()
            if t in (b"-a", b"-and"):
                op = self.take()
                nxt = self.peek()
                if nxt is None or nxt in (b")", b",", b"-o", b"-or", b"-a",
                                          b"-and"):
                    raise FindError("invalid expression; you have used a "
                                    "binary operator '%s' with nothing "
                                    "after it." % os.fsdecode(op))
                right = self.p_not()
            elif t is None or t in (b")", b"-o", b"-or", b","):
                break
            else:
                right = self.p_not()
            left = self.mk_and(left, right)
        return left

    def p_not(self):
        t = self.peek()
        if t in (b"!", b"-not"):
            self.take()
            nxt = self.peek()
            if nxt is None or nxt in (b")", b",", b"-o", b"-or", b"-a",
                                      b"-and"):
                raise FindError("invalid expression; '%s' must be followed "
                                "by an expression" % os.fsdecode(t))
            sub = self.p_not()
            return self.mk_not(sub)
        return self.p_primary()

    def p_primary(self):
        t = self.peek()
        if t is None:
            raise FindError("invalid expression")
        if t == b"(":
            self.take()
            if self.peek() == b")":
                raise FindError("invalid expression; empty parentheses are "
                                "not allowed.")
            if self.peek() is None:
                raise FindError("invalid expression; I was expecting to find "
                                "a ')' somewhere but did not see one.")
            e = self.p_comma()
            if self.peek() != b")":
                raise FindError("invalid expression; I was expecting to find "
                                "a ')' somewhere but did not see one.")
            self.take()
            return e
        if t in (b")", b"-a", b"-and", b"-o", b"-or", b","):
            raise FindError("invalid expression; you have used a binary "
                            "operator '%s' with nothing before it."
                            % os.fsdecode(t))
        self.take()
        name = os.fsdecode(t)
        fn = PRIMARIES.get(name)
        if fn is None:
            if t.startswith(b"-") and len(t) > 1:
                raise FindError("unknown predicate `%s'" % name)
            raise FindError("paths must precede expression: `%s'" % name)
        return fn(self, name)

    def arg(self, name):
        if self.pos >= len(self.args):
            raise FindError("missing argument to `%s'" % name)
        return self.take()

    # combinators
    @staticmethod
    def mk_and(a, b):
        return lambda e: a(e) and b(e)

    @staticmethod
    def mk_or(a, b):
        return lambda e: a(e) or b(e)

    @staticmethod
    def mk_not(a):
        return lambda e: not a(e)

    @staticmethod
    def mk_comma(a, b):
        def f(e):
            a(e)
            return b(e)
        return f

    # -- traversal --
    def run(self, starts, tree):
        if not self.has_action:
            pr = self.do_print_fn()
            if tree is None:
                tree = pr
            else:
                inner = tree
                tree = lambda e: inner(e) and pr(e)
        self.tree = tree
        try:
            if not starts:
                self.walk_start(b".")
            else:
                for s in starts:
                    self.walk_start(s)
        except Quit:
            pass
        self.flush()

    def walk_start(self, start):
        # findutils opens fts with FTS_VERBATIM: the starting point is used
        # exactly as given (no trimming of repeated trailing slashes).
        path = start
        if start == b"":
            warn("'': No such file or directory")
            self.status = 1
            return
        try:
            st = os.lstat(path)
        except OSError as e:
            warn("'%s': %s" % (os.fsdecode(start), os.strerror(e.errno)))
            self.status = 1
            return
        name = strip_trailing_slashes(base_name(path))
        self.visit(Ent(path, 0, st, name, start))

    def visit(self, ent):
        st = ent.st
        is_dir = stat.S_ISDIR(st.st_mode)
        d = ent.depth
        in_range = d >= self.mindepth
        prune = False
        if not self.depth_first and in_range:
            self.stop_level = False
            self.tree(ent)
            prune = self.stop_level
            self.stop_level = False
        if is_dir and not prune and (self.maxdepth < 0 or d < self.maxdepth):
            try:
                with os.scandir(ent.path) as it:
                    entries = list(it)
            except OSError as e:
                warn("'%s': %s" % (os.fsdecode(ent.path),
                                   os.strerror(e.errno)))
                self.status = 1
                entries = []
            p = ent.path
            prefix = (p[:-1] if p.endswith(b"/") else p) + b"/"
            for de in entries:
                cpath = prefix + de.name
                try:
                    cst = de.stat(follow_symlinks=False)
                except OSError as e:
                    warn("'%s': %s" % (os.fsdecode(cpath),
                                       os.strerror(e.errno)))
                    self.status = 1
                    continue
                self.visit(Ent(cpath, d + 1, cst, de.name, ent.start))
        if self.depth_first and in_range:
            self.tree(ent)

    # -- actions --
    def do_print_fn(self):
        def f(e):
            self.write(e.path + b"\n")
            return True
        return f

    # -- printf rendering --
    def render(self, segs, e):
        parts = []
        for seg in segs:
            k = seg[0]
            if k == "plain":
                parts.append(seg[1])
            elif k == "stop":
                break
            else:
                parts.append(self.directive(seg, e))
        return b"".join(parts)

    def directive(self, seg, e):
        _, spec, conv, aux, raw = seg
        st = e.st
        path = e.path
        if conv == "p":
            return fmt_str(path, spec)
        if conv == "f":
            return fmt_str(base_name(path), spec)
        if conv == "h":
            k = path.rfind(b"/")
            return fmt_str(b"." if k < 0 else path[:k], spec)
        if conv == "P":
            if e.depth > 0:
                cp = path[len(e.start):]
                if cp.startswith(b"/"):
                    cp = cp[1:]
            else:
                cp = b""
            return fmt_str(cp, spec)
        if conv == "H":
            return fmt_str(e.start, spec)
        if conv == "d":
            return fmt_int(e.depth, spec, "d")
        if conv == "s":
            return fmt_str(str(st.st_size).encode(), spec)
        if conv == "y":
            return fmt_str(type_letter(st.st_mode).encode(), spec)
        if conv == "Y":
            if stat.S_ISLNK(st.st_mode):
                try:
                    t = type_letter(os.stat(path).st_mode)
                except OSError as ex:
                    import errno
                    if ex.errno == errno.ELOOP:
                        t = "L"
                    elif ex.errno == errno.ENOENT:
                        t = "N"
                    else:
                        t = "?"
            else:
                t = type_letter(st.st_mode)
            return fmt_str(t.encode(), spec)
        if conv == "m":
            return fmt_int(st.st_mode & 0o7777, spec, "o")
        if conv == "M":
            return fmt_str(filemode_string(st.st_mode).encode(), spec)
        if conv == "l":
            if stat.S_ISLNK(st.st_mode):
                try:
                    tgt = os.readlink(path)
                except OSError:
                    tgt = b""
            else:
                tgt = b""
            return fmt_str(tgt, spec)
        if conv == "n":
            return fmt_str(str(st.st_nlink).encode(), spec)
        if conv == "i":
            return fmt_str(str(st.st_ino).encode(), spec)
        if conv == "U":
            return fmt_str(str(st.st_uid).encode(), spec)
        if conv == "G":
            return fmt_str(str(st.st_gid).encode(), spec)
        if conv == "u":
            return fmt_str(self.user_name(st.st_uid), spec)
        if conv == "g":
            return fmt_str(self.group_name(st.st_gid), spec)
        if conv == "b":
            return fmt_str(str(st.st_blocks).encode(), spec)
        if conv == "k":
            return fmt_str(str(ceil_div(st.st_blocks * 512, 1024)).encode(),
                           spec)
        if conv == "D":
            return fmt_str(str(st.st_dev).encode(), spec)
        if conv == "F":
            return fmt_str(fs_type(st.st_dev), spec)
        if conv == "S":
            if st.st_size == 0:
                v = 1.0 if st.st_blocks == 0 else float("inf")
            else:
                v = (512.0 * st.st_blocks) / st.st_size
            return fmt_float_g(v, raw)
        if conv == "Z":
            return fmt_str(b"", spec)
        if conv in "atc":
            ns = {"a": st.st_atime_ns, "t": st.st_mtime_ns,
                  "c": st.st_ctime_ns}[conv]
            return fmt_str(ctime_format(ns // 1000000000, ns % 1000000000),
                           spec)
        if conv in "ATCB":
            if conv == "B":
                ns = getattr(st, "st_birthtime_ns", None)
                if ns is None:
                    return fmt_str(b"", spec)
            else:
                ns = {"A": st.st_atime_ns, "T": st.st_mtime_ns,
                      "C": st.st_ctime_ns}[conv]
            return fmt_str(format_date(ns // 1000000000, ns % 1000000000,
                                       aux), spec)
        return b""

    def user_name(self, uid):
        r = self.uid_cache.get(uid)
        if r is None:
            try:
                import pwd
                r = pwd.getpwuid(uid).pw_name.encode()
            except Exception:
                r = str(uid).encode()
            self.uid_cache[uid] = r
        return r

    def group_name(self, gid):
        r = self.gid_cache.get(gid)
        if r is None:
            try:
                import grp
                r = grp.getgrgid(gid).gr_name.encode()
            except Exception:
                r = str(gid).encode()
            self.gid_cache[gid] = r
        return r

    def is_empty(self, e):
        m = e.st.st_mode
        if stat.S_ISDIR(m):
            if e._empty is None:
                try:
                    with os.scandir(e.path) as it:
                        e._empty = next(iter(it), None) is None
                except OSError as ex:
                    warn("'%s': %s" % (os.fsdecode(e.path),
                                       os.strerror(ex.errno)))
                    self.status = 1
                    e._empty = False
            return e._empty
        if stat.S_ISREG(m):
            return e.st.st_size == 0
        return False


# ---------------------------------------------------------------------------
# Numeric argument helpers
# ---------------------------------------------------------------------------

_UINT_RE = re.compile(rb"^[ \t\n\v\f\r]*\+?[0-9]+$")
_FLOAT_RE = re.compile(
    rb"^[ \t\n\v\f\r]*[+-]?(?:(?:[0-9]+\.?[0-9]*|\.[0-9]+)(?:[eE][+-]?[0-9]+)?"
    rb"|[iI][nN][fF](?:[iI][nN][iI][tT][yY])?|[nN][aA][nN])$")


def get_comp(s):
    if s[:1] == b"+":
        return "gt", s[1:]
    if s[:1] == b"-":
        return "lt", s[1:]
    return "eq", s


def get_num(s):
    """Parse [+-]N as GNU find's get_num: returns (kind, value) or None."""
    kind, rest = get_comp(s)
    if not _UINT_RE.match(rest):
        return None
    v = int(rest.strip().lstrip(b"+"))
    if v > 0xFFFFFFFFFFFFFFFF:
        return None
    return kind, v


def cmp_num(kind, val, ref):
    if kind == "gt":
        return val > ref
    if kind == "lt":
        return val < ref
    return val == ref


# ---------------------------------------------------------------------------
# Primaries
# ---------------------------------------------------------------------------

PRIMARIES = {}


def primary(*names):
    def deco(fn):
        for n in names:
            PRIMARIES[n] = fn
        return fn
    return deco


def _true(e):
    return True


def _false(e):
    return False


@primary("-true")
def p_true(f, name):
    return _true


@primary("-false")
def p_false(f, name):
    return _false


@primary("-depth", "-d")
def p_depth(f, name):
    f.depth_first = True
    return _true


@primary("-maxdepth", "-mindepth")
def p_maxdepth(f, name):
    a = f.arg(name)
    if a and all(48 <= c <= 57 for c in a):
        v = int(a)
        if v <= 2147483647:
            if name == "-maxdepth":
                f.maxdepth = v
            else:
                f.mindepth = v
            return _true
    raise FindError("Expected a positive decimal integer argument to %s, "
                    "but got '%s'" % (name, os.fsdecode(a)))


@primary("-noleaf", "-xdev", "-mount", "-ignore_readdir_race",
         "-noignore_readdir_race", "-warn", "-nowarn")
def p_noop_option(f, name):
    return _true


@primary("-daystart")
def p_daystart(f, name):
    if not f.full_days:
        sec, nsec = f.cur_day_start
        sec += 86400
        tm = time.localtime(sec)
        sec -= tm.tm_sec + tm.tm_min * 60 + tm.tm_hour * 3600
        f.cur_day_start = (sec, nsec)
        f.full_days = True
    return _true


@primary("-regextype")
def p_regextype(f, name):
    a = os.fsdecode(f.arg(name))
    if a not in REGEX_TYPES or REGEX_TYPES[a] is None:
        raise FindError("Unknown regular expression type '%s'" % a)
    f.regex_syntax = REGEX_TYPES[a]
    return _true


@primary("-name", "-iname")
def p_name(f, name):
    pat = f.arg(name)
    rx = fnmatch_compile(pat, name == "-iname")
    m = rx.fullmatch
    return lambda e: m(e.name) is not None


@primary("-path", "-ipath", "-wholename", "-iwholename")
def p_path(f, name):
    pat = f.arg(name)
    rx = fnmatch_compile(pat, name in ("-ipath", "-iwholename"))
    m = rx.fullmatch
    return lambda e: m(e.path) is not None


@primary("-lname", "-ilname")
def p_lname(f, name):
    pat = f.arg(name)
    rx = fnmatch_compile(pat, name == "-ilname")

    def t(e):
        if not stat.S_ISLNK(e.st.st_mode):
            return False
        try:
            tgt = os.readlink(e.path)
        except OSError:
            return False
        return rx.fullmatch(tgt) is not None
    return t


@primary("-regex", "-iregex")
def p_regex(f, name):
    pat = f.arg(name)
    syn = f.regex_syntax
    if name == "-iregex":
        syn |= RE_ICASE
    try:
        rx = GnuRegex(pat, syn).compile()
    except RegexError as ex:
        raise FindError("%s" % ex)
    m = rx.fullmatch
    return lambda e: m(e.path) is not None


TYPE_TESTS = {
    ord("f"): stat.S_ISREG,
    ord("d"): stat.S_ISDIR,
    ord("l"): stat.S_ISLNK,
    ord("b"): stat.S_ISBLK,
    ord("c"): stat.S_ISCHR,
    ord("p"): stat.S_ISFIFO,
    ord("s"): stat.S_ISSOCK,
    ord("D"): lambda m: False,
}


@primary("-type", "-xtype")
def p_type(f, name):
    a = f.arg(name)
    if not a:
        raise FindError("Arguments to %s should contain at least one letter"
                        % name)
    tests = []
    seen = set()
    i = 0
    while True:
        c = a[i]
        if c not in TYPE_TESTS:
            raise FindError("Unknown argument to %s: %c" % (name, c))
        if c in seen:
            raise FindError("Duplicate file type '%c' in the argument list "
                            "to %s." % (c, name))
        seen.add(c)
        tests.append(TYPE_TESTS[c])
        i += 1
        if i >= len(a):
            break
        if a[i] != 44:
            raise FindError("Must separate multiple arguments to %s using: ','"
                            % name)
        i += 1
        if i >= len(a):
            raise FindError("Last file type in list argument to %s is "
                            "missing, i.e., list is ending on: ','" % name)
    if name == "-xtype":
        def t(e):
            m = e.st.st_mode
            if stat.S_ISLNK(m):
                try:
                    m = os.stat(e.path).st_mode
                except OSError:
                    pass
            return any(x(m) for x in tests)
        return t
    if len(tests) == 1:
        t0 = tests[0]
        return lambda e: t0(e.st.st_mode)
    return lambda e: any(x(e.st.st_mode) for x in tests)


SIZE_UNITS = {ord("b"): 512, ord("c"): 1, ord("w"): 2, ord("k"): 1024,
              ord("M"): 1048576, ord("G"): 1073741824}


@primary("-size")
def p_size(f, name):
    a = f.arg(name)
    if not a:
        raise FindError("invalid null argument to -size")
    last = a[-1]
    blk = 512
    num = a
    if last in SIZE_UNITS:
        blk = SIZE_UNITS[last]
        num = a[:-1]
    elif not _isdigit(last):
        raise FindError("invalid -size type `%c'" % last)
    r = get_num(num)
    if r is None:
        raise FindError("invalid argument `%s' to `-size'" % os.fsdecode(a))
    kind, val = r

    def t(e):
        sz = e.st.st_size
        fv = sz // blk + (1 if sz % blk else 0)
        return cmp_num(kind, fv, val)
    return t


@primary("-empty")
def p_empty(f, name):
    return lambda e: f.is_empty(e)


@primary("-links")
def p_links(f, name):
    a = f.arg(name)
    r = get_num(a)
    if r is None:
        raise FindError("invalid argument `%s' to `-links'" % os.fsdecode(a))
    kind, val = r
    return lambda e: cmp_num(kind, e.st.st_nlink, val)


@primary("-inum")
def p_inum(f, name):
    a = f.arg(name)
    r = get_num(a)
    if r is None:
        raise FindError("invalid argument `%s' to `-inum'" % os.fsdecode(a))
    kind, val = r
    return lambda e: cmp_num(kind, e.st.st_ino, val)


@primary("-uid", "-gid")
def p_uid(f, name):
    a = f.arg(name)
    r = get_num(a)
    if r is None:
        raise FindError("invalid argument `%s' to `%s'"
                        % (os.fsdecode(a), name))
    kind, val = r
    if name == "-uid":
        return lambda e: cmp_num(kind, e.st.st_uid, val)
    return lambda e: cmp_num(kind, e.st.st_gid, val)


@primary("-user")
def p_user(f, name):
    a = f.arg(name)
    try:
        import pwd
        uid = pwd.getpwnam(os.fsdecode(a)).pw_uid
    except Exception:
        if a and all(_isdigit(c) for c in a):
            uid = int(a)
        else:
            raise FindError("'%s' is not the name of a known user"
                            % os.fsdecode(a))
    return lambda e: e.st.st_uid == uid


@primary("-group")
def p_group(f, name):
    a = f.arg(name)
    try:
        import grp
        gid = grp.getgrnam(os.fsdecode(a)).gr_gid
    except Exception:
        if a and all(_isdigit(c) for c in a):
            gid = int(a)
        else:
            raise FindError("'%s' is not the name of an existing group"
                            % os.fsdecode(a))
    return lambda e: e.st.st_gid == gid


@primary("-nouser", "-nogroup")
def p_nouser(f, name):
    def t(e):
        try:
            if name == "-nouser":
                import pwd
                pwd.getpwuid(e.st.st_uid)
            else:
                import grp
                grp.getgrgid(e.st.st_gid)
            return False
        except KeyError:
            return True
        except Exception:
            return False
    return t


@primary("-readable", "-writable", "-executable")
def p_access(f, name):
    mode = {"-readable": os.R_OK, "-writable": os.W_OK,
            "-executable": os.X_OK}[name]
    return lambda e: os.access(e.path, mode)


@primary("-perm")
def p_perm(f, name):
    a = f.arg(name)
    kind = "exact"
    start = 0
    if a[:1] == b"-":
        kind = "least"
        start = 1
    elif a[:1] == b"/":
        kind = "any"
        start = 1
    change = mode_compile(a[start:])
    if change is None or (a[:1] == b"+" and len(a) > 1 and 48 <= a[1] < 56):
        raise FindError("invalid mode '%s'" % os.fsdecode(a))
    vals = (mode_adjust(0, False, 0, change), mode_adjust(0, True, 0, change))

    def t(e):
        mode = e.st.st_mode
        pv = vals[1 if stat.S_ISDIR(mode) else 0]
        if kind == "least":
            return (mode & pv) == pv
        if kind == "any":
            return pv == 0 or (mode & pv) != 0
        return (mode & 0o7777) == pv
    return t


def _relative_timestamp(f, s, origin, unit, name):
    kind, rest = get_comp(s)
    if kind == "lt":
        kind = "gt"
    elif kind == "gt":
        kind = "lt"
    if not _FLOAT_RE.match(rest):
        raise FindError("invalid argument `%s' to `%s'"
                        % (os.fsdecode(s), name))
    try:
        offset = float(rest.strip())
    except ValueError:
        raise FindError("invalid argument `%s' to `%s'"
                        % (os.fsdecode(s), name))
    x = offset * unit
    if x != x or x in (float("inf"), float("-inf")):
        raise FindError("arithmetic overflow while converting %s to a "
                        "number of seconds" % os.fsdecode(s))
    import math
    frac, whole = math.modf(x)
    nanosec = frac * 1.0e9
    osec, onsec = origin
    rsec = int(osec - whole)
    rnsec = int(onsec - nanosec)
    if onsec < nanosec:
        rnsec += 1000000000
        rsec -= 1
    return kind, rsec * 1000000000 + rnsec


def _time_attr(letter):
    return {"a": "st_atime_ns", "c": "st_ctime_ns", "m": "st_mtime_ns"}[letter]


@primary("-mtime", "-atime", "-ctime")
def p_xtime(f, name):
    a = f.arg(name)
    attr = _time_attr(name[1])
    origin = f.cur_day_start
    kind0, _ = get_comp(a)
    if kind0 == "lt":
        origin = (origin[0] + 86399, origin[1])
    kind, ref = _relative_timestamp(f, a, origin, 86400, name)
    return _timewindow(kind, ref, attr, 86400)


@primary("-mmin", "-amin", "-cmin")
def p_xmin(f, name):
    a = f.arg(name)
    attr = _time_attr(name[1])
    origin = (f.cur_day_start[0] + 86400, f.cur_day_start[1])
    kind, ref = _relative_timestamp(f, a, origin, 60, name)
    return _timewindow(kind, ref, attr, 60)


def _timewindow(kind, ref, attr, window):
    wns = window * 1000000000
    if kind == "gt":
        return lambda e: getattr(e.st, attr) > ref
    if kind == "lt":
        return lambda e: getattr(e.st, attr) < ref

    def t(e):
        delta = getattr(e.st, attr) - ref
        return 0 < delta <= wns
    return t


@primary("-newer", "-anewer", "-cnewer")
def p_newer(f, name):
    a = f.arg(name)
    try:
        st = os.lstat(a)
    except OSError as ex:
        raise FindError("'%s': %s" % (os.fsdecode(a), os.strerror(ex.errno)))
    ref = st.st_mtime_ns
    attr = {"-newer": "st_mtime_ns", "-anewer": "st_atime_ns",
            "-cnewer": "st_ctime_ns"}[name]
    return lambda e: getattr(e.st, attr) > ref


@primary("-samefile")
def p_samefile(f, name):
    a = f.arg(name)
    try:
        st = os.lstat(a)
    except OSError as ex:
        raise FindError("'%s': %s" % (os.fsdecode(a), os.strerror(ex.errno)))
    return lambda e: e.st.st_ino == st.st_ino and e.st.st_dev == st.st_dev


@primary("-print")
def p_print(f, name):
    f.has_action = True
    return f.do_print_fn()


@primary("-print0")
def p_print0(f, name):
    f.has_action = True

    def t(e):
        f.write(e.path + b"\0")
        return True
    return t


@primary("-printf")
def p_printf(f, name):
    a = f.arg(name)
    f.has_action = True
    segs = parse_printf_format(a)

    def t(e):
        f.write(f.render(segs, e))
        return True
    return t


@primary("-prune")
def p_prune(f, name):
    def t(e):
        if not f.depth_first and stat.S_ISDIR(e.st.st_mode):
            f.stop_level = True
        return True
    return t


@primary("-quit")
def p_quit(f, name):
    def t(e):
        raise Quit()
    return t


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def looks_like_expression(arg, leading):
    if not arg:
        return False
    c = arg[0]
    if c == 45:
        return len(arg) > 1
    if c in (41, 44):
        if len(arg) > 1:
            return False
        return not leading
    if c in (33, 40):
        return len(arg) == 1
    return False


def main(argv):
    sys.setrecursionlimit(100000)
    args = [os.fsencode(a) for a in argv]
    i = 0
    while i < len(args):
        a = args[i]
        if a in (b"-P", b"-H", b"-L"):
            i += 1
            continue
        if a == b"-D":
            i += 2
            continue
        if a.startswith(b"-O") and len(a) > 2:
            i += 1
            continue
        if a == b"--":
            i += 1
        break
    starts = []
    while i < len(args) and not looks_like_expression(args[i], True):
        starts.append(args[i])
        i += 1
    expr = args[i:]
    f = Find()
    try:
        tree = f.parse_expression(expr)
    except FindError as ex:
        warn(str(ex))
        return 1
    try:
        f.run(starts, tree)
    except BrokenPipeError:
        return 1
    return f.status


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
