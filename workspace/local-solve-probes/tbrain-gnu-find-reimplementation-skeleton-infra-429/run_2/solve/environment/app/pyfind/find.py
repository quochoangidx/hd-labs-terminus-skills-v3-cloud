"""pyfind: a GNU find 4.9.0 replacement in pure Python.

Usage: python3 /app/pyfind/find.py [starting-point...] [expression]

Symbolic links are never followed (the default -P behaviour).  All path
handling is done on bytes so that output matches GNU find byte for byte.
"""

import math
import os
import re
import stat
import sys
import time

PROG = "find"


# ---------------------------------------------------------------------------
# Errors and output
# ---------------------------------------------------------------------------

class FatalError(Exception):
    pass


class QuitNow(Exception):
    pass


def warn(msg):
    try:
        sys.stderr.write("%s: %s\n" % (PROG, msg))
        sys.stderr.flush()
    except Exception:
        pass


def qs(b):
    if isinstance(b, bytes):
        b = os.fsdecode(b)
    return "'" + b + "'"


class Output:
    def __init__(self):
        self.out = sys.stdout.buffer
        self.parts = []
        self.size = 0

    def write(self, data):
        if data:
            self.parts.append(data)
            self.size += len(data)
            if self.size > 65536:
                self.flush()

    def flush(self):
        if self.parts:
            try:
                self.out.write(b"".join(self.parts))
                self.out.flush()
            except BrokenPipeError:
                pass
            self.parts = []
            self.size = 0


OUT = None


# ---------------------------------------------------------------------------
# Global state
# ---------------------------------------------------------------------------

class Options:
    def __init__(self):
        self.maxdepth = None
        self.mindepth = 0
        self.depth_first = False
        self.regex_syntax = None  # set after syntax table is defined
        self.start_ns = time.time_ns()
        self.cur_day_start_ns = self.start_ns - 86400 * 10 ** 9
        self.full_days = False
        self.exit_status = 0


OPTS = None


# ---------------------------------------------------------------------------
# Path helpers (gnulib semantics)
# ---------------------------------------------------------------------------

def last_component(name):
    i = 0
    n = len(name)
    while i < n and name[i:i + 1] == b"/":
        i += 1
    base = i
    last_was_slash = False
    p = i
    while p < n:
        if name[p:p + 1] == b"/":
            last_was_slash = True
        elif last_was_slash:
            base = p
            last_was_slash = False
        p += 1
    return name[base:]


def base_len(name):
    ln = len(name)
    while ln > 1 and name[ln - 1:ln] == b"/":
        ln -= 1
    return ln


def base_name(name):
    base = last_component(name)
    if not base:
        return name[:base_len(name)]
    length = base_len(base)
    if length < len(base) and base[length:length + 1] == b"/":
        length += 1
    return base[:length]


def match_name(path):
    b = base_name(path)
    lc = last_component(b)
    if not lc:
        lc = b
    # strip_trailing_slashes operates on the whole string: keep the prefix
    prefix = b[:len(b) - len(lc)]
    return prefix + lc[:base_len(lc)]


# ---------------------------------------------------------------------------
# fnmatch (port of glibc fnmatch, flags 0 or FNM_CASEFOLD)
# ---------------------------------------------------------------------------

def _lower(c):
    if 65 <= c <= 90:
        return c + 32
    return c


def _cclass(name, c):
    if name == b"alnum":
        return (48 <= c <= 57) or (65 <= c <= 90) or (97 <= c <= 122)
    if name == b"alpha":
        return (65 <= c <= 90) or (97 <= c <= 122)
    if name == b"blank":
        return c in (32, 9)
    if name == b"cntrl":
        return c < 32 or c == 127
    if name == b"digit":
        return 48 <= c <= 57
    if name == b"graph":
        return 33 <= c <= 126
    if name == b"lower":
        return 97 <= c <= 122
    if name == b"print":
        return 32 <= c <= 126
    if name == b"punct":
        return 33 <= c <= 126 and not ((48 <= c <= 57) or (65 <= c <= 90) or (97 <= c <= 122))
    if name == b"space":
        return c in (32, 9, 10, 11, 12, 13)
    if name == b"upper":
        return 65 <= c <= 90
    if name == b"xdigit":
        return (48 <= c <= 57) or (65 <= c <= 70) or (97 <= c <= 102)
    return None


CLASS_NAMES = (b"alnum", b"alpha", b"blank", b"cntrl", b"digit", b"graph",
               b"lower", b"print", b"punct", b"space", b"upper", b"xdigit")


def fnmatch(pat, s, fold):
    P = pat + b"\0"   # sentinel NUL like C strings
    plen = len(pat)
    slen = len(s)

    def F(c):
        return _lower(c) if fold else c

    def m(pi, si):
        while pi < plen:
            c = P[pi]
            pi += 1
            c = F(c)
            if c == 63:  # '?'
                if si == slen:
                    return False
                si += 1
            elif c == 92:  # '\\'
                c = P[pi]
                pi += 1
                if c == 0:
                    return False
                c = F(c)
                if si == slen or F(s[si]) != c:
                    return False
                si += 1
            elif c == 42:  # '*'
                c = P[pi]
                pi += 1
                while c == 63 or c == 42:
                    if c == 63:
                        if si == slen:
                            return False
                        si += 1
                    c = P[pi]
                    pi += 1
                if c == 0:
                    return True
                if c == 91:  # '['
                    start = pi - 1
                    for n in range(si, slen):
                        if m(start, n):
                            return True
                else:
                    start = pi - 1
                    if c == 92:
                        c = P[pi]
                    c = F(c)
                    for n in range(si, slen):
                        if F(s[n]) == c and m(start, n):
                            return True
                return False
            elif c == 91:  # '['
                if si == slen:
                    return False
                p_init = pi
                p = pi
                negate = P[p] in (33, 94)
                if negate:
                    p += 1
                fn = F(s[si])
                orig = s[si]
                c = P[p]
                p += 1
                matched = False
                literal_bracket = False
                while True:
                    goto_normal = False
                    if c == 92:
                        if P[p] == 0:
                            return False
                        c = F(P[p])
                        p += 1
                        goto_normal = True
                    elif c == 91 and P[p] == 58:  # '[:'
                        startp = p
                        name = bytearray()
                        q = p
                        ok = True
                        while True:
                            if len(name) >= 256:
                                return False
                            q += 1
                            cc = P[q]
                            if cc == 58 and P[q + 1] == 93:
                                q += 2
                                break
                            if cc < 97 or cc >= 122:
                                ok = False
                                break
                            name.append(cc)
                        if not ok:
                            p = startp
                            c = 91
                            goto_normal = True
                        else:
                            p = q
                            res = _cclass(bytes(name), orig)
                            if res is None:
                                return False
                            if res:
                                matched = True
                                break
                            c = P[p]
                            p += 1
                            if c == 93:
                                break
                            continue
                    elif c == 0:
                        literal_bracket = True
                        break
                    else:
                        if c == 91 and P[p] in (46, 61):  # '[.' or '[='
                            delim = P[p]
                            q = p + 1
                            if P[q] != 0 and P[q + 1] == delim and P[q + 2] == 93:
                                c = P[q]
                                p = q + 3
                                c = F(c)
                                # fallthrough into normal handling below
                                goto_normal = True
                            else:
                                c = F(c)
                                goto_normal = True
                        else:
                            c = F(c)
                            goto_normal = True
                    if goto_normal:
                        is_range = (P[p] == 45 and P[p + 1] != 0 and P[p + 1] != 93)
                        if not is_range and c == fn:
                            matched = True
                            break
                        cold = c
                        c = P[p]
                        p += 1
                        if c == 45 and P[p] != 93:
                            cend = P[p]
                            p += 1
                            if cend == 91 and P[p] in (46, 61):
                                delim = P[p]
                                q = p + 1
                                if P[q] != 0 and P[q + 1] == delim and P[q + 2] == 93:
                                    cend = P[q]
                                    p = q + 3
                            elif cend == 92:
                                cend = P[p]
                                p += 1
                            if cend == 0:
                                return False
                            cend = F(cend)
                            if cold <= fn <= cend:
                                matched = True
                                break
                            c = P[p]
                            p += 1
                        if c == 93:
                            break
                if literal_bracket:
                    pi = p_init
                    if si == slen or F(s[si]) != 91:
                        return False
                    si += 1
                    continue
                if matched:
                    # skip rest of bracket
                    while True:
                        c = P[p]
                        p += 1
                        if c == 0:
                            return False
                        if c == 92:
                            if P[p] == 0:
                                return False
                            p += 1
                        elif c == 91 and P[p] == 58:
                            q = p
                            startp = p
                            ok = True
                            cnt = 0
                            while True:
                                q += 1
                                cnt += 1
                                if cnt >= 256:
                                    return False
                                if P[q] == 58 and P[q + 1] == 93:
                                    break
                                cc = P[q]
                                if cc < 97 or cc >= 122:
                                    ok = False
                                    break
                            if ok:
                                p = q + 2
                            else:
                                p = startp
                        elif c == 93:
                            break
                    if negate:
                        return False
                else:
                    if not negate:
                        return False
                pi = p
                si += 1
            else:
                if si == slen or c != F(s[si]):
                    return False
                si += 1
        return si == slen

    return m(0, 0)


