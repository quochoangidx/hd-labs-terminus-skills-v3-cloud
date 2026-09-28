"""pym4: a GNU m4 1.4.19 replacement in pure Python.

Usage: python3 /app/pym4/m4.py [FILE]...
"""

import sys
import os
import re
import threading

# ---------------------------------------------------------------------------
# Constants

PROGRAM_NAME = "m4"

T_EOF, T_STRING, T_WORD, T_OPEN, T_COMMA, T_CLOSE, T_SIMPLE, T_MACDEF = range(8)

K_STR, K_FILE, K_MACRO = range(3)

C_SPACE = " \t\n\v\f\r"
WORD_START = frozenset("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_")
WORD_CHARS = frozenset("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_0123456789")
WORD_RE = re.compile(r"[A-Za-z0-9_]*")


class _MacroMark(object):
    __slots__ = ()


MACRO_MARK = _MacroMark()
EOF = None


class Fatal(Exception):
    pass


class M4Exit(Exception):
    def __init__(self, code):
        Exception.__init__(self)
        self.code = code


def to_i32(v):
    v &= 0xFFFFFFFF
    if v >= 0x80000000:
        v -= 0x100000000
    return v


def to_i64(v):
    v &= 0xFFFFFFFFFFFFFFFF
    if v >= 0x8000000000000000:
        v -= 0x10000000000000000
    return v


LONG_MAX = (1 << 63) - 1
LONG_MIN = -(1 << 63)


def c_strtol(s):
    """Emulate strtol(s, &end, 10).  Returns (value, endindex, overflow)."""
    n = len(s)
    i = 0
    while i < n and s[i] in C_SPACE:
        i += 1
    neg = False
    if i < n and s[i] in "+-":
        neg = s[i] == "-"
        i += 1
    j = i
    while j < n and "0" <= s[j] <= "9":
        j += 1
    if j == i:
        return 0, 0, False
    v = int(s[i:j])
    if neg:
        v = -v
    ovf = False
    if v > LONG_MAX:
        v = LONG_MAX
        ovf = True
    elif v < LONG_MIN:
        v = LONG_MIN
        ovf = True
    return v, j, ovf


_STRTOD_RE = re.compile(
    r"[ \t\n\v\f\r]*([+-]?)(?:"
    r"0[xX]((?:[0-9a-fA-F]+\.?[0-9a-fA-F]*|\.[0-9a-fA-F]+))([pP][+-]?[0-9]+)?"
    r"|((?:[0-9]+\.?[0-9]*|\.[0-9]+))([eE][+-]?[0-9]+)?"
    r"|([iI][nN][fF](?:[iI][nN][iI][tT][yY])?)"
    r"|([nN][aA][nN](?:\([0-9A-Za-z_]*\))?)"
    r")")


def c_strtod(s):
    """Emulate strtod.  Returns (value, endindex)."""
    m = _STRTOD_RE.match(s)
    if not m:
        return 0.0, 0
    sign = -1.0 if m.group(1) == "-" else 1.0
    if m.group(2) is not None:
        mant = m.group(2)
        exp = m.group(3) or "p0"
        if "." in mant:
            ip, fp = mant.split(".", 1)
        else:
            ip, fp = mant, ""
        ival = int((ip + fp) or "0", 16)
        e = int(exp[1:]) - 4 * len(fp)
        try:
            if e >= 0:
                v = float(ival << e) if e < 5000 else (float("inf") if ival else 0.0)
            else:
                from fractions import Fraction
                if -e > 5000 and ival:
                    v = float(Fraction(ival, 1 << min(-e, 20000)))
                else:
                    v = float(Fraction(ival, 1 << -e))
        except OverflowError:
            v = float("inf")
        return sign * v, m.end()
    if m.group(4) is not None:
        txt = m.group(4) + (m.group(5) or "")
        try:
            v = float(txt)
        except (ValueError, OverflowError):
            v = float("inf")
        return sign * v, m.end()
    if m.group(6) is not None:
        return sign * float("inf"), m.end()
    if m.group(7) is not None:
        return float("nan") * (1.0 if sign > 0 else -1.0), m.end()
    return 0.0, 0


# ---------------------------------------------------------------------------
# Regular expressions (GNU regex, RE_SYNTAX_EMACS == 0, POSIX longest match)

class RegexError(Exception):
    pass


class _Stop(Exception):
    pass