# ---------------------------------------------------------------------------
# GNU regex -> Python regex translation
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
RE_INVALID_INTERVAL_ORD = 1 << 21
RE_ICASE = 1 << 22
RE_CARET_ANCHORS_HERE = 1 << 23
RE_CONTEXT_INVALID_DUP = 1 << 24

_POSIX_COMMON = (RE_CHAR_CLASSES | RE_DOT_NEWLINE | RE_DOT_NOT_NULL
                 | RE_INTERVALS | RE_NO_EMPTY_RANGES)
RE_SYNTAX_EMACS = 0
RE_SYNTAX_POSIX_BASIC = _POSIX_COMMON | RE_BK_PLUS_QM | RE_CONTEXT_INVALID_DUP
RE_SYNTAX_POSIX_MINIMAL_BASIC = _POSIX_COMMON | RE_LIMITED_OPS
RE_SYNTAX_POSIX_EXTENDED = (_POSIX_COMMON | RE_CONTEXT_INDEP_ANCHORS
                            | RE_CONTEXT_INDEP_OPS | RE_NO_BK_BRACES
                            | RE_NO_BK_PARENS | RE_NO_BK_VBAR
                            | RE_CONTEXT_INVALID_OPS
                            | RE_UNMATCHED_RIGHT_PAREN_ORD)
RE_SYNTAX_AWK = (RE_BACKSLASH_ESCAPE_IN_LISTS | RE_DOT_NOT_NULL
                 | RE_NO_BK_PARENS | RE_NO_BK_REFS | RE_NO_BK_VBAR
                 | RE_NO_EMPTY_RANGES | RE_DOT_NEWLINE
                 | RE_CONTEXT_INDEP_ANCHORS | RE_CHAR_CLASSES
                 | RE_UNMATCHED_RIGHT_PAREN_ORD | RE_NO_GNU_OPS)
RE_SYNTAX_GNU_AWK = ((RE_SYNTAX_POSIX_EXTENDED | RE_BACKSLASH_ESCAPE_IN_LISTS
                      | RE_INVALID_INTERVAL_ORD)
                     & ~(RE_DOT_NOT_NULL | RE_CONTEXT_INDEP_OPS
                         | RE_CONTEXT_INVALID_OPS))
RE_SYNTAX_POSIX_AWK = (RE_SYNTAX_POSIX_EXTENDED | RE_BACKSLASH_ESCAPE_IN_LISTS
                       | RE_INTERVALS | RE_NO_GNU_OPS
                       | RE_INVALID_INTERVAL_ORD)
RE_SYNTAX_GREP = ((RE_SYNTAX_POSIX_BASIC | RE_NEWLINE_ALT)
                  & ~(RE_CONTEXT_INVALID_DUP | RE_DOT_NOT_NULL))
RE_SYNTAX_EGREP = ((RE_SYNTAX_POSIX_EXTENDED | RE_INVALID_INTERVAL_ORD
                    | RE_NEWLINE_ALT)
                   & ~(RE_CONTEXT_INVALID_OPS | RE_DOT_NOT_NULL))
RE_SYNTAX_POSIX_EGREP = RE_SYNTAX_EGREP
RE_SYNTAX_ED = RE_SYNTAX_POSIX_BASIC
RE_SYNTAX_SED = RE_SYNTAX_POSIX_BASIC

REGEX_TYPES = {
    "findutils-default": RE_SYNTAX_EMACS | RE_DOT_NEWLINE,
    "ed": RE_SYNTAX_ED,
    "emacs": RE_SYNTAX_EMACS,
    "gnu-awk": RE_SYNTAX_GNU_AWK,
    "grep": RE_SYNTAX_GREP,
    "posix-awk": RE_SYNTAX_POSIX_AWK,
    "awk": RE_SYNTAX_AWK,
    "posix-basic": RE_SYNTAX_POSIX_BASIC,
    "posix-egrep": RE_SYNTAX_POSIX_EGREP,
    "egrep": RE_SYNTAX_EGREP,
    "posix-extended": RE_SYNTAX_POSIX_EXTENDED,
    "posix-minimal-basic": RE_SYNTAX_POSIX_MINIMAL_BASIC,
    "sed": RE_SYNTAX_SED,
}

# token types
T_CHAR, T_END, T_BACKSLASH_END, T_ALT, T_STAR, T_PLUS, T_QUESTION, \
    T_OPEN_DUP, T_CLOSE_DUP, T_OPEN_GROUP, T_CLOSE_GROUP, T_BRACKET, \
    T_PERIOD, T_ANCHOR, T_BACKREF, T_WORD, T_NOTWORD, T_SPACE, \
    T_NOTSPACE = range(19)

A_LINE_FIRST, A_LINE_LAST, A_BUF_FIRST, A_BUF_LAST, A_WORD_FIRST, \
    A_WORD_LAST, A_WORD_DELIM, A_NOT_WORD_DELIM = range(8)

WORDSET = b"0-9A-Za-z_"


class RegexError(Exception):
    pass


def _upper(c):
    if 97 <= c <= 122:
        return c - 32
    return c


class Tok:
    __slots__ = ("type", "c", "len", "aux")

    def __init__(self, type_, c, ln, aux=None):
        self.type = type_
        self.c = c
        self.len = ln
        self.aux = aux


class GnuRegexCompiler:
    def __init__(self, pattern, syntax, icase):
        self.orig = pattern
        self.icase = icase
        self.buf = bytes(_upper(c) for c in pattern) if icase else pattern
        self.n = len(pattern)
        self.syntax = syntax
        self.pos = 0
        self.nsub = 0
        self.completed = set()

    # -- tokenizer ---------------------------------------------------------
    def peek(self, pos, syntax):
        buf = self.buf
        if pos >= self.n:
            return Tok(T_END, 0, 0)
        c = buf[pos]
        if c == 92:  # backslash
            if pos + 1 >= self.n:
                return Tok(T_BACKSLASH_END, c, 1)
            c2o = self.orig[pos + 1]
            c2 = buf[pos + 1]
            t = Tok(T_CHAR, c2, 2)
            ch = chr(c2o)
            if ch == "|":
                if not (syntax & RE_LIMITED_OPS) and not (syntax & RE_NO_BK_VBAR):
                    t.type = T_ALT
            elif "1" <= ch <= "9":
                if not (syntax & RE_NO_BK_REFS):
                    t.type = T_BACKREF
                    t.aux = c2o - 48
            elif ch in "<>bB`'":
                if not (syntax & RE_NO_GNU_OPS):
                    t.type = T_ANCHOR
                    t.aux = {"<": A_WORD_FIRST, ">": A_WORD_LAST,
                             "b": A_WORD_DELIM, "B": A_NOT_WORD_DELIM,
                             "`": A_BUF_FIRST, "'": A_BUF_LAST}[ch]
            elif ch in "wWsS":
                if not (syntax & RE_NO_GNU_OPS):
                    t.type = {"w": T_WORD, "W": T_NOTWORD,
                              "s": T_SPACE, "S": T_NOTSPACE}[ch]
            elif ch == "(":
                if not (syntax & RE_NO_BK_PARENS):
                    t.type = T_OPEN_GROUP
            elif ch == ")":
                if not (syntax & RE_NO_BK_PARENS):
                    t.type = T_CLOSE_GROUP
            elif ch == "+":
                if not (syntax & RE_LIMITED_OPS) and (syntax & RE_BK_PLUS_QM):
                    t.type = T_PLUS
            elif ch == "?":
                if not (syntax & RE_LIMITED_OPS) and (syntax & RE_BK_PLUS_QM):
                    t.type = T_QUESTION
            elif ch == "{":
                if (syntax & RE_INTERVALS) and not (syntax & RE_NO_BK_BRACES):
                    t.type = T_OPEN_DUP
            elif ch == "}":
                if (syntax & RE_INTERVALS) and not (syntax & RE_NO_BK_BRACES):
                    t.type = T_CLOSE_DUP
            return t
        t = Tok(T_CHAR, c, 1)
        ch = chr(c)
        if ch == "\n":
            if syntax & RE_NEWLINE_ALT:
                t.type = T_ALT
        elif ch == "|":
            if not (syntax & RE_LIMITED_OPS) and (syntax & RE_NO_BK_VBAR):
                t.type = T_ALT
        elif ch == "*":
            t.type = T_STAR
        elif ch == "+":
            if not (syntax & RE_LIMITED_OPS) and not (syntax & RE_BK_PLUS_QM):
                t.type = T_PLUS
        elif ch == "?":
            if not (syntax & RE_LIMITED_OPS) and not (syntax & RE_BK_PLUS_QM):
                t.type = T_QUESTION
        elif ch == "{":
            if (syntax & RE_INTERVALS) and (syntax & RE_NO_BK_BRACES):
                t.type = T_OPEN_DUP
        elif ch == "}":
            if (syntax & RE_INTERVALS) and (syntax & RE_NO_BK_BRACES):
                t.type = T_CLOSE_DUP
        elif ch == "(":
            if syntax & RE_NO_BK_PARENS:
                t.type = T_OPEN_GROUP
        elif ch == ")":
            if syntax & RE_NO_BK_PARENS:
                t.type = T_CLOSE_GROUP
        elif ch == "[":
            t.type = T_BRACKET
        elif ch == ".":
            t.type = T_PERIOD
        elif ch == "^":
            if not (syntax & (RE_CONTEXT_INDEP_ANCHORS | RE_CARET_ANCHORS_HERE)) and pos != 0:
                prev = buf[pos - 1]
                if not (syntax & RE_NEWLINE_ALT) or prev != 10:
                    return t
            t.type = T_ANCHOR
            t.aux = A_LINE_FIRST
        elif ch == "$":
            if not (syntax & RE_CONTEXT_INDEP_ANCHORS) and pos + 1 != self.n:
                nxt = self.peek(pos + 1, syntax)
                if nxt.type not in (T_ALT, T_CLOSE_GROUP):
                    return t
            t.type = T_ANCHOR
            t.aux = A_LINE_LAST
        return t

    def fetch(self, syntax):
        t = self.peek(self.pos, syntax)
        self.pos += t.len
        return t

    # -- parser ------------------------------------------------------------
    def compile(self):
        syntax = self.syntax
        tok = self.fetch(syntax | RE_CARET_ANCHORS_HERE)
        tree, tok = self.parse_reg_exp(tok, syntax, 0)
        if tok.type != T_END:
            raise RegexError("Unmatched ) or \\)")
        return tree if tree is not None else b""

    def parse_reg_exp(self, tok, syntax, nest):
        initial = set(self.completed)
        branches = []
        tree, tok = self.parse_branch(tok, syntax, nest)
        branches.append(tree)
        while tok.type == T_ALT:
            tok = self.fetch(syntax | RE_CARET_ANCHORS_HERE)
            if tok.type != T_ALT and tok.type != T_END and \
                    (nest == 0 or tok.type != T_CLOSE_GROUP):
                accumulated = set(self.completed)
                self.completed = set(initial)
                br, tok = self.parse_branch(tok, syntax, nest)
                self.completed |= accumulated
            else:
                br = None
            branches.append(br)
        if len(branches) == 1:
            return branches[0], tok
        return b"(?:" + b"|".join(b if b is not None else b"" for b in branches) + b")", tok

    def parse_branch(self, tok, syntax, nest):
        parts = []
        tree, tok = self.parse_expression(tok, syntax, nest)
        if tree is not None:
            parts.append(tree)
        while tok.type != T_ALT and tok.type != T_END and \
                (nest == 0 or tok.type != T_CLOSE_GROUP):
            t2, tok = self.parse_expression(tok, syntax, nest)
            if t2 is not None:
                parts.append(t2)
        if not parts:
            return None, tok
        return b"".join(parts), tok

    def char_re(self, c):
        return b"\\x%02x" % c

    def parse_expression(self, tok, syntax, nest):
        tt = tok.type
        if tt == T_CHAR:
            tree = self.char_re(tok.c)
        elif tt == T_PERIOD:
            excl = set()
            if not (syntax & RE_DOT_NEWLINE):
                excl.add(10)
            if syntax & RE_DOT_NOT_NULL:
                excl.add(0)
            tree = self.set_re(set(range(256)) - excl)
        elif tt == T_BRACKET:
            tree = self.parse_bracket(syntax)
        elif tt == T_BACKREF:
            if tok.aux not in self.completed:
                raise RegexError("Invalid back reference")
            tree = b"(?P=g%d)" % tok.aux
        elif tt == T_OPEN_GROUP:
            tree = self.parse_sub_exp(syntax, nest + 1)
        elif tt in (T_OPEN_DUP, T_STAR, T_PLUS, T_QUESTION, T_CLOSE_GROUP, T_CLOSE_DUP):
            if tt == T_OPEN_DUP and (syntax & RE_CONTEXT_INVALID_DUP):
                raise RegexError("Invalid preceding regular expression")
            if tt in (T_OPEN_DUP, T_STAR, T_PLUS, T_QUESTION):
                if (syntax & RE_CONTEXT_INVALID_OPS) and not (syntax & RE_CONTEXT_INVALID_DUP):
                    raise RegexError("Invalid preceding regular expression")
                elif syntax & RE_CONTEXT_INDEP_OPS:
                    tok = self.fetch(syntax)
                    return self.parse_expression(tok, syntax, nest)
            if tt == T_CLOSE_GROUP and not (syntax & RE_UNMATCHED_RIGHT_PAREN_ORD):
                raise RegexError("Unmatched ) or \\)")
            tree = self.char_re(tok.c)
        elif tt == T_ANCHOR:
            a = tok.aux
            W = b"[" + WORDSET + b"]"
            if a == A_LINE_FIRST:
                tree = b"(?:\\A|(?<=\\n))"
            elif a == A_LINE_LAST:
                tree = b"(?:\\Z|(?=\\n))"
            elif a == A_BUF_FIRST:
                tree = b"\\A"
            elif a == A_BUF_LAST:
                tree = b"\\Z"
            elif a == A_WORD_FIRST:
                tree = b"(?<!" + W + b")(?=" + W + b")"
            elif a == A_WORD_LAST:
                tree = b"(?<=" + W + b")(?!" + W + b")"
            elif a == A_WORD_DELIM:
                tree = (b"(?:(?<!" + W + b")(?=" + W + b")|(?<=" + W + b")(?!" + W + b"))")
            else:
                tree = (b"(?:(?<=" + W + b")(?=" + W + b")|(?<!" + W + b")(?!" + W + b"))")
            tok = self.fetch(syntax)
            return tree, tok
        elif tt == T_WORD:
            tree = b"[" + WORDSET + b"]"
        elif tt == T_NOTWORD:
            tree = b"[^" + WORDSET + b"]"
        elif tt == T_SPACE:
            tree = b"[ \\t\\n\\v\\f\\r]"
        elif tt == T_NOTSPACE:
            tree = b"[^ \\t\\n\\v\\f\\r]"
        elif tt in (T_ALT, T_END):
            return None, tok
        elif tt == T_BACKSLASH_END:
            raise RegexError("Trailing backslash")
        else:
            raise RegexError("internal")

        tok = self.fetch(syntax)
        while tok.type in (T_STAR, T_PLUS, T_QUESTION, T_OPEN_DUP):
            dup_type = tok.type
            tree, tok = self.parse_dup(tree, tok, syntax)
            if (syntax & RE_CONTEXT_INVALID_DUP) and tok.type in (T_STAR, T_OPEN_DUP):
                raise RegexError("Invalid preceding regular expression")
            _ = dup_type
        return tree, tok

    def parse_sub_exp(self, syntax, nest):
        cur = self.nsub + 1
        self.nsub += 1
        tok = self.fetch(syntax | RE_CARET_ANCHORS_HERE)
        if tok.type == T_CLOSE_GROUP:
            inner = None
        else:
            inner, tok = self.parse_reg_exp(tok, syntax, nest)
            if tok.type != T_CLOSE_GROUP:
                raise RegexError("Unmatched ( or \\(")
        if cur <= 9:
            self.completed.add(cur)
        return b"(?P<g%d>" % cur + (inner or b"") + b")"

    def fetch_number(self, syntax):
        num = -1
        while True:
            tok = self.fetch(syntax)
            c = tok.c
            if tok.type == T_END:
                return -2, tok
            if tok.type == T_CLOSE_DUP or c == 44:
                break
            if tok.type != T_CHAR or c < 48 or c > 57 or num == -2:
                num = -2
            elif num == -1:
                num = c - 48
            else:
                num = min(0x7fff + 1, num * 10 + c - 48)
        return num, tok

    def parse_dup(self, elem, tok, syntax):
        start_idx = self.pos
        start_tok = tok
        if tok.type == T_OPEN_DUP:
            end = 0
            start, stok = self.fetch_number(syntax)
            if start == -1:
                if stok.type == T_CHAR and stok.c == 44:
                    start = 0
                else:
                    raise RegexError("Invalid content of \\{\\}")
            last = stok
            if start != -2:
                if stok.type == T_CLOSE_DUP:
                    end = start
                elif stok.type == T_CHAR and stok.c == 44:
                    end, last = self.fetch_number(syntax)
                else:
                    end = -2
            if start == -2 or end == -2:
                if not (syntax & RE_INVALID_INTERVAL_ORD):
                    if last.type == T_END:
                        raise RegexError("Unmatched \\{")
                    raise RegexError("Invalid content of \\{\\}")
                self.pos = start_idx
                t = Tok(T_CHAR, start_tok.c, 0)
                return elem, t
            if (end != -1 and start > end) or last.type != T_CLOSE_DUP:
                raise RegexError("Invalid content of \\{\\}")
            if (end if end != -1 else start) > 0x7fff:
                raise RegexError("Regular expression too big")
        else:
            start = 1 if tok.type == T_PLUS else 0
            end = 1 if tok.type == T_QUESTION else -1
        tok = self.fetch(syntax)
        if elem is None:
            return None, tok
        if end == -1:
            if start == 0:
                q = b"*"
            elif start == 1:
                q = b"+"
            else:
                q = b"{%d,}" % start
        else:
            if start == 0 and end == 1:
                q = b"?"
            elif start == end:
                q = b"{%d}" % start
            else:
                q = b"{%d,%d}" % (start, end)
        return b"(?:" + elem + b")" + q, tok

    # -- brackets ----------------------------------------------------------
    def peek_bracket(self, pos, syntax):
        buf = self.buf
        if pos >= self.n:
            return Tok(T_END, 0, 0)
        c = buf[pos]
        if c == 92 and (syntax & RE_BACKSLASH_ESCAPE_IN_LISTS) and pos + 1 < self.n:
            return Tok(T_CHAR, buf[pos + 1], 2)
        if c == 91:
            c2 = buf[pos + 1] if pos + 1 < self.n else 0
            if c2 == 46:
                return Tok("coll", c2, 2)
            if c2 == 61:
                return Tok("equiv", c2, 2)
            if c2 == 58 and (syntax & RE_CHAR_CLASSES):
                return Tok("class", c2, 2)
            return Tok(T_CHAR, c, 1)
        if c == 45:
            return Tok("range", c, 1)
        if c == 93:
            return Tok("close", c, 1)
        if c == 94:
            return Tok("not", c, 1)
        return Tok(T_CHAR, c, 1)

    def parse_bracket_symbol(self, tok):
        delim = {"coll": 46, "equiv": 61, "class": 58}[tok.type]
        if self.pos >= self.n:
            raise RegexError("Unmatched [")
        name = bytearray()
        i = 0
        while True:
            if i >= 32:
                raise RegexError("Unmatched [")
            if tok.type == "class":
                ch = self.orig[self.pos]
            else:
                ch = self.buf[self.pos]
            self.pos += 1
            if self.pos >= self.n:
                raise RegexError("Unmatched [")
            if ch == delim and self.buf[self.pos] == 93:
                break
            name.append(ch)
            i += 1
        self.pos += 1
        return (tok.type, bytes(name))

    def parse_bracket_element(self, tok, syntax, accept_hyphen):
        self.pos += tok.len
        if tok.type in ("coll", "equiv", "class"):
            return self.parse_bracket_symbol(tok)
        if tok.type == "range" and not accept_hyphen:
            t2 = self.peek_bracket(self.pos, syntax)
            if t2.type != "close":
                raise RegexError("Invalid range end")
        return ("char", tok.c)

    def parse_bracket(self, syntax):
        s = set()
        non_match = False
        tok = self.peek_bracket(self.pos, syntax)
        if tok.type == T_END:
            raise RegexError("Unmatched [")
        if tok.type == "not":
            non_match = True
            if syntax & RE_HAT_LISTS_NOT_NEWLINE:
                s.add(10)
            self.pos += tok.len
            tok = self.peek_bracket(self.pos, syntax)
            if tok.type == T_END:
                raise RegexError("Unmatched [")
        if tok.type == "close":
            tok.type = T_CHAR
        first_round = True
        while True:
            start_elem = self.parse_bracket_element(tok, syntax, first_round)
            first_round = False
            tok = self.peek_bracket(self.pos, syntax)
            is_range = False
            if start_elem[0] not in ("class", "equiv"):
                if tok.type == T_END:
                    raise RegexError("Unmatched [")
                if tok.type == "range":
                    self.pos += tok.len
                    tok2 = self.peek_bracket(self.pos, syntax)
                    if tok2.type == T_END:
                        raise RegexError("Unmatched [")
                    if tok2.type == "close":
                        self.pos -= tok.len
                        tok.type = T_CHAR
                    else:
                        is_range = True
            if is_range:
                end_elem = self.parse_bracket_element(tok2, syntax, True)
                tok = self.peek_bracket(self.pos, syntax)
                if start_elem[0] in ("class", "equiv") or end_elem[0] in ("class", "equiv"):
                    raise RegexError("Invalid range end")
                sc = self.elem_char(start_elem)
                ec = self.elem_char(end_elem)
                if (syntax & RE_NO_EMPTY_RANGES) and sc > ec:
                    raise RegexError("Invalid range end")
                for ch in range(sc, ec + 1):
                    s.add(ch)
            else:
                kind = start_elem[0]
                if kind == "char":
                    s.add(start_elem[1])
                elif kind in ("equiv", "coll"):
                    if len(start_elem[1]) != 1:
                        raise RegexError("Invalid collation character")
                    s.add(start_elem[1][0])
                elif kind == "class":
                    name = start_elem[1]
                    if self.icase and name in (b"upper", b"lower"):
                        name = b"alpha"
                    if name not in CLASS_NAMES:
                        raise RegexError("Invalid character class name")
                    for ch in range(256):
                        if _cclass(name, ch):
                            s.add(ch)
            if tok.type == T_END:
                raise RegexError("Unmatched [")
            if tok.type == "close":
                break
        self.pos += tok.len
        if non_match:
            s = set(range(256)) - s
        if self.icase:
            s = set(_upper(c) for c in s) | set(c for c in s if not (97 <= c <= 122))
        return self.set_re(s)

    def elem_char(self, elem):
        if elem[0] == "char":
            return elem[1]
        if len(elem[1]) != 1:
            raise RegexError("Invalid collation character")
        return elem[1][0]

    def set_re(self, s):
        if not s:
            return b"(?!)"
        chars = sorted(s)
        parts = []
        i = 0
        while i < len(chars):
            j = i
            while j + 1 < len(chars) and chars[j + 1] == chars[j] + 1:
                j += 1
            if j == i:
                parts.append(b"\\x%02x" % chars[i])
            else:
                parts.append(b"\\x%02x-\\x%02x" % (chars[i], chars[j]))
            i = j + 1
        return b"[" + b"".join(parts) + b"]"