class Regex(object):
    """Parser/compiler for GNU Emacs-style regular expressions."""

    def __init__(self, pat):
        self.p = pat
        self.n = len(pat)
        self.i = 0
        self.ngroups = 0
        self.completed = set()
        self.tok = None
        self.fetch(True)
        ast = self.parse_reg_exp(0)
        if self.tok[0] != "END":
            # Unmatched close paren at top level
            raise RegexError("Unmatched ) or \\)")
        self.ast = ast

    # -- tokenizer -------------------------------------------------------
    def fetch(self, caret_here=False):
        self.tok = self.peek_token(self.i, caret_here)
        self.i = self.tok_end

    def peek_token(self, i, caret_here):
        p = self.p
        n = self.n
        if i >= n:
            self.tok_end = i
            return ("END",)
        c = p[i]
        if c == "\\":
            if i + 1 >= n:
                raise RegexError("Trailing backslash")
            c2 = p[i + 1]
            self.tok_end = i + 2
            if c2 == "|":
                return ("ALT",)
            if "1" <= c2 <= "9":
                return ("BACKREF", ord(c2) - 48)
            if c2 == "<":
                return ("ANCHOR", "wbeg")
            if c2 == ">":
                return ("ANCHOR", "wend")
            if c2 == "b":
                return ("ANCHOR", "wbound")
            if c2 == "B":
                return ("ANCHOR", "nwbound")
            if c2 == "w":
                return ("WORD",)
            if c2 == "W":
                return ("NOTWORD",)
            if c2 == "s":
                return ("SPACE",)
            if c2 == "S":
                return ("NOTSPACE",)
            if c2 == "`":
                return ("ANCHOR", "bufstart")
            if c2 == "'":
                return ("ANCHOR", "bufend")
            if c2 == "(":
                return ("OPEN",)
            if c2 == ")":
                return ("CLOSE",)
            return ("CHAR", c2)
        self.tok_end = i + 1
        if c == "*":
            return ("STAR",)
        if c == "+":
            return ("PLUS",)
        if c == "?":
            return ("QUES",)
        if c == ".":
            return ("ANY",)
        if c == "^":
            if i == 0 or caret_here:
                return ("ANCHOR", "bol")
            return ("CHAR", c)
        if c == "$":
            if i + 1 != n:
                nxt = p[i + 1:i + 3]
                if nxt not in ("\\|", "\\)"):
                    return ("CHAR", c)
            return ("ANCHOR", "eol")
        if c == "[":
            return self.parse_bracket(i + 1)
        return ("CHAR", c)

    def parse_bracket(self, i):
        p = self.p
        n = self.n
        neg = False
        if i < n and p[i] == "^":
            neg = True
            i += 1
        chars = set()
        first = True

        def elem(i):
            if i >= n:
                raise RegexError("Unmatched [")
            c = p[i]
            if c == "[" and i + 1 < n and p[i + 1] in ".=":
                delim = p[i + 1]
                j = p.find(delim + "]", i + 2)
                if j < 0:
                    raise RegexError("Unmatched [")
                name = p[i + 2:j]
                if len(name) != 1:
                    raise RegexError("Invalid collation character")
                return name, j + 2
            return c, i + 1

        while True:
            if i >= n:
                raise RegexError("Unmatched [")
            c = p[i]
            if c == "]" and not first:
                i += 1
                break
            first = False
            start, i = elem(i)
            if i < n and p[i] == "-" and i + 1 < n and p[i + 1] != "]":
                end, i = elem(i + 1)
                a, b = ord(start), ord(end)
                for x in range(a, b + 1):
                    chars.add(chr(x))
            else:
                chars.add(start)
        self.tok_end = i
        return ("SET", frozenset(chars), neg)

    # -- parser ----------------------------------------------------------
    def parse_reg_exp(self, nest):
        branches = [self.parse_branch(nest)]
        while self.tok[0] == "ALT":
            self.fetch(True)
            branches.append(self.parse_branch(nest))
        if len(branches) == 1:
            return branches[0]
        return ("alt", branches)

    def parse_branch(self, nest):
        items = []
        while True:
            t = self.tok[0]
            if t == "ALT" or t == "END" or (nest > 0 and t == "CLOSE"):
                break
            items.append(self.parse_expression(nest))
        if len(items) == 1:
            return items[0]
        return ("cat", items)

    def parse_expression(self, nest):
        tok = self.tok
        t = tok[0]
        if t == "CHAR":
            node = ("char", tok[1])
        elif t == "ANY":
            node = ("any",)
        elif t == "SET":
            node = ("set", tok[1], tok[2])
        elif t == "WORD":
            node = ("word", True)
        elif t == "NOTWORD":
            node = ("word", False)
        elif t == "SPACE":
            node = ("space", True)
        elif t == "NOTSPACE":
            node = ("space", False)
        elif t == "BACKREF":
            if tok[1] not in self.completed:
                raise RegexError("Invalid back reference")
            node = ("backref", tok[1])
        elif t == "OPEN":
            self.ngroups += 1
            idx = self.ngroups
            self.fetch(True)
            if self.tok[0] == "CLOSE":
                inner = ("cat", [])
            else:
                inner = self.parse_reg_exp(nest + 1)
                if self.tok[0] != "CLOSE":
                    raise RegexError("Unmatched ( or \\(")
            self.completed.add(idx)
            node = ("group", idx, inner)
        elif t == "ANCHOR":
            node = ("anchor", tok[1])
            self.fetch(True)
            return node
        elif t in ("STAR", "PLUS", "QUES"):
            node = ("char", {"STAR": "*", "PLUS": "+", "QUES": "?"}[t])
        elif t == "CLOSE":
            raise RegexError("Unmatched ) or \\)")
        else:
            raise RegexError("internal")
        self.fetch(False)
        while self.tok[0] in ("STAR", "PLUS", "QUES"):
            t = self.tok[0]
            if t == "STAR":
                node = ("rep", node, 0, None)
            elif t == "PLUS":
                node = ("rep", node, 1, None)
            else:
                node = ("rep", node, 0, 1)
            self.fetch(False)
        return node

    # -- matcher ---------------------------------------------------------
    def search(self, s, start):
        """Return (start, end, caps) for the leftmost-longest match at or
        after START, or None."""
        n = len(s)
        caps = [None] * (self.ngroups + 1)
        state = {"best": None, "steps": 0}

        def isword(ch):
            return ch.isalnum() and ch.isascii() or ch == "_"

        def comp(node):
            kind = node[0]
            if kind == "char":
                c = node[1]

                def m(i, k):
                    return i < n and s[i] == c and k(i + 1)
                return m
            if kind == "any":
                def m(i, k):
                    return i < n and s[i] != "\n" and k(i + 1)
                return m
            if kind == "set":
                cs, neg = node[1], node[2]
                if neg:
                    def m(i, k):
                        return i < n and s[i] not in cs and k(i + 1)
                else:
                    def m(i, k):
                        return i < n and s[i] in cs and k(i + 1)
                return m
            if kind == "word":
                want = node[1]

                def m(i, k):
                    return i < n and isword(s[i]) == want and k(i + 1)
                return m
            if kind == "space":
                want = node[1]

                def m(i, k):
                    return i < n and (s[i] in C_SPACE) == want and k(i + 1)
                return m
            if kind == "backref":
                g = node[1]

                def m(i, k):
                    c = caps[g]
                    if c is None:
                        return False
                    sub = s[c[0]:c[1]]
                    if s.startswith(sub, i):
                        return k(i + len(sub))
                    return False
                return m
            if kind == "anchor":
                a = node[1]
                if a == "bol":
                    def test(i):
                        return i == 0 or s[i - 1] == "\n"
                elif a == "eol":
                    def test(i):
                        return i == n or s[i] == "\n"
                elif a == "bufstart":
                    def test(i):
                        return i == 0
                elif a == "bufend":
                    def test(i):
                        return i == n
                else:
                    def test(i, a=a):
                        pw = i > 0 and isword(s[i - 1])
                        nw = i < n and isword(s[i])
                        if a == "wbeg":
                            return nw and not pw
                        if a == "wend":
                            return pw and not nw
                        if a == "wbound":
                            return pw != nw
                        return pw == nw

                def m(i, k):
                    return test(i) and k(i)
                return m
            if kind == "cat":
                items = [comp(x) for x in node[1]]
                if not items:
                    return lambda i, k: k(i)
                f = items[-1]
                for g in reversed(items[:-1]):
                    f = (lambda a, b: (lambda i, k: a(i, lambda j: b(j, k))))(g, f)
                return f
            if kind == "alt":
                alts = [comp(x) for x in node[1]]

                def m(i, k):
                    for a in alts:
                        if a(i, k):
                            return True
                    return False
                return m
            if kind == "group":
                g = node[1]
                inner = comp(node[2])

                def m(i, k):
                    def k2(j):
                        prev = caps[g]
                        caps[g] = (i, j)
                        if k(j):
                            return True
                        caps[g] = prev
                        return False
                    return inner(i, k2)
                return m
            if kind == "rep":
                body = comp(node[1])
                mn, mx = node[2], node[3]

                def m(i, k):
                    def loop(i, count):
                        state["steps"] += 1
                        if state["steps"] > 400000:
                            raise _Stop()
                        if mx is None or count < mx:
                            def k2(j):
                                if j == i:
                                    # An empty iteration is only useful to
                                    # satisfy a minimum count.
                                    return count < mn and k(j)
                                return loop(j, count + 1)
                            if body(i, k2):
                                return True
                        if count >= mn:
                            return k(i)
                        return False
                    return loop(i, 0)
                return m
            raise RegexError("internal")

        if not hasattr(self, "_compiled_for") or self._compiled_for is not s:
            pass
        matcher = comp(self.ast)

        for st in range(start, n + 1):
            state["best"] = None
            state["steps"] = 0
            for g in range(len(caps)):
                caps[g] = None

            def final(j):
                b = state["best"]
                if b is None or j > b[0]:
                    state["best"] = (j, list(caps))
                return j == n

            try:
                matcher(st, final)
            except _Stop:
                pass
            except RecursionError:
                pass
            b = state["best"]
            if b is not None:
                return st, b[0], b[1]
        return None


_regex_cache = {}


def compile_regex(pat):
    r = _regex_cache.get(pat)
    if r is None:
        r = Regex(pat)
        _regex_cache[pat] = r
    return r


# ---------------------------------------------------------------------------
# Eval

(E_NO_ERROR, E_DIVIDE_ZERO, E_MODULO_ZERO, E_NEGATIVE_EXPONENT, E_SYNTAX_ERROR,
 E_MISSING_RIGHT, E_UNKNOWN_INPUT, E_EXCESS_INPUT, E_INVALID_OPERATOR) = range(9)

(ET_ERROR, ET_BADOP, ET_PLUS, ET_MINUS, ET_EXPONENT, ET_TIMES, ET_DIVIDE,
 ET_MODULO, ET_ASSIGN, ET_EQ, ET_NOTEQ, ET_GT, ET_GTEQ, ET_LS, ET_LSEQ,
 ET_LSHIFT, ET_RSHIFT, ET_LNOT, ET_LAND, ET_LOR, ET_NOT, ET_AND, ET_OR,
 ET_XOR, ET_LEFTP, ET_RIGHTP, ET_NUMBER, ET_EOTEXT) = range(28)


def c_div(a, b):
    q = abs(a) // abs(b)
    if (a < 0) != (b < 0):
        q = -q
    return q


def c_mod(a, b):
    return a - b * c_div(a, b)