def compile_regex(pattern, syntax, icase):
    comp = GnuRegexCompiler(pattern, syntax, icase)
    pyre = comp.compile()
    return re.compile(pyre, re.DOTALL)


# ---------------------------------------------------------------------------
# Mode handling (gnulib modechange)
# ---------------------------------------------------------------------------

S_ISUID = 0o4000
S_ISGID = 0o2000
S_ISVTX = 0o1000
S_IRWXU = 0o700
S_IRWXG = 0o070
S_IRWXO = 0o007
CHMOD_MODE_BITS = 0o7777


def mode_compile(s):
    if s[:1] and "0" <= s[0] < "8":
        v = 0
        i = 0
        while i < len(s) and "0" <= s[i] < "8":
            v = v * 8 + ord(s[i]) - 48
            if v > 0o7777:
                return None
            i += 1
        if i < len(s):
            return None
        return [("=", "ord", CHMOD_MODE_BITS, v, CHMOD_MODE_BITS)]
    changes = []
    p = 0
    n = len(s)

    def at(i):
        return s[i] if i < n else "\0"

    while True:
        affected = 0
        while True:
            ch = at(p)
            if ch == "u":
                affected |= S_ISUID | S_IRWXU
            elif ch == "g":
                affected |= S_ISGID | S_IRWXG
            elif ch == "o":
                affected |= S_ISVTX | S_IRWXO
            elif ch == "a":
                affected |= CHMOD_MODE_BITS
            elif ch in "=+-" and ch != "\0":
                break
            else:
                return None
            p += 1
        while True:
            op = at(p)
            p += 1
            ch = at(p)
            if ch == "u":
                value = S_IRWXU
                flag = "copy"
                p += 1
            elif ch == "g":
                value = S_IRWXG
                flag = "copy"
                p += 1
            elif ch == "o":
                value = S_IRWXO
                flag = "copy"
                p += 1
            else:
                value = 0
                flag = "ord"
                while True:
                    ch = at(p)
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
                    p += 1
            mentioned = (affected & value) if affected else value
            changes.append((op, flag, affected, value, mentioned))
            if at(p) not in ("=", "+", "-") or at(p) == "\0":
                break
        if at(p) != ",":
            break
        p += 1
    if p >= n:
        return changes
    return None