class Evaluator(object):
    def __init__(self, text, warn):
        self.s = text
        self.i = 0
        self.last = 0
        self.warn = warn

    def lex(self):
        s = self.s
        n = len(s)
        i = self.i
        while i < n and s[i] in C_SPACE:
            i += 1
        self.last = i
        if i >= n:
            self.i = i
            return ET_EOTEXT, 0
        c = s[i]
        if "0" <= c <= "9":
            if c == "0":
                i += 1
                c2 = s[i] if i < n else ""
                if c2 in ("x", "X"):
                    base = 16
                    i += 1
                elif c2 in ("b", "B"):
                    base = 2
                    i += 1
                elif c2 in ("r", "R"):
                    base = 0
                    i += 1
                    while i < n and "0" <= s[i] <= "9" and base <= 36:
                        base = 10 * base + ord(s[i]) - 48
                        i += 1
                    if base == 0 or base > 36 or i >= n or s[i] != ":":
                        self.i = i
                        return ET_ERROR, 0
                    i += 1
                else:
                    base = 8
            else:
                base = 10
            value = 0
            while i < n:
                ch = s[i]
                if "0" <= ch <= "9":
                    digit = ord(ch) - 48
                elif "a" <= ch <= "z":
                    digit = ord(ch) - 97 + 10
                elif "A" <= ch <= "Z":
                    digit = ord(ch) - 65 + 10
                else:
                    break
                if base == 1:
                    if digit == 1:
                        value = (value + 1) & 0xFFFFFFFF
                    elif digit == 0 and value == 0:
                        i += 1
                        continue
                    else:
                        break
                elif digit >= base:
                    break
                else:
                    value = (value * base + digit) & 0xFFFFFFFF
                i += 1
            self.i = i
            return ET_NUMBER, to_i32(value)
        i += 1
        nx = s[i] if i < n else ""
        tok = ET_ERROR
        if c == "+":
            tok = ET_BADOP if nx in ("+", "=") else ET_PLUS
        elif c == "-":
            tok = ET_BADOP if nx in ("-", "=") else ET_MINUS
        elif c == "*":
            if nx == "*":
                i += 1
                tok = ET_EXPONENT
            elif nx == "=":
                tok = ET_BADOP
            else:
                tok = ET_TIMES
        elif c == "/":
            tok = ET_BADOP if nx == "=" else ET_DIVIDE
        elif c == "%":
            tok = ET_BADOP if nx == "=" else ET_MODULO
        elif c == "=":
            if nx == "=":
                i += 1
                tok = ET_EQ
            else:
                tok = ET_ASSIGN
        elif c == "!":
            if nx == "=":
                i += 1
                tok = ET_NOTEQ
            else:
                tok = ET_LNOT
        elif c == ">":
            if nx == "=":
                i += 1
                tok = ET_GTEQ
            elif nx == ">":
                i += 1
                if i < n and s[i] == "=":
                    tok = ET_BADOP
                else:
                    tok = ET_RSHIFT
            else:
                tok = ET_GT
        elif c == "<":
            if nx == "=":
                i += 1
                tok = ET_LSEQ
            elif nx == "<":
                i += 1
                if i < n and s[i] == "=":
                    tok = ET_BADOP
                else:
                    tok = ET_LSHIFT
            else:
                tok = ET_LS
        elif c == "^":
            tok = ET_BADOP if nx == "=" else ET_XOR
        elif c == "~":
            tok = ET_NOT
        elif c == "&":
            if nx == "&":
                i += 1
                tok = ET_LAND
            elif nx == "=":
                tok = ET_BADOP
            else:
                tok = ET_AND
        elif c == "|":
            if nx == "|":
                i += 1
                tok = ET_LOR
            elif nx == "=":
                tok = ET_BADOP
            else:
                tok = ET_OR
        elif c == "(":
            tok = ET_LEFTP
        elif c == ")":
            tok = ET_RIGHTP
        self.i = i
        return tok, 0

    def undo(self):
        self.i = self.last

    def evaluate(self):
        et, v = self.lex()
        er, v = self.logical_or(et, v)
        if er == E_NO_ERROR and self.i < len(self.s):
            t, _ = self.lex()
            er = E_INVALID_OPERATOR if t == ET_BADOP else E_EXCESS_INPUT
        return er, v

    def logical_or(self, et, v1):
        er, v1 = self.logical_and(et, v1)
        if er != E_NO_ERROR:
            return er, v1
        while True:
            et, v2 = self.lex()
            if et != ET_LOR:
                break
            et, v2 = self.lex()
            if et == ET_ERROR:
                return E_UNKNOWN_INPUT, v1
            er, v2 = self.logical_and(et, v2)
            if er == E_NO_ERROR:
                v1 = 1 if (v1 or v2) else 0
            elif v1 != 0 and er < E_SYNTAX_ERROR:
                v1 = 1
            else:
                return er, v1
        if et == ET_ERROR:
            return E_UNKNOWN_INPUT, v1
        self.undo()
        return E_NO_ERROR, v1

    def logical_and(self, et, v1):
        er, v1 = self.or_term(et, v1)
        if er != E_NO_ERROR:
            return er, v1
        while True:
            et, v2 = self.lex()
            if et != ET_LAND:
                break
            et, v2 = self.lex()
            if et == ET_ERROR:
                return E_UNKNOWN_INPUT, v1
            er, v2 = self.or_term(et, v2)
            if er == E_NO_ERROR:
                v1 = 1 if (v1 and v2) else 0
            elif v1 == 0 and er < E_SYNTAX_ERROR:
                pass
            else:
                return er, v1
        if et == ET_ERROR:
            return E_UNKNOWN_INPUT, v1
        self.undo()
        return E_NO_ERROR, v1

    def _binary(self, et, v1, sub, ops, apply):
        er, v1 = sub(et, v1)
        if er != E_NO_ERROR:
            return er, v1
        while True:
            op, v2 = self.lex()
            if op not in ops:
                break
            et, v2 = self.lex()
            if et == ET_ERROR:
                return E_UNKNOWN_INPUT, v1
            er, v2 = sub(et, v2)
            if er != E_NO_ERROR:
                return er, v1
            r = apply(op, v1, v2)
            if isinstance(r, tuple):
                return r
            v1 = r
        if op == ET_ERROR:
            return E_UNKNOWN_INPUT, v1
        self.undo()
        return E_NO_ERROR, v1

    def or_term(self, et, v1):
        return self._binary(et, v1, self.xor_term, (ET_OR,),
                            lambda op, a, b: to_i32(a | b))

    def xor_term(self, et, v1):
        return self._binary(et, v1, self.and_term, (ET_XOR,),
                            lambda op, a, b: to_i32(a ^ b))

    def and_term(self, et, v1):
        return self._binary(et, v1, self.equality_term, (ET_AND,),
                            lambda op, a, b: to_i32(a & b))

    def equality_term(self, et, v1):
        def apply(op, a, b):
            if op == ET_ASSIGN:
                self.warn("Warning: recommend ==, not =, for equality operator")
                op = ET_EQ
            return 1 if ((op == ET_EQ) == (a == b)) else 0
        return self._binary(et, v1, self.cmp_term, (ET_EQ, ET_NOTEQ, ET_ASSIGN), apply)

    def cmp_term(self, et, v1):
        def apply(op, a, b):
            if op == ET_GT:
                return 1 if a > b else 0
            if op == ET_GTEQ:
                return 1 if a >= b else 0
            if op == ET_LS:
                return 1 if a < b else 0
            return 1 if a <= b else 0
        return self._binary(et, v1, self.shift_term, (ET_GT, ET_GTEQ, ET_LS, ET_LSEQ), apply)

    def shift_term(self, et, v1):
        def apply(op, a, b):
            sh = b & 0x1F
            if op == ET_LSHIFT:
                return to_i32((a & 0xFFFFFFFF) << sh)
            return to_i32(a >> sh)
        return self._binary(et, v1, self.add_term, (ET_LSHIFT, ET_RSHIFT), apply)

    def add_term(self, et, v1):
        def apply(op, a, b):
            if op == ET_PLUS:
                return to_i32(a + b)
            return to_i32(a - b)
        return self._binary(et, v1, self.mult_term, (ET_PLUS, ET_MINUS), apply)

    def mult_term(self, et, v1):
        def apply(op, a, b):
            if op == ET_TIMES:
                return to_i32(a * b)
            if op == ET_DIVIDE:
                if b == 0:
                    return (E_DIVIDE_ZERO, a)
                if b == -1:
                    return to_i32(-a)
                return to_i32(c_div(a, b))
            if b == 0:
                return (E_MODULO_ZERO, a)
            if b == -1:
                return 0
            return to_i32(c_mod(a, b))
        return self._binary(et, v1, self.exp_term, (ET_TIMES, ET_DIVIDE, ET_MODULO), apply)

    def exp_term(self, et, v1):
        er, v1 = self.unary_term(et, v1)
        if er != E_NO_ERROR:
            return er, v1
        while True:
            et, v2 = self.lex()
            if et != ET_EXPONENT:
                break
            et, v2 = self.lex()
            if et == ET_ERROR:
                return E_UNKNOWN_INPUT, v1
            er, v2 = self.exp_term(et, v2)
            if er != E_NO_ERROR:
                return er, v1
            if v2 < 0:
                return E_NEGATIVE_EXPONENT, v1
            if v1 == 0 and v2 == 0:
                return E_DIVIDE_ZERO, v1
            v1 = to_i32(pow(v1 & 0xFFFFFFFF, v2, 1 << 32))
        if et == ET_ERROR:
            return E_UNKNOWN_INPUT, v1
        self.undo()
        return E_NO_ERROR, v1

    def unary_term(self, et, v1):
        if et in (ET_PLUS, ET_MINUS, ET_NOT, ET_LNOT):
            et2, v1 = self.lex()
            if et2 == ET_ERROR:
                return E_UNKNOWN_INPUT, v1
            er, v1 = self.unary_term(et2, v1)
            if er != E_NO_ERROR:
                return er, v1
            if et == ET_MINUS:
                v1 = to_i32(-v1)
            elif et == ET_NOT:
                v1 = to_i32(~v1)
            elif et == ET_LNOT:
                v1 = 1 if v1 == 0 else 0
            return E_NO_ERROR, v1
        return self.simple_term(et, v1)

    def simple_term(self, et, v1):
        if et == ET_LEFTP:
            et, v1 = self.lex()
            if et == ET_ERROR:
                return E_UNKNOWN_INPUT, v1
            er, v1 = self.logical_or(et, v1)
            if er != E_NO_ERROR:
                return er, v1
            et, v2 = self.lex()
            if et == ET_ERROR:
                return E_UNKNOWN_INPUT, v1
            if et != ET_RIGHTP:
                return E_MISSING_RIGHT, v1
            return E_NO_ERROR, v1
        if et == ET_NUMBER:
            return E_NO_ERROR, v1
        if et == ET_BADOP:
            return E_INVALID_OPERATOR, v1
        return E_SYNTAX_ERROR, v1