def mode_adjust(oldmode, is_dir, umask, changes):
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
        value &= (affected if affected else ~umask) & ~omit_change
        if op == "=":
            preserved = (~affected if affected else umask) | omit_change
            newmode = (newmode & preserved) | value
        elif op == "+":
            newmode |= value
        elif op == "-":
            newmode &= ~value
    return newmode & 0o7777


def mode_string(m):
    fmt = stat.S_IFMT(m)
    if fmt == stat.S_IFREG:
        t = "-"
    elif fmt == stat.S_IFDIR:
        t = "d"
    elif fmt == stat.S_IFLNK:
        t = "l"
    elif fmt == stat.S_IFCHR:
        t = "c"
    elif fmt == stat.S_IFBLK:
        t = "b"
    elif fmt == stat.S_IFIFO:
        t = "p"
    elif fmt == stat.S_IFSOCK:
        t = "s"
    else:
        t = "?"
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
    fmt = stat.S_IFMT(m)
    return {stat.S_IFREG: b"f", stat.S_IFDIR: b"d", stat.S_IFLNK: b"l",
            stat.S_IFCHR: b"c", stat.S_IFBLK: b"b", stat.S_IFIFO: b"p",
            stat.S_IFSOCK: b"s"}.get(fmt, b"U")


# ---------------------------------------------------------------------------
# Number parsing
# ---------------------------------------------------------------------------

C_SPACE = " \t\n\v\f\r"


def get_comp_type(s):
    if s[:1] == "+":
        return "GT", s[1:]
    if s[:1] == "-":
        return "LT", s[1:]
    return "EQ", s


def xstrtoumax(s):
    i = 0
    while i < len(s) and s[i] in C_SPACE:
        i += 1
    if i < len(s) and s[i] == "-":
        return None
    if i < len(s) and s[i] == "+":
        i += 1
    j = i
    while j < len(s) and "0" <= s[j] <= "9":
        j += 1
    if j == i or j != len(s):
        return None
    v = int(s[i:j])
    if v >= 1 << 64:
        return None
    return v


_FLOAT_RE = re.compile(r"[ \t\n\v\f\r]*[+-]?(?:(?:[0-9]+\.?[0-9]*|\.[0-9]+)(?:[eE][+-]?[0-9]+)?|inf|infinity|nan)\Z",
                       re.IGNORECASE)


def xstrtod(s):
    if not _FLOAT_RE.match(s):
        return None
    try:
        v = float(s.strip(C_SPACE))
    except ValueError:
        return None
    if math.isinf(v) and "inf" not in s.lower():
        return None
    return v


# ---------------------------------------------------------------------------
# printf
# ---------------------------------------------------------------------------

def parse_cspec(spec):
    """spec is the bytes between '%' and the conversion char."""
    flags = set()
    i = 0
    while i < len(spec) and chr(spec[i]) in "-+ #0":
        flags.add(chr(spec[i]))
        i += 1
    j = i
    while j < len(spec) and 48 <= spec[j] <= 57:
        j += 1
    width = int(spec[i:j]) if j > i else 0
    prec = None
    if j < len(spec) and spec[j] == 46:
        k = j + 1
        m = k
        while m < len(spec) and 48 <= spec[m] <= 57:
            m += 1
        prec = int(spec[k:m]) if m > k else 0
    return flags, width, prec


def c_fmt_str(spec, s):
    flags, width, prec = parse_cspec(spec)
    if prec is not None:
        s = s[:prec]
    if len(s) < width:
        pad = b" " * (width - len(s))
        s = s + pad if "-" in flags else pad + s
    return s


def c_fmt_int(spec, value, conv):
    flags, width, prec = parse_cspec(spec)
    sign = b""
    if conv == "d":
        if value < 0:
            sign = b"-"
            value = -value
        elif "+" in flags:
            sign = b"+"
        elif " " in flags:
            sign = b" "
        digits = str(value).encode()
    else:
        digits = ("%o" % value).encode()
    if prec is not None:
        if prec == 0 and value == 0:
            digits = b""
        if len(digits) < prec:
            digits = b"0" * (prec - len(digits)) + digits
    if conv == "o" and "#" in flags and not digits.startswith(b"0"):
        digits = b"0" + digits
    body_len = len(sign) + len(digits)
    if body_len < width:
        if "-" in flags:
            return sign + digits + b" " * (width - body_len)
        if "0" in flags and prec is None:
            return sign + b"0" * (width - body_len) + digits
        return b" " * (width - body_len) + sign + digits
    return sign + digits


PRINTF_DIRECTIVES = b"abcdDfFgGhHiklmMnpPsSuUyYZ"
PRINTF_TIME_DIRECTIVES = b"ABCT"


def parse_printf_format(fmt):
    segs = []   # ('lit', bytes) | ('dir', spec, conv, aux) | ('stop',)
    lit = bytearray()
    i = 0
    n = len(fmt)
    while i < n:
        c = fmt[i]
        if c == 92:  # backslash
            if i + 1 >= n:
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
                lit.append(v & 0xff)
                i = j
                continue
            esc = {97: 7, 98: 8, 102: 12, 110: 10, 114: 13, 116: 9, 118: 11, 92: 92}
            if c2 in esc:
                lit.append(esc[c2])
                i += 2
                continue
            if c2 == 99:  # \c
                if lit:
                    segs.append(("lit", bytes(lit)))
                segs.append(("stop",))
                return segs
            warn("warning: unrecognized escape `\\%s'" % chr(c2))
            lit.append(92)
            lit.append(c2)
            i += 2
            continue
        if c == 37:  # '%'
            if i + 1 >= n:
                raise FatalError("error: %s at end of format string" % "%")
            if fmt[i + 1] == 37:
                lit.append(37)
                i += 2
                continue
            j = i + 1
            while j < n and fmt[j] in b"-+ #":
                j += 1
            while j < n and 48 <= fmt[j] <= 57:
                j += 1
            if j < n and fmt[j] == 46:
                j += 1
                while j < n and 48 <= fmt[j] <= 57:
                    j += 1
            if j < n and fmt[j] in PRINTF_DIRECTIVES:
                if lit:
                    segs.append(("lit", bytes(lit)))
                    lit = bytearray()
                segs.append(("dir", fmt[i + 1:j], chr(fmt[j]), None))
                i = j + 1
                continue
            if j < n and fmt[j] in PRINTF_TIME_DIRECTIVES and j + 1 < n:
                if lit:
                    segs.append(("lit", bytes(lit)))
                    lit = bytearray()
                segs.append(("dir", fmt[i + 1:j], chr(fmt[j]), chr(fmt[j + 1])))
                i = j + 2
                continue
            # unrecognized: drop the '%', continue with following char
            if j < n:
                warn("warning: unrecognized format directive `%%%s'" % chr(fmt[j]))
            i += 1
            continue
        lit.append(c)
        i += 1
    if lit:
        segs.append(("lit", bytes(lit)))
    return segs


WEEKDAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep",
          "Oct", "Nov", "Dec"]


def ctime_format(ns):
    sec, nsec = divmod(ns, 10 ** 9)
    tm = time.localtime(sec)
    wday = (tm.tm_wday + 1) % 7
    return ("%3s %3s %2d %02d:%02d:%02d.%010d %04d" % (
        WEEKDAYS[wday], MONTHS[tm.tm_mon - 1], tm.tm_mday, tm.tm_hour,
        tm.tm_min, tm.tm_sec, nsec, tm.tm_year)).encode()


def time_format(ns, k):
    sec, nsec = divmod(ns, 10 ** 9)
    if k == "@":
        return ("%d.%09d0" % (sec, nsec)).encode()
    tm = time.localtime(sec)
    frac = ".%09d0" % nsec
    if k == "+":
        return (time.strftime("%Y-%m-%d+%H:%M:%S", tm) + frac).encode()
    if k in "ST":
        return (time.strftime("%" + k, tm) + frac).encode()
    if k == "X":
        return (time.strftime("%H:%M:%S", tm) + frac).encode()
    try:
        return time.strftime("%" + k, tm).encode()
    except ValueError:
        return b""


def user_name(uid):
    try:
        import pwd
        return pwd.getpwuid(uid).pw_name.encode()
    except Exception:
        return str(uid).encode()


def group_name(gid):
    try:
        import grp
        return grp.getgrgid(gid).gr_name.encode()
    except Exception:
        return str(gid).encode()