EVAL_MESSAGES = {
    E_DIVIDE_ZERO: "divide by zero in eval: %s",
    E_MODULO_ZERO: "modulo by zero in eval: %s",
    E_NEGATIVE_EXPONENT: "negative exponent in eval: %s",
    E_SYNTAX_ERROR: "bad expression in eval: %s",
    E_MISSING_RIGHT: "bad expression in eval (missing right parenthesis): %s",
    E_UNKNOWN_INPUT: "bad expression in eval (bad input): %s",
    E_EXCESS_INPUT: "bad expression in eval (excess input): %s",
    E_INVALID_OPERATOR: "invalid operator in eval: %s",
}

DIGITS36 = "0123456789abcdefghijklmnopqrstuvwxyz"


def ntoa(value, radix):
    neg = value < 0
    u = -value if neg else value
    if u == 0:
        s = "0"
    else:
        out = []
        while u:
            out.append(DIGITS36[u % radix])
            u //= radix
        s = "".join(reversed(out))
    return ("-" + s) if neg else s


# ---------------------------------------------------------------------------
# printf-style formatting helpers

def format_hexfloat(v, conv, flags, width, prec):
    import math
    upper = conv == "A"
    if math.isnan(v) or math.isinf(v):
        if math.isnan(v):
            body = "nan"
            neg = math.copysign(1.0, v) < 0
        else:
            body = "inf"
            neg = v < 0
        if upper:
            body = body.upper()
        sign = "-" if neg else ("+" if "+" in flags else (" " if " " in flags else ""))
        s = sign + body
        if len(s) < width:
            if "-" in flags:
                s = s + " " * (width - len(s))
            else:
                s = " " * (width - len(s)) + s
        return s
    neg = math.copysign(1.0, v) < 0
    a = abs(v)
    if a == 0.0:
        lead = 0
        mant = 0
        exp = 0
    else:
        m, e = math.frexp(a)  # a = m * 2**e, 0.5 <= m < 1
        if e - 1 < -1022:
            # subnormal: glibc prints 0x0.xxxp-1022
            lead = 0
            mant = int(a * (2.0 ** 1074))  # 52-bit fraction
            exp = -1022
        else:
            ival = int(m * (1 << 53))  # 53 bits
            lead = 1
            mant = ival - (1 << 52)
            exp = e - 1
    digits = "%013x" % mant
    if prec < 0:
        digits = digits.rstrip("0")
    else:
        if prec < 13:
            keep = digits[:prec]
            rest = digits[prec:]
            full = (lead << (4 * prec)) | (int(keep, 16) if keep else 0)
            restv = int(rest, 16)
            half = 8 << (4 * (len(rest) - 1))
            if restv > half or (restv == half and (full & 1)):
                full += 1
            lead = full >> (4 * prec)
            fracv = full & ((1 << (4 * prec)) - 1)
            digits = ("%0*x" % (prec, fracv)) if prec > 0 else ""
        else:
            digits = digits + "0" * (prec - 13)
    s = "%x" % lead
    if digits or "#" in flags:
        s += "." + digits
    s += "p%+d" % exp
    prefix = "0x"
    if upper:
        s = s.upper()
        prefix = "0X"
    sign = "-" if neg else ("+" if "+" in flags else (" " if " " in flags else ""))
    total = len(sign) + len(prefix) + len(s)
    if total < width:
        pad = width - total
        if "-" in flags:
            return sign + prefix + s + " " * pad
        if "0" in flags:
            return sign + prefix + "0" * pad + s
        return " " * pad + sign + prefix + s
    return sign + prefix + s


def format_float(v, conv, flags, width, prec):
    import math
    if conv in "aA":
        return format_hexfloat(v, conv, flags, width, prec)
    if math.isnan(v) or math.isinf(v):
        if math.isnan(v):
            body = "nan"
            neg = math.copysign(1.0, v) < 0
        else:
            body = "inf"
            neg = v < 0
        if conv in "EFG":
            body = body.upper()
        sign = "-" if neg else ("+" if "+" in flags else (" " if " " in flags else ""))
        s = sign + body
        if len(s) < width:
            if "-" in flags:
                s = s + " " * (width - len(s))
            else:
                s = " " * (width - len(s)) + s
        return s
    spec = "%" + "".join(f for f in "-+ 0#" if f in flags)
    if width:
        spec += str(width)
    if prec >= 0:
        spec += "." + str(prec)
    spec += conv
    try:
        return spec % v
    except (ValueError, OverflowError):
        return ""


def format_int(value, conv, flags, width, prec):
    if conv in "di":
        neg = value < 0
        mag = -value if neg else value
    else:
        neg = False
        mag = value
    if conv in "diu":
        digits = str(mag)
    elif conv == "o":
        digits = "%o" % mag
    elif conv == "x":
        digits = "%x" % mag
    else:
        digits = "%X" % mag
    if prec >= 0:
        if prec == 0 and mag == 0:
            digits = ""
        if len(digits) < prec:
            digits = "0" * (prec - len(digits)) + digits
    if "#" in flags and conv == "o" and not digits.startswith("0"):
        digits = "0" + digits
    prefix = ""
    if conv in "di":
        if neg:
            prefix = "-"
        elif "+" in flags:
            prefix = "+"
        elif " " in flags:
            prefix = " "
    if "#" in flags and conv in "xX" and mag != 0:
        prefix += "0x" if conv == "x" else "0X"
    total = len(prefix) + len(digits)
    if total < width:
        pad = width - total
        if "-" in flags:
            return prefix + digits + " " * pad
        if "0" in flags and prec < 0:
            return prefix + "0" * pad + digits
        return " " * pad + prefix + digits
    return prefix + digits


# ---------------------------------------------------------------------------
# Data structures

class Block(object):
    __slots__ = ("kind", "text", "pos", "file", "line", "advance", "func")

    def __init__(self, kind, text, file, line):
        self.kind = kind
        self.text = text
        self.pos = 0
        self.file = file
        self.line = line
        self.advance = False
        self.func = None


class Builtin(object):
    __slots__ = ("name", "func", "blind", "groks")

    def __init__(self, name, func, blind, groks):
        self.name = name
        self.func = func
        self.blind = blind
        self.groks = groks


class Def(object):
    __slots__ = ("text", "builtin")

    def __init__(self, text=None, builtin=None):
        self.text = text
        self.builtin = builtin


def argtext(a):
    return a if isinstance(a, str) else ""


# ---------------------------------------------------------------------------
# The interpreter