def do_printf(segs, ent):
    out = []
    for seg in segs:
        kind = seg[0]
        if kind == "lit":
            out.append(seg[1])
            continue
        if kind == "stop":
            break
        spec, conv, aux = seg[1], seg[2], seg[3]
        st = ent.st
        path = ent.path
        if conv == "d":
            out.append(c_fmt_int(spec, ent.depth, "d"))
            continue
        if conv == "m":
            out.append(c_fmt_int(spec, st.st_mode & 0o7777, "o"))
            continue
        if conv == "p":
            s = path
        elif conv == "P":
            if ent.depth > 0:
                cp = path[ent.start_len:]
                if cp[:1] == b"/":
                    cp = cp[1:]
                s = cp
            else:
                s = b""
        elif conv == "f":
            s = base_name(path)
        elif conv == "h":
            k = path.rfind(b"/")
            s = b"." if k < 0 else path[:k]
        elif conv == "H":
            s = ent.start
        elif conv == "s":
            s = str(st.st_size).encode()
        elif conv == "y":
            s = type_char(st.st_mode)
        elif conv == "Y":
            if stat.S_ISLNK(st.st_mode):
                try:
                    s = type_char(os.stat(path).st_mode)
                except OSError as e:
                    import errno
                    if e.errno == errno.ELOOP:
                        s = b"L"
                    elif e.errno == errno.ENOENT:
                        s = b"N"
                    else:
                        s = b"?"
            else:
                s = type_char(st.st_mode)
        elif conv == "M":
            s = mode_string(st.st_mode)
        elif conv == "l":
            s = b""
            if stat.S_ISLNK(st.st_mode):
                try:
                    s = os.readlink(path)
                except OSError:
                    OPTS.exit_status = 1
        elif conv == "n":
            s = str(st.st_nlink).encode()
        elif conv == "i":
            s = str(st.st_ino).encode()
        elif conv == "U":
            s = str(st.st_uid).encode()
        elif conv == "G":
            s = str(st.st_gid).encode()
        elif conv == "u":
            s = user_name(st.st_uid)
        elif conv == "g":
            s = group_name(st.st_gid)
        elif conv == "D":
            s = str(st.st_dev).encode()
        elif conv == "b":
            s = str(getattr(st, "st_blocks", 0)).encode()
        elif conv == "k":
            s = str((getattr(st, "st_blocks", 0) + 1) // 2).encode()
        elif conv == "S":
            blocks = getattr(st, "st_blocks", 0)
            if st.st_size:
                s = ("%g" % (blocks * 512.0 / st.st_size)).encode()
            else:
                s = b"1"
        elif conv == "a":
            s = ctime_format(st.st_atime_ns)
        elif conv == "c":
            s = ctime_format(st.st_ctime_ns)
        elif conv == "t":
            s = ctime_format(st.st_mtime_ns)
        elif conv == "A":
            s = time_format(st.st_atime_ns, aux)
        elif conv == "C":
            s = time_format(st.st_ctime_ns, aux)
        elif conv == "T":
            s = time_format(st.st_mtime_ns, aux)
        elif conv == "B":
            s = b""
        elif conv == "F":
            s = b"unknown"
        elif conv == "Z":
            s = b""
        else:
            s = b""
        out.append(c_fmt_str(spec, s))
    return b"".join(out)


# ---------------------------------------------------------------------------
# Entries
# ---------------------------------------------------------------------------

class Entry:
    __slots__ = ("path", "depth", "st", "start", "start_len", "pruned")

    def __init__(self, path, depth, st, start, start_len):
        self.path = path
        self.depth = depth
        self.st = st
        self.start = start
        self.start_len = start_len
        self.pruned = False


# ---------------------------------------------------------------------------
# Expression parsing
# ---------------------------------------------------------------------------

def mk_and(a, b):
    return lambda e: a(e) and b(e)


def mk_or(a, b):
    return lambda e: a(e) or b(e)


def mk_not(a):
    return lambda e: not a(e)


def mk_comma(a, b):
    def f(e):
        a(e)
        return b(e)
    return f


def pred_true(e):
    return True


def pred_false(e):
    return False


class Parser:
    def __init__(self, args):
        self.args = args
        self.pos = 0
        self.has_action = False

    def peek(self):
        if self.pos < len(self.args):
            return self.args[self.pos]
        return None

    def next(self):
        t = self.args[self.pos]
        self.pos += 1
        return t

    def parse(self):
        if self.peek() is None:
            return None
        e = self.parse_comma()
        if self.peek() is not None:
            t = self.peek()
            if t == ")":
                raise FatalError("invalid expression; you have too many ')'")
            raise FatalError("invalid expression")
        return e

    def parse_comma(self):
        left = self.parse_or()
        while self.peek() == ",":
            self.next()
            if self.peek() is None:
                raise FatalError("invalid expression; expected an expression after ','")
            right = self.parse_or()
            left = mk_comma(left, right)
        return left

    def parse_or(self):
        left = self.parse_and()
        while self.peek() in ("-o", "-or"):
            op = self.next()
            if self.peek() is None:
                raise FatalError("invalid expression; expected an expression after '%s'" % op)
            right = self.parse_and()
            left = mk_or(left, right)
        return left

    def parse_and(self):
        left = self.parse_unary()
        while True:
            t = self.peek()
            if t in ("-a", "-and"):
                self.next()
                if self.peek() is None:
                    raise FatalError("invalid expression; expected an expression after '%s'" % t)
                right = self.parse_unary()
            elif t is None or t in (")", ",", "-o", "-or"):
                break
            else:
                right = self.parse_unary()
            left = mk_and(left, right)
        return left

    def parse_unary(self):
        t = self.peek()
        if t is None:
            raise FatalError("invalid expression")
        if t in ("!", "-not"):
            self.next()
            if self.peek() is None:
                raise FatalError("invalid expression; expected an expression after '%s'" % t)
            return mk_not(self.parse_unary())
        if t == "(":
            self.next()
            if self.peek() == ")":
                raise FatalError("invalid expression; empty parentheses are not allowed.")
            if self.peek() is None:
                raise FatalError("invalid expression; I was expecting to find a ')' somewhere but did not see one.")
            e = self.parse_comma()
            if self.peek() != ")":
                raise FatalError("invalid expression; I was expecting to find a ')' somewhere but did not see one.")
            self.next()
            return e
        if t in (")", ",", "-o", "-or", "-a", "-and"):
            raise FatalError("invalid expression; you have used a binary operator '%s' with nothing before it." % t)
        self.next()
        return self.primary(t)

    def arg(self, name):
        if self.pos >= len(self.args):
            raise FatalError("missing argument to `%s'" % name)
        return self.next()

    # -- primaries --------------------------------------------------------
    def primary(self, t):
        if not t.startswith("-") or t == "-":
            raise FatalError("paths must precede expression: `%s'" % t)
        name = t[1:]
        h = getattr(self, "p_" + name.replace("-", "_"), None)
        if h is None or name in ("", ):
            raise FatalError("unknown predicate `%s'" % t)
        return h(t)

    # options
    def p_depth(self, t):
        OPTS.depth_first = True
        return pred_true

    p_d = p_depth

    def _depth_arg(self, t):
        a = self.arg(t)
        if a and all("0" <= ch <= "9" for ch in a):
            return int(a)
        raise FatalError("Expected a positive decimal integer argument to %s, but got %s" % (t, qs(a)))

    def p_maxdepth(self, t):
        OPTS.maxdepth = self._depth_arg(t)
        return pred_true

    def p_mindepth(self, t):
        OPTS.mindepth = self._depth_arg(t)
        return pred_true

    def p_regextype(self, t):
        a = self.arg(t)
        if a not in REGEX_TYPES:
            raise FatalError("Unknown regular expression type %s" % qs(a))
        OPTS.regex_syntax = REGEX_TYPES[a]
        return pred_true

    def _noop(self, t):
        return pred_true

    p_noleaf = _noop
    p_xdev = _noop
    p_mount = _noop
    p_warn = _noop
    p_nowarn = _noop
    p_ignore_readdir_race = _noop
    p_noignore_readdir_race = _noop

    def p_daystart(self, t):
        if not OPTS.full_days:
            sec = (OPTS.cur_day_start_ns // 10 ** 9) + 86400
            nsec = OPTS.cur_day_start_ns % 10 ** 9
            tm = time.localtime(sec)
            sec -= tm.tm_sec + tm.tm_min * 60 + tm.tm_hour * 3600
            OPTS.cur_day_start_ns = sec * 10 ** 9 + nsec
            OPTS.full_days = True
        return pred_true

    # tests
    def p_true(self, t):
        return pred_true

    def p_false(self, t):
        return pred_false

    def _name(self, t, fold):
        pat = os.fsencode(self.arg(t))

        def f(e):
            return fnmatch(pat, match_name(e.path), fold)
        return f

    def p_name(self, t):
        return self._name(t, False)

    def p_iname(self, t):
        return self._name(t, True)

    def _path(self, t, fold):
        pat = os.fsencode(self.arg(t))
        return lambda e: fnmatch(pat, e.path, fold)

    def p_path(self, t):
        return self._path(t, False)

    def p_ipath(self, t):
        return self._path(t, True)

    p_wholename = p_path
    p_iwholename = p_ipath

    def _lname(self, t, fold):
        pat = os.fsencode(self.arg(t))

        def f(e):
            if not stat.S_ISLNK(e.st.st_mode):
                return False
            try:
                target = os.readlink(e.path)
            except OSError:
                return False
            return fnmatch(pat, target, fold)
        return f

    def p_lname(self, t):
        return self._lname(t, False)

    def p_ilname(self, t):
        return self._lname(t, True)

    def _regex(self, t, icase):
        pat = os.fsencode(self.arg(t))
        try:
            rx = compile_regex(pat, OPTS.regex_syntax, icase)
        except RegexError as ex:
            raise FatalError(str(ex))
        except re.error as ex:
            raise FatalError("Invalid regular expression: %s" % ex)
        if icase:
            return lambda e: rx.fullmatch(e.path.upper()) is not None
        return lambda e: rx.fullmatch(e.path) is not None

    def p_regex(self, t):
        return self._regex(t, False)

    def p_iregex(self, t):
        return self._regex(t, True)

    def p_type(self, t):
        a = self.arg(t)
        if not a:
            raise FatalError("Arguments to -type should contain at least one letter")
        types = set()
        i = 0
        tmap = {"f": stat.S_IFREG, "d": stat.S_IFDIR, "l": stat.S_IFLNK,
                "b": stat.S_IFBLK, "c": stat.S_IFCHR, "p": stat.S_IFIFO,
                "s": stat.S_IFSOCK, "D": -1}
        while i < len(a):
            ch = a[i]
            if ch not in tmap:
                raise FatalError("Unknown argument to -type: %s" % ch)
            if tmap[ch] in types:
                raise FatalError("Duplicate file type '%s' in the argument list to -type" % ch)
            types.add(tmap[ch])
            i += 1
            if i < len(a):
                if a[i] != ",":
                    raise FatalError("Must separate multiple arguments to -type using: ','")
                i += 1
                if i >= len(a):
                    raise FatalError("Last file type in list argument to -type is missing, i.e., list is ending on: ','")
        return lambda e: stat.S_IFMT(e.st.st_mode) in types

    def p_size(self, t):
        a = self.arg(t)
        if not a:
            raise FatalError("invalid null argument to -size")
        suf = a[-1]
        units = {"b": 512, "c": 1, "w": 2, "k": 1024, "M": 1024 ** 2,
                 "G": 1024 ** 3}
        if suf in units:
            bs = units[suf]
            num = a[:-1]
        elif "0" <= suf <= "9":
            bs = 512
            num = a
        else:
            raise FatalError("invalid -size type `%s'" % suf)
        kind, rest = get_comp_type(num)
        v = xstrtoumax(rest)
        if v is None:
            raise FatalError("invalid argument `%s' to `-size'" % a)

        def f(e):
            sz = e.st.st_size
            fv = sz // bs + (1 if sz % bs else 0)
            if kind == "GT":
                return fv > v
            if kind == "LT":
                return fv < v
            return fv == v
        return f

    def _num(self, t):
        a = self.arg(t)
        kind, rest = get_comp_type(a)
        v = xstrtoumax(rest)
        if v is None:
            raise FatalError("invalid argument `%s' to `%s'" % (a, t))
        return kind, v

    def _numpred(self, t, getter):
        kind, v = self._num(t)

        def f(e):
            x = getter(e.st)
            if kind == "GT":
                return x > v
            if kind == "LT":
                return x < v
            return x == v
        return f

    def p_links(self, t):
        return self._numpred(t, lambda st: st.st_nlink)

    def p_inum(self, t):
        return self._numpred(t, lambda st: st.st_ino)

    def p_uid(self, t):
        return self._numpred(t, lambda st: st.st_uid)

    def p_gid(self, t):
        return self._numpred(t, lambda st: st.st_gid)

    def p_user(self, t):
        a = self.arg(t)
        try:
            import pwd
            uid = pwd.getpwnam(a).pw_uid
        except Exception:
            if a and a.isdigit():
                uid = int(a)
            else:
                raise FatalError("%s is not the name of a known user" % qs(a))
        return lambda e: e.st.st_uid == uid

    def p_group(self, t):
        a = self.arg(t)
        try:
            import grp
            gid = grp.getgrnam(a).gr_gid
        except Exception:
            if a and a.isdigit():
                gid = int(a)
            else:
                raise FatalError("%s is not the name of an existing group" % qs(a))
        return lambda e: e.st.st_gid == gid

    def p_nouser(self, t):
        def f(e):
            try:
                import pwd
                pwd.getpwuid(e.st.st_uid)
                return False
            except KeyError:
                return True
        return f

    def p_nogroup(self, t):
        def f(e):
            try:
                import grp
                grp.getgrgid(e.st.st_gid)
                return False
            except KeyError:
                return True
        return f

    def p_empty(self, t):
        def f(e):
            m = e.st.st_mode
            if stat.S_ISDIR(m):
                try:
                    with os.scandir(e.path) as it:
                        for _ in it:
                            return False
                except OSError as ex:
                    warn("%s: %s" % (qs(e.path), ex.strerror))
                    OPTS.exit_status = 1
                    return False
                return True
            if stat.S_ISREG(m):
                return e.st.st_size == 0
            return False
        return f

    def p_perm(self, t):
        a = self.arg(t)
        c0 = a[:1]
        if c0 == "-":
            start, kind = 1, "ALL"
        elif c0 == "/":
            start, kind = 1, "ANY"
        elif c0 == "+":
            if mode_compile(a) is None:
                start, kind = 1, "ANY"
            else:
                start, kind = 0, "EQ"
        else:
            start, kind = 0, "EQ"
        change = mode_compile(a[start:])
        if change is None or (c0 == "+" and a[1:2] and "0" <= a[1] < "8"):
            raise FatalError("invalid mode %s" % qs(a))
        v0 = mode_adjust(0, False, 0, change)
        v1 = mode_adjust(0, True, 0, change)
        if c0 == "/" and v0 == 0 and v1 == 0:
            kind = "ALL"

        def f(e):
            m = e.st.st_mode
            pv = v1 if stat.S_ISDIR(m) else v0
            if kind == "ALL":
                return (m & pv) == pv
            if kind == "ANY":
                return (m & pv) != 0
            return (m & 0o7777) == pv
        return f

    def _time(self, t, attr, is_min):
        a = self.arg(t)
        kind, rest = get_comp_type(a)
        if is_min:
            origin = OPTS.cur_day_start_ns + 86400 * 10 ** 9
            unit = 60
        else:
            origin = OPTS.cur_day_start_ns
            if kind == "LT":
                origin += (86400 - 1) * 10 ** 9
            unit = 86400
        # xstrtod on the part after the comparison char
        v = xstrtod(rest)
        if v is None:
            raise FatalError("invalid argument `%s' to `%s'" % (a, t))
        # invert
        if kind == "LT":
            kind = "GT"
        elif kind == "GT":
            kind = "LT"
        frac, secs = math.modf(v * unit)
        ref = origin - int(secs) * 10 ** 9 - int(frac * 1e9)
        window = unit * 10 ** 9

        def f(e):
            delta = getattr(e.st, attr) - ref
            if kind == "GT":
                return delta > 0
            if kind == "LT":
                return delta < 0
            return 0 <= delta < window
        return f

    def p_mtime(self, t):
        return self._time(t, "st_mtime_ns", False)

    def p_atime(self, t):
        return self._time(t, "st_atime_ns", False)

    def p_ctime(self, t):
        return self._time(t, "st_ctime_ns", False)

    def p_mmin(self, t):
        return self._time(t, "st_mtime_ns", True)

    def p_amin(self, t):
        return self._time(t, "st_atime_ns", True)

    def p_cmin(self, t):
        return self._time(t, "st_ctime_ns", True)

    def _newer(self, t, attr):
        a = self.arg(t)
        try:
            st = os.lstat(os.fsencode(a))
        except OSError as ex:
            raise FatalError("%s: %s" % (qs(a), ex.strerror))
        ref = st.st_mtime_ns
        return lambda e: getattr(e.st, attr) > ref

    def p_newer(self, t):
        return self._newer(t, "st_mtime_ns")

    def p_anewer(self, t):
        return self._newer(t, "st_atime_ns")

    def p_cnewer(self, t):
        return self._newer(t, "st_ctime_ns")

    def p_samefile(self, t):
        a = self.arg(t)
        try:
            st = os.lstat(os.fsencode(a))
        except OSError as ex:
            raise FatalError("%s: %s" % (qs(a), ex.strerror))
        return lambda e: e.st.st_ino == st.st_ino and e.st.st_dev == st.st_dev

    def p_readable(self, t):
        return lambda e: os.access(e.path, os.R_OK, follow_symlinks=False) if os.access in os.supports_follow_symlinks else os.access(e.path, os.R_OK)

    def p_writable(self, t):
        return lambda e: os.access(e.path, os.W_OK)

    def p_executable(self, t):
        return lambda e: os.access(e.path, os.X_OK)

    # actions
    def p_print(self, t):
        self.has_action = True

        def f(e):
            OUT.write(e.path + b"\n")
            return True
        return f

    def p_print0(self, t):
        self.has_action = True

        def f(e):
            OUT.write(e.path + b"\0")
            return True
        return f

    def p_printf(self, t):
        self.has_action = True
        fmt = os.fsencode(self.arg(t))
        segs = parse_printf_format(fmt)

        def f(e):
            OUT.write(do_printf(segs, e))
            return True
        return f

    def p_prune(self, t):
        def f(e):
            if not OPTS.depth_first:
                e.pruned = True
            return True
        return f

    def p_quit(self, t):
        def f(e):
            raise QuitNow()
        return f


# ---------------------------------------------------------------------------
# Traversal
# ---------------------------------------------------------------------------

def visit(path, depth, st, start, start_len, expr):
    is_dir = stat.S_ISDIR(st.st_mode)
    ent = Entry(path, depth, st, start, start_len)
    maxd = OPTS.maxdepth
    descend = is_dir and (maxd is None or depth < maxd)
    if not OPTS.depth_first:
        if depth >= OPTS.mindepth:
            expr(ent)
        if descend and not ent.pruned:
            walk_children(ent, expr)
    else:
        if descend:
            walk_children(ent, expr)
        if depth >= OPTS.mindepth:
            expr(ent)


def walk_children(ent, expr):
    path = ent.path
    try:
        with os.scandir(path) as it:
            entries = [(d.name, d) for d in it]
    except OSError as ex:
        warn("%s: %s" % (qs(path), ex.strerror))
        OPTS.exit_status = 1
        return
    prefix = path if path.endswith(b"/") else path + b"/"
    for name, d in entries:
        cpath = prefix + name
        try:
            st = d.stat(follow_symlinks=False)
        except OSError as ex:
            warn("%s: %s" % (qs(cpath), ex.strerror))
            OPTS.exit_status = 1
            continue
        visit(cpath, ent.depth + 1, st, ent.start, ent.start_len, expr)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def looks_like_expression(arg, leading):
    if arg[:1] == "-":
        return len(arg) > 1
    if arg in (")", ","):
        return not leading
    if arg in ("(", "!"):
        return True
    return False


def main(argv):
    global OPTS, OUT
    OPTS = Options()
    OPTS.regex_syntax = REGEX_TYPES["findutils-default"]
    OUT = Output()
    sys.setrecursionlimit(100000)

    i = 0
    while i < len(argv):
        a = argv[i]
        if a in ("-H", "-L", "-P"):
            i += 1
        elif a == "--":
            i += 1
            break
        elif a == "-D":
            if i + 1 >= len(argv):
                warn("Missing argument after the -D option.")
                return 1
            i += 2
        elif a.startswith("-D") or a.startswith("-O"):
            i += 1
        else:
            break
    starts = []
    while i < len(argv) and not looks_like_expression(argv[i], True):
        starts.append(argv[i])
        i += 1
    expr_args = argv[i:]

    parser = Parser(expr_args)
    try:
        expr = parser.parse()
    except FatalError as ex:
        warn(str(ex))
        return 1
    if expr is None:
        expr = parser.p_print("-print")
    elif not parser.has_action:
        pr = parser.p_print("-print")
        expr = mk_and(expr, pr)

    if not starts:
        starts = ["."]

    try:
        for s in starts:
            path = os.fsencode(s)
            try:
                st = os.lstat(path) if path else os.lstat(b"")
            except (OSError, ValueError) as ex:
                warn("%s: %s" % (qs(s), getattr(ex, "strerror", None) or "No such file or directory"))
                OPTS.exit_status = 1
                continue
            visit(path, 0, st, path, len(path), expr)
    except QuitNow:
        pass
    except FatalError as ex:
        OUT.flush()
        warn(str(ex))
        return 1
    OUT.flush()
    return OPTS.exit_status


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