class M4(object):
    def __init__(self):
        self.stack = []
        self.wrapup = []
        self.cur_file = ""
        self.cur_line = 0
        self.start_of_line = False
        self.input_change = False
        self.lquote = "`"
        self.rquote = "'"
        self.bcomm = "#"
        self.ecomm = "\n"
        self.symtab = {}
        self.cur_div = 0
        self.divs = {}
        self.out0 = []
        self.retcode = 0
        self.stdin_used = False
        self.builtins = {}
        self.init_builtins()

    # -- diagnostics -----------------------------------------------------
    def stderr(self, text):
        try:
            sys.stderr.buffer.write(text.encode("latin-1", "replace"))
            sys.stderr.buffer.flush()
        except Exception:
            pass

    def warn(self, msg):
        self.stderr("%s:%s:%d: %s\n" % (PROGRAM_NAME, self.cur_file, self.cur_line, msg))

    def fatal(self, msg, file=None, line=None):
        if file is None:
            file, line = self.cur_file, self.cur_line
        self.stderr("%s:%s:%d: %s\n" % (PROGRAM_NAME, file, line, msg))
        raise Fatal()

    # -- output ----------------------------------------------------------
    def output(self, text):
        d = self.cur_div
        if d == 0:
            self.out0.append(text)
        elif d > 0:
            lst = self.divs.get(d)
            if lst is None:
                lst = self.divs[d] = []
            lst.append(text)

    def shipout(self, obs, text):
        if obs is not None:
            obs.append(text)
        else:
            self.output(text)

    def flush_stdout(self):
        data = "".join(self.out0)
        self.out0 = []
        try:
            sys.stdout.buffer.write(data.encode("latin-1", "replace"))
            sys.stdout.buffer.flush()
        except Exception:
            pass

    def make_diversion(self, n):
        self.cur_div = n
        if n > 0 and n not in self.divs:
            self.divs[n] = []

    def insert_diversion(self, n):
        if n <= 0 or n == self.cur_div:
            return
        lst = self.divs.get(n)
        if lst is None:
            return
        del self.divs[n]
        text = "".join(lst)
        if text:
            self.output(text)

    def undivert_all(self):
        for n in sorted(self.divs.keys()):
            if n != self.cur_div:
                self.insert_diversion(n)

    # -- input -----------------------------------------------------------
    def push_file(self, text, name):
        b = Block(K_FILE, text, name, 1)
        b.advance = self.start_of_line
        self.start_of_line = False
        self.stack.append(b)
        self.input_change = True
        self.cur_file = name
        self.cur_line = 1

    def push_string(self, text, file, line):
        if text:
            self.stack.append(Block(K_STR, text, file, line))
            self.input_change = True

    def push_macro(self, bi):
        b = Block(K_MACRO, "", self.cur_file, self.cur_line)
        b.func = bi
        self.stack.append(b)
        self.input_change = True

    def pop_input(self):
        b = self.stack.pop()
        if b.kind == K_FILE:
            self.start_of_line = b.advance
        self.input_change = True

    def push_wrapup(self, text):
        self.wrapup.append(Block(K_STR, text, self.cur_file, self.cur_line))

    def pop_wrapup(self):
        if not self.wrapup:
            return False
        self.stack = self.wrapup
        self.wrapup = []
        self.input_change = True
        return True

    def peek_char(self):
        stack = self.stack
        i = len(stack) - 1
        while i >= 0:
            b = stack[i]
            if b.kind == K_MACRO:
                return MACRO_MARK
            if b.pos < len(b.text):
                return b.text[b.pos]
            i -= 1
        return EOF

    def lookahead(self, n):
        """Return up to N upcoming characters without consuming them."""
        stack = self.stack
        res = ""
        i = len(stack) - 1
        while i >= 0 and len(res) < n:
            b = stack[i]
            if b.kind == K_MACRO:
                break
            res += b.text[b.pos:b.pos + (n - len(res))]
            i -= 1
        return res

    def next_char(self):
        stack = self.stack
        while True:
            if not stack:
                self.cur_file = ""
                self.cur_line = 0
                return EOF
            b = stack[-1]
            if self.input_change:
                self.cur_file = b.file
                self.cur_line = b.line
                self.input_change = False
            k = b.kind
            if k == K_STR:
                p = b.pos
                if p < len(b.text):
                    b.pos = p + 1
                    return b.text[p]
            elif k == K_FILE:
                if self.start_of_line:
                    self.start_of_line = False
                    b.line += 1
                    self.cur_line = b.line
                p = b.pos
                if p < len(b.text):
                    b.pos = p + 1
                    c = b.text[p]
                    if c == "\n":
                        self.start_of_line = True
                    return c
            else:
                self.pop_input()
                return b.func
            self.pop_input()

    def match_rest(self, s):
        """First char of S already consumed; match and consume the rest."""
        if len(s) == 1:
            return True
        rest = s[1:]
        if self.lookahead(len(rest)) == rest:
            for _ in range(len(rest)):
                self.next_char()
            return True
        return False

    def peek_match(self, s):
        return self.lookahead(len(s)) == s

    def next_token(self):
        ch = self.peek_char()
        if ch is EOF:
            self.next_char()
            return T_EOF, None
        if ch is MACRO_MARK:
            f = self.next_char()
            return T_MACDEF, f
        self.next_char()
        bc = self.bcomm
        if bc and ch == bc[0] and self.match_rest(bc):
            file, line = self.cur_file, self.cur_line
            ec = self.ecomm
            ec0 = ec[0]
            parts = [bc]
            while True:
                b = self.stack[-1] if self.stack else None
                if b is not None and b.kind == K_STR and not self.input_change:
                    t = b.text
                    p = b.pos
                    j = t.find(ec0, p)
                    if j < 0:
                        j = len(t)
                    if j > p:
                        parts.append(t[p:j])
                        b.pos = j
                        continue
                c = self.next_char()
                if c is EOF:
                    self.fatal("ERROR: end of file in comment", file, line)
                if not isinstance(c, str):
                    continue
                if c == ec0 and self.match_rest(ec):
                    parts.append(ec)
                    break
                parts.append(c)
            return T_STRING, "".join(parts)
        if ch in WORD_START:
            parts = [ch]
            while True:
                b = self.stack[-1] if self.stack else None
                if b is not None and b.kind == K_STR and not self.input_change and b.pos < len(b.text):
                    m = WORD_RE.match(b.text, b.pos)
                    e = m.end()
                    if e > b.pos:
                        parts.append(b.text[b.pos:e])
                        b.pos = e
                    if e < len(b.text):
                        break
                c = self.peek_char()
                if isinstance(c, str) and c in WORD_CHARS:
                    self.next_char()
                    parts.append(c)
                else:
                    break
            return T_WORD, "".join(parts)
        lq = self.lquote
        if lq and ch == lq[0] and self.match_rest(lq):
            file, line = self.cur_file, self.cur_line
            rq = self.rquote
            rq0 = rq[0]
            lq0 = lq[0]
            level = 1
            parts = []
            while True:
                b = self.stack[-1] if self.stack else None
                if b is not None and b.kind == K_STR and not self.input_change:
                    t = b.text
                    p = b.pos
                    j = len(t)
                    x = t.find(rq0, p)
                    if 0 <= x < j:
                        j = x
                    x = t.find(lq0, p, j)
                    if 0 <= x < j:
                        j = x
                    if j > p:
                        parts.append(t[p:j])
                        b.pos = j
                        continue
                c = self.next_char()
                if c is EOF:
                    self.fatal("ERROR: end of file in string", file, line)
                if not isinstance(c, str):
                    continue
                if c == rq0 and self.match_rest(rq):
                    level -= 1
                    if level == 0:
                        break
                    parts.append(rq)
                elif c == lq0 and self.match_rest(lq):
                    level += 1
                    parts.append(lq)
                else:
                    parts.append(c)
            return T_STRING, "".join(parts)
        if ch == "(":
            return T_OPEN, ch
        if ch == ",":
            return T_COMMA, ch
        if ch == ")":
            return T_CLOSE, ch
        return T_SIMPLE, ch

    def peek_token(self):
        ch = self.peek_char()
        if ch is EOF:
            return T_EOF
        if ch is MACRO_MARK:
            return T_MACDEF
        bc = self.bcomm
        if bc and ch == bc[0] and self.peek_match(bc):
            return T_STRING
        if ch in WORD_START:
            return T_WORD
        lq = self.lquote
        if lq and ch == lq[0] and self.peek_match(lq):
            return T_STRING
        if ch == "(":
            return T_OPEN
        if ch == ",":
            return T_COMMA
        if ch == ")":
            return T_CLOSE
        return T_SIMPLE

    # -- symbols ---------------------------------------------------------
    def lookup(self, name):
        st = self.symtab.get(name)
        if st:
            return st[-1]
        return None

    def define(self, name, d, push=False):
        st = self.symtab.get(name)
        if not st:
            self.symtab[name] = [d]
        elif push:
            st.append(d)
        else:
            st[-1] = d

    def undefine(self, name):
        self.symtab.pop(name, None)

    def popdef(self, name):
        st = self.symtab.get(name)
        if st:
            st.pop()
            if not st:
                del self.symtab[name]

    # -- expansion -------------------------------------------------------
    def expand_input(self):
        next_token = self.next_token
        expand_token = self.expand_token
        while True:
            t, d = next_token()
            if t == T_EOF:
                return
            expand_token(None, t, d)

    def expand_token(self, obs, t, data):
        if t == T_WORD:
            d = self.lookup(data)
            if d is None or (d.builtin is not None and d.builtin.blind
                             and self.peek_token() != T_OPEN):
                self.shipout(obs, data)
            else:
                self.expand_macro(data, d)
        elif t == T_MACDEF or t == T_EOF:
            pass
        else:
            self.shipout(obs, data)

    def expand_macro(self, name, d):
        open_file, open_line = self.cur_file, self.cur_line
        argv = self.collect_arguments(name, d)
        close_file, close_line = self.cur_file, self.cur_line
        self.cur_file, self.cur_line = open_file, open_line
        out = []
        self.call_macro(d, argv, out)
        if out:
            self.push_string("".join(out), open_file, open_line)
        self.cur_file, self.cur_line = close_file, close_line

    def collect_arguments(self, name, d):
        argv = [name]
        groks = d.builtin is not None and d.builtin.groks
        if self.peek_token() == T_OPEN:
            self.next_token()
            while True:
                more, arg = self.expand_argument()
                if not groks and not isinstance(arg, str):
                    arg = ""
                argv.append(arg)
                if not more:
                    break
        return argv

    def expand_argument(self):
        file, line = self.cur_file, self.cur_line
        buf = []
        func = None
        next_token = self.next_token
        while True:
            t, data = next_token()
            if not (t == T_SIMPLE and data in C_SPACE):
                break
        paren = 0
        while True:
            if t == T_COMMA or t == T_CLOSE:
                if paren == 0:
                    if func is not None:
                        return t == T_COMMA, func
                    return t == T_COMMA, "".join(buf)
                if t == T_CLOSE:
                    paren -= 1
                buf.append(data)
            elif t == T_OPEN:
                paren += 1
                buf.append(data)
            elif t == T_SIMPLE:
                buf.append(data)
            elif t == T_WORD or t == T_STRING:
                self.expand_token(buf, t, data)
            elif t == T_MACDEF:
                if not any(buf):
                    func = data
            elif t == T_EOF:
                self.fatal("ERROR: end of file in argument list", file, line)
            t, data = next_token()

    def call_macro(self, d, argv, out):
        if d.builtin is not None:
            d.builtin.func(argv, out)
        else:
            self.expand_user_macro(d.text, argv, out)

    def expand_user_macro(self, text, argv, out):
        argc = len(argv)
        i = 0
        n = len(text)
        while True:
            j = text.find("$", i)
            if j < 0:
                out.append(text[i:])
                return
            out.append(text[i:j])
            j += 1
            c = text[j] if j < n else ""
            if "0" <= c <= "9":
                k = j
                while k < n and "0" <= text[k] <= "9":
                    k += 1
                idx = int(text[j:k])
                if idx < argc:
                    out.append(argtext(argv[idx]))
                i = k
            elif c == "#":
                out.append(str(argc - 1))
                i = j + 1
            elif c == "*" or c == "@":
                self.dump_args(out, argv, ",", c == "@")
                i = j + 1
            else:
                out.append("$")
                i = j

    def dump_args(self, out, argv, sep, quoted):
        lq, rq = self.lquote, self.rquote
        for i in range(1, len(argv)):
            if i > 1:
                out.append(sep)
            if quoted:
                out.append(lq)
            out.append(argtext(argv[i]))
            if quoted:
                out.append(rq)

    # -- builtin helpers -------------------------------------------------
    def bad_argc(self, argv, mn, mx):
        argc = len(argv)
        name = argtext(argv[0])
        if mn > 0 and argc < mn:
            self.warn("Warning: too few arguments to builtin `%s'" % name)
            return True
        if mx > 0 and argc > mx:
            self.warn("Warning: excess arguments to builtin `%s' ignored" % name)
        return False

    def numeric_arg(self, argv, s):
        """Return int value or None."""
        name = argtext(argv[0])
        if s == "":
            self.warn("empty string treated as 0 in builtin `%s'" % name)
            return 0
        v, end, ovf = c_strtol(s)
        if end != len(s):
            self.warn("non-numeric argument to builtin `%s'" % name)
            return None
        if s[0] in C_SPACE:
            self.warn("leading whitespace ignored in builtin `%s'" % name)
        elif ovf:
            self.warn("numeric overflow detected in builtin `%s'" % name)
        return to_i32(v)

    def read_file(self, name):
        if name == "":
            return None
        try:
            if os.path.isdir(name):
                return None
            with open(name, "rb") as f:
                return f.read().decode("latin-1")
        except (OSError, IOError):
            return None

    # -- builtins --------------------------------------------------------
    def init_builtins(self):
        tab = [
            # name, func, blind, groks
            ("__file__", self.b_file, False, False),
            ("__line__", self.b_line, False, False),
            ("__program__", self.b_program, False, False),
            ("builtin", self.b_builtin, True, True),
            ("changecom", self.b_changecom, False, False),
            ("changequote", self.b_changequote, False, False),
            ("debugfile", self.b_noop, False, False),
            ("debugmode", self.b_noop, False, False),
            ("decr", self.b_decr, True, False),
            ("define", self.b_define, True, True),
            ("defn", self.b_defn, True, False),
            ("divert", self.b_divert, False, False),
            ("divnum", self.b_divnum, False, False),
            ("dnl", self.b_dnl, False, False),
            ("dumpdef", self.b_dumpdef, False, False),
            ("errprint", self.b_errprint, True, False),
            ("esyscmd", self.b_noop, True, False),
            ("eval", self.b_eval, True, False),
            ("format", self.b_format, True, False),
            ("ifdef", self.b_ifdef, True, False),
            ("ifelse", self.b_ifelse, True, False),
            ("include", self.b_include, True, False),
            ("incr", self.b_incr, True, False),
            ("index", self.b_index, True, False),
            ("indir", self.b_indir, True, True),
            ("len", self.b_len, True, False),
            ("m4exit", self.b_m4exit, False, False),
            ("m4wrap", self.b_m4wrap, True, False),
            ("maketemp", self.b_noop, True, False),
            ("mkstemp", self.b_noop, True, False),
            ("patsubst", self.b_patsubst, True, False),
            ("popdef", self.b_popdef, True, False),
            ("pushdef", self.b_pushdef, True, True),
            ("regexp", self.b_regexp, True, False),
            ("shift", self.b_shift, True, False),
            ("sinclude", self.b_sinclude, True, False),
            ("substr", self.b_substr, True, False),
            ("syscmd", self.b_noop, True, False),
            ("sysval", self.b_sysval, False, False),
            ("traceoff", self.b_noop, False, False),
            ("traceon", self.b_noop, False, False),
            ("translit", self.b_translit, True, False),
            ("undefine", self.b_undefine, True, False),
            ("undivert", self.b_undivert, False, False),
        ]
        for name, func, blind, groks in tab:
            bi = Builtin(name, func, blind, groks)
            self.builtins[name] = bi
            self.symtab[name] = [Def(builtin=bi)]
        self.symtab["__gnu__"] = [Def(text="")]
        self.symtab["__unix__"] = [Def(text="")]

    def b_noop(self, argv, out):
        pass

    def b_sysval(self, argv, out):
        out.append("0")

    def b_file(self, argv, out):
        self.bad_argc(argv, 1, 1)
        out.append(self.lquote + self.cur_file + self.rquote)

    def b_line(self, argv, out):
        self.bad_argc(argv, 1, 1)
        out.append(str(self.cur_line))

    def b_program(self, argv, out):
        self.bad_argc(argv, 1, 1)
        out.append(self.lquote + PROGRAM_NAME + self.rquote)

    def _define(self, argv, push):
        if self.bad_argc(argv, 2, 3):
            return
        if not isinstance(argv[1], str):
            self.warn("Warning: %s: invalid macro name ignored" % argtext(argv[0]))
            return
        name = argv[1]
        if len(argv) == 2:
            self.define(name, Def(text=""), push)
            return
        v = argv[2]
        if isinstance(v, str):
            self.define(name, Def(text=v), push)
        else:
            self.define(name, Def(builtin=v), push)

    def b_define(self, argv, out):
        self._define(argv, False)

    def b_pushdef(self, argv, out):
        self._define(argv, True)

    def b_undefine(self, argv, out):
        if self.bad_argc(argv, 2, -1):
            return
        for a in argv[1:]:
            self.undefine(argtext(a))

    def b_popdef(self, argv, out):
        if self.bad_argc(argv, 2, -1):
            return
        for a in argv[1:]:
            self.popdef(argtext(a))

    def b_defn(self, argv, out):
        if self.bad_argc(argv, 2, -1):
            return
        for a in argv[1:]:
            name = argtext(a)
            d = self.lookup(name)
            if d is None:
                continue
            if d.builtin is None:
                out.append(self.lquote)
                out.append(d.text)
                out.append(self.rquote)
            elif len(argv) != 2:
                self.warn("Warning: cannot concatenate builtin `%s'" % name)
            else:
                self.push_macro(d.builtin)

    def b_indir(self, argv, out):
        if self.bad_argc(argv, 2, -1):
            return
        if not isinstance(argv[1], str):
            self.warn("Warning: indir: invalid macro name ignored")
            return
        name = argv[1]
        d = self.lookup(name)
        if d is None:
            self.warn("undefined macro `%s'" % name)
            return
        args = list(argv[1:])
        if not (d.builtin is not None and d.builtin.groks):
            for i in range(1, len(args)):
                if not isinstance(args[i], str):
                    args[i] = ""
        self.call_macro(d, args, out)

    def b_builtin(self, argv, out):
        if self.bad_argc(argv, 2, -1):
            return
        if not isinstance(argv[1], str):
            self.warn("Warning: builtin: invalid macro name ignored")
            return
        name = argv[1]
        bi = self.builtins.get(name)
        if bi is None:
            self.warn("undefined builtin `%s'" % name)
            return
        args = list(argv[1:])
        if not bi.groks:
            for i in range(1, len(args)):
                if not isinstance(args[i], str):
                    args[i] = ""
        bi.func(args, out)

    def b_ifdef(self, argv, out):
        if self.bad_argc(argv, 3, 4):
            return
        if self.lookup(argtext(argv[1])) is not None:
            out.append(argtext(argv[2]))
        elif len(argv) >= 4:
            out.append(argtext(argv[3]))

    def b_ifelse(self, argv, out):
        argc = len(argv)
        if argc == 2:
            return
        if self.bad_argc(argv, 4, -1):
            return
        if (argc + 2) % 3 > 1:
            self.warn("Warning: excess arguments to builtin `%s' ignored" % argtext(argv[0]))
        args = [argtext(a) for a in argv[1:]]
        i = 0
        n = len(args)
        while True:
            if args[i] == args[i + 1]:
                out.append(args[i + 2])
                return
            rem = n - i
            if rem == 3:
                return
            if rem == 4 or rem == 5:
                out.append(args[i + 3])
                return
            i += 3

    def b_shift(self, argv, out):
        if self.bad_argc(argv, 2, -1):
            return
        self.dump_args(out, argv[1:], ",", True)

    def b_changequote(self, argv, out):
        self.bad_argc(argv, 1, 3)
        lq = argtext(argv[1]) if len(argv) >= 2 else None
        rq = argtext(argv[2]) if len(argv) >= 3 else None
        if lq is None:
            lq, rq = "`", "'"
        elif rq is None or (lq and not rq):
            rq = "'"
        self.lquote = lq
        self.rquote = rq

    def b_changecom(self, argv, out):
        self.bad_argc(argv, 1, 3)
        bc = argtext(argv[1]) if len(argv) >= 2 else None
        ec = argtext(argv[2]) if len(argv) >= 3 else None
        if bc is None:
            bc = ec = ""
        elif ec is None or (bc and not ec):
            ec = "\n"
        self.bcomm = bc
        self.ecomm = ec

    def b_dnl(self, argv, out):
        self.bad_argc(argv, 1, 1)
        file, line = self.cur_file, self.cur_line
        while True:
            c = self.next_char()
            if c is EOF:
                self.stderr("%s:%s:%d: Warning: end of file treated as newline\n"
                            % (PROGRAM_NAME, file, line))
                break
            if c == "\n":
                break
        if file != self.cur_file or line != self.cur_line:
            self.input_change = True

    def b_m4wrap(self, argv, out):
        if self.bad_argc(argv, 2, -1):
            return
        o = []
        self.dump_args(o, argv, " ", False)
        self.push_wrapup("".join(o))

    def _include(self, argv, silent):
        if self.bad_argc(argv, 2, 2):
            return
        name = argtext(argv[1])
        text = self.read_file(name)
        if text is None:
            if not silent:
                self.warn("cannot open `%s': No such file or directory" % name)
                self.retcode = 1
            return
        self.push_file(text, name)

    def b_include(self, argv, out):
        self._include(argv, False)

    def b_sinclude(self, argv, out):
        self._include(argv, True)

    def b_divert(self, argv, out):
        if self.bad_argc(argv, 1, 2):
            return
        i = 0
        if len(argv) >= 2:
            i = self.numeric_arg(argv, argtext(argv[1]))
            if i is None:
                return
        self.make_diversion(i)

    def b_undivert(self, argv, out):
        if len(argv) == 1:
            self.undivert_all()
            return
        for a in argv[1:]:
            s = argtext(a)
            v, end, ovf = c_strtol(s)
            if end == len(s) and not (s and s[0] in C_SPACE):
                self.insert_diversion(to_i32(v))
            else:
                text = self.read_file(s)
                if text is None:
                    self.warn("cannot undivert `%s': No such file or directory" % s)
                elif text:
                    self.output(text)

    def b_divnum(self, argv, out):
        self.bad_argc(argv, 1, 1)
        out.append(str(self.cur_div))

    def b_len(self, argv, out):
        if self.bad_argc(argv, 2, 2):
            return
        out.append(str(len(argtext(argv[1]))))

    def b_index(self, argv, out):
        if self.bad_argc(argv, 3, 3):
            if len(argv) == 2:
                out.append("0")
            return
        out.append(str(argtext(argv[1]).find(argtext(argv[2]))))

    def b_substr(self, argv, out):
        if self.bad_argc(argv, 3, 4):
            if len(argv) == 2:
                out.append(argtext(argv[1]))
            return
        s = argtext(argv[1])
        avail = len(s)
        start = self.numeric_arg(argv, argtext(argv[2]))
        if start is None:
            return
        length = avail
        if len(argv) >= 4:
            length = self.numeric_arg(argv, argtext(argv[3]))
            if length is None:
                return
        if start < 0 or length <= 0 or start >= avail:
            return
        if start + length > avail:
            length = avail - start
        out.append(s[start:start + length])

    @staticmethod
    def expand_ranges(s):
        res = []
        frm = 0
        i = 0
        n = len(s)
        while i < n:
            c = s[i]
            if c == "-" and frm != 0:
                i += 1
                if i >= n:
                    res.append("-")
                    break
                to = ord(s[i])
                if frm <= to:
                    x = frm
                    while x < to:
                        x += 1
                        res.append(chr(x))
                else:
                    x = frm
                    while True:
                        x -= 1
                        if x < to:
                            break
                        res.append(chr(x))
                frm = to
                i += 1
            else:
                res.append(c)
                frm = ord(c)
                i += 1
        return "".join(res)

    def b_translit(self, argv, out):
        if self.bad_argc(argv, 3, 4) or not argtext(argv[2]):
            if len(argv) >= 2:
                out.append(argtext(argv[1]))
            return
        frm = argtext(argv[2])
        if "-" in frm:
            frm = self.expand_ranges(frm)
        to = argtext(argv[3]) if len(argv) >= 4 else ""
        if "-" in to:
            to = self.expand_ranges(to)
        mapping = {}
        ti = 0
        for ch in frm:
            if ch not in mapping:
                mapping[ch] = to[ti] if ti < len(to) else None
            if ti < len(to):
                ti += 1
        res = []
        for ch in argtext(argv[1]):
            if ch not in mapping:
                res.append(ch)
            else:
                r = mapping[ch]
                if r is not None:
                    res.append(r)
        out.append("".join(res))

    def _compile(self, pat, name):
        try:
            return compile_regex(pat)
        except RegexError as e:
            self.warn("bad regular expression: `%s': %s" % (pat, e))
            return None

    def substitute(self, out, victim, repl, st, en, caps):
        i = 0
        n = len(repl)
        nsub = len(caps) - 1
        while True:
            j = repl.find("\\", i)
            if j < 0:
                out.append(repl[i:])
                return
            out.append(repl[i:j])
            j += 1
            if j >= n:
                self.warn("Warning: trailing \\ ignored in replacement")
                return
            c = repl[j]
            if c == "0" or c == "&":
                out.append(victim[st:en])
            elif "1" <= c <= "9":
                k = ord(c) - 48
                if k > nsub:
                    self.warn("Warning: sub-expression %d not present" % k)
                else:
                    cp = caps[k]
                    if cp is not None:
                        out.append(victim[cp[0]:cp[1]])
            else:
                out.append(c)
            i = j + 1

    def b_regexp(self, argv, out):
        if self.bad_argc(argv, 3, 4):
            if len(argv) == 2:
                out.append("0")
            return
        victim = argtext(argv[1])
        rx = self._compile(argtext(argv[2]), "regexp")
        if rx is None:
            return
        m = rx.search(victim, 0)
        if len(argv) == 3:
            out.append(str(m[0]) if m else "-1")
        elif m:
            self.substitute(out, victim, argtext(argv[3]), m[0], m[1], m[2])

    def b_patsubst(self, argv, out):
        if self.bad_argc(argv, 3, 4):
            if len(argv) == 2:
                out.append(argtext(argv[1]))
            return
        victim = argtext(argv[1])
        pat = argtext(argv[2])
        if not pat and len(argv) == 3:
            out.append(victim)
            return
        rx = self._compile(pat, "patsubst")
        if rx is None:
            return
        repl = argtext(argv[3]) if len(argv) >= 4 else ""
        length = len(victim)
        offset = 0
        res = []
        while offset <= length:
            m = rx.search(victim, offset)
            if m is None:
                if offset < length:
                    res.append(victim[offset:])
                break
            st, en, caps = m
            if st > offset:
                res.append(victim[offset:st])
            self.substitute(res, victim, repl, st, en, caps)
            offset = en
            if st == en:
                if offset < length:
                    res.append(victim[offset])
                offset += 1
        out.append("".join(res))

    # format
    def _arg_int(self, s):
        if s == "":
            self.warn("empty string treated as 0")
            return 0
        v, end, ovf = c_strtol(s)
        if end != len(s):
            self.warn("non-numeric argument %s" % s)
        elif s[0] in C_SPACE:
            self.warn("leading whitespace ignored")
        elif ovf or to_i32(v) != v:
            self.warn("numeric overflow detected")
        return v

    def _arg_double(self, s):
        if s == "":
            self.warn("empty string treated as 0")
            return 0.0
        v, end = c_strtod(s)
        if end != len(s):
            self.warn("non-numeric argument %s" % s)
        elif s[0] in C_SPACE:
            self.warn("leading whitespace ignored")
        return v

    def b_format(self, argv, out):
        if self.bad_argc(argv, 2, -1):
            return
        args = [argtext(a) for a in argv[2:]]
        pos = [0]

        def next_str():
            if pos[0] >= len(args):
                return ""
            s = args[pos[0]]
            pos[0] += 1
            return s

        def next_int():
            if pos[0] >= len(args):
                return 0
            return self._arg_int(next_str())

        def next_double():
            if pos[0] >= len(args):
                return 0.0
            return self._arg_double(next_str())

        f = argtext(argv[1])
        n = len(f)
        i = 0
        res = []
        while True:
            j = f.find("%", i)
            if j < 0:
                res.append(f[i:])
                break
            res.append(f[i:j])
            i = j + 1
            if i < n and f[i] == "%":
                res.append("%")
                i += 1
                continue
            ok = set("aAcdeEfFgGiosuxX")
            flags = set()
            while i < n:
                c = f[i]
                if c == "'":
                    ok -= set("ceEsxX")
                elif c in "+ ":
                    ok -= set("cosuxX")
                elif c == "0":
                    ok -= set("cs")
                elif c == "#":
                    ok -= set("cdisu")
                elif c == "-":
                    pass
                else:
                    break
                flags.add(c)
                i += 1
            width = 0
            if i < n and f[i] == "*":
                width = to_i32(next_int())
                i += 1
            else:
                while i < n and "0" <= f[i] <= "9":
                    width = width * 10 + ord(f[i]) - 48
                    i += 1
            prec = -1
            if i < n and f[i] == ".":
                ok.discard("c")
                i += 1
                if i < n and f[i] == "*":
                    prec = to_i32(next_int())
                    i += 1
                else:
                    prec = 0
                    while i < n and "0" <= f[i] <= "9":
                        prec = prec * 10 + ord(f[i]) - 48
                        i += 1
            lflag = 0
            hflag = 0
            if i < n and f[i] == "l":
                lflag = 1
                i += 1
                ok -= set("cs")
            elif i < n and f[i] == "h":
                hflag = 1
                i += 1
                if i < n and f[i] == "h":
                    hflag = 2
                    i += 1
                ok -= set("aAceEfFgGs")
            c = f[i] if i < n else ""
            i += 1
            if c == "" or c not in ok:
                self.warn("Warning: unrecognized specifier in `%s'" % f)
                if c == "":
                    i -= 1
                continue
            if width < 0:
                flags.add("-")
                width = -width
            if prec < 0:
                prec = -1
            if c == "c":
                v = to_i32(next_int())
                ch = chr(v & 0xFF)
                s = ch
                if width > 1:
                    if "-" in flags:
                        s = ch + " " * (width - 1)
                    else:
                        s = " " * (width - 1) + ch
                k = s.find("\0")
                if k >= 0:
                    s = s[:k]
                res.append(s)
            elif c == "s":
                s = next_str()
                if prec >= 0:
                    s = s[:prec]
                if len(s) < width:
                    if "-" in flags:
                        s = s + " " * (width - len(s))
                    else:
                        s = " " * (width - len(s)) + s
                res.append(s)
            elif c in "diouxX":
                v = next_int()
                if lflag:
                    v = to_i64(v)
                    if c not in "di":
                        v &= 0xFFFFFFFFFFFFFFFF
                else:
                    v = to_i32(v)
                    if hflag == 2:
                        v = ((v + 128) & 0xFF) - 128 if c in "di" else v & 0xFF
                    elif hflag == 1:
                        v = ((v + 32768) & 0xFFFF) - 32768 if c in "di" else v & 0xFFFF
                    elif c not in "di":
                        v &= 0xFFFFFFFF
                res.append(format_int(v, "d" if c == "i" else c, flags, width, prec))
            else:
                v = next_double()
                res.append(format_float(v, c, flags, width, prec))
        out.append("".join(res))

    def b_incr(self, argv, out):
        if self.bad_argc(argv, 2, 2):
            return
        v = self.numeric_arg(argv, argtext(argv[1]))
        if v is None:
            return
        out.append(str(to_i32(v + 1)))

    def b_decr(self, argv, out):
        if self.bad_argc(argv, 2, 2):
            return
        v = self.numeric_arg(argv, argtext(argv[1]))
        if v is None:
            return
        out.append(str(to_i32(v - 1)))

    def b_eval(self, argv, out):
        if self.bad_argc(argv, 2, 4):
            return
        name = argtext(argv[0])
        radix = 10
        a2 = argtext(argv[2]) if len(argv) > 2 else ""
        if a2:
            radix = self.numeric_arg(argv, a2)
            if radix is None:
                return
        if radix < 1 or radix > 36:
            self.warn("radix %d in builtin `%s' out of range" % (radix, name))
            return
        mn = 1
        if len(argv) >= 4:
            mn = self.numeric_arg(argv, argtext(argv[3]))
            if mn is None:
                return
        if mn < 0:
            self.warn("negative width to builtin `%s'" % name)
            return
        expr = argtext(argv[1])
        value = 0
        if not expr:
            self.warn("empty string treated as 0 in builtin `%s'" % name)
        else:
            ev = Evaluator(expr, self.warn)
            er, value = ev.evaluate()
            if er != E_NO_ERROR:
                self.warn(EVAL_MESSAGES[er] % expr)
                return
        if radix == 1:
            res = []
            if value < 0:
                res.append("-")
                value = -value
                if value >= 1 << 31:
                    value = 1 << 31
            if mn - value > 0:
                res.append("0" * (mn - value))
            res.append("1" * value)
            out.append("".join(res))
            return
        s = ntoa(value, radix)
        if s.startswith("-"):
            out.append("-")
            s = s[1:]
        if mn - len(s) > 0:
            out.append("0" * (mn - len(s)))
        out.append(s)

    def b_errprint(self, argv, out):
        if self.bad_argc(argv, 2, -1):
            return
        o = []
        self.dump_args(o, argv, " ", False)
        self.stderr("".join(o))

    def b_dumpdef(self, argv, out):
        names = [argtext(a) for a in argv[1:]] if len(argv) > 1 else sorted(self.symtab)
        for name in sorted(set(names)):
            d = self.lookup(name)
            if d is None:
                if len(argv) > 1:
                    self.warn("undefined macro `%s'" % name)
                continue
            if d.builtin is not None:
                self.stderr("%s:\t<%s>\n" % (name, d.builtin.name))
            else:
                self.stderr("%s:\t%s%s%s\n" % (name, self.lquote, d.text, self.rquote))

    def b_m4exit(self, argv, out):
        self.bad_argc(argv, 1, 2)
        code = 0
        if len(argv) >= 2:
            v = self.numeric_arg(argv, argtext(argv[1]))
            if v is None:
                code = 1
            else:
                code = v
        if code < 0 or code > 255:
            self.warn("exit status out of range: `%d'" % code)
            code = 1
        raise M4Exit(code)

    # -- driver ----------------------------------------------------------
    def process_file(self, name):
        if name == "-":
            try:
                data = sys.stdin.buffer.read()
            except Exception:
                data = b""
            self.push_file(data.decode("latin-1"), "stdin")
        else:
            text = self.read_file(name)
            if text is None:
                self.stderr("%s: cannot open `%s': No such file or directory\n"
                            % (PROGRAM_NAME, name))
                self.retcode = 1
                return
            self.push_file(text, name)
        self.expand_input()

    def run(self, files):
        try:
            if not files:
                files = ["-"]
            for f in files:
                self.process_file(f)
            while self.pop_wrapup():
                self.expand_input()
            self.make_diversion(0)
            self.undivert_all()
            code = self.retcode
        except M4Exit as e:
            code = e.code
        except Fatal:
            code = 1
        self.flush_stdout()
        return code


def main(argv):
    files = list(argv)
    if files and files[0] == "--":
        files = files[1:]
    result = [1]

    def worker():
        m = M4()
        try:
            result[0] = m.run(files)
        except RecursionError:
            m.flush_stdout()
            m.stderr("%s: recursion limit exceeded\n" % PROGRAM_NAME)
            result[0] = 1

    sys.setrecursionlimit(1000000)
    try:
        threading.stack_size(1024 * 1024 * 1024)
    except (ValueError, RuntimeError):
        try:
            threading.stack_size(256 * 1024 * 1024)
        except (ValueError, RuntimeError):
            pass
    t = threading.Thread(target=worker)
    t.start()
    t.join()
    return result[0]


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
