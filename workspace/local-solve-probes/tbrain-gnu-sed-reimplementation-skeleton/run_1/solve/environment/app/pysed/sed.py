"""pysed: a GNU sed 4.9 replacement in pure Python.

Usage: python3 /app/pysed/sed.py [OPTION]... {script-only-if-no-other-script} [input-file]...
"""

import os
import re
import sys


class SedError(Exception):
    def __init__(self, msg, status=1):
        Exception.__init__(self, msg)
        self.status = status


# ---------------------------------------------------------------------------
# Character classes (C locale, bytes decoded as latin-1)
# ---------------------------------------------------------------------------

ALL = frozenset(chr(i) for i in range(256))


def _cls(pred):
    return frozenset(chr(i) for i in range(256) if pred(i))


CLASSES = {
    'alpha': _cls(lambda o: 65 <= o <= 90 or 97 <= o <= 122),
    'digit': _cls(lambda o: 48 <= o <= 57),
    'alnum': _cls(lambda o: 65 <= o <= 90 or 97 <= o <= 122 or 48 <= o <= 57),
    'upper': _cls(lambda o: 65 <= o <= 90),
    'lower': _cls(lambda o: 97 <= o <= 122),
    'space': _cls(lambda o: 9 <= o <= 13 or o == 32),
    'blank': _cls(lambda o: o == 9 or o == 32),
    'punct': _cls(lambda o: 33 <= o <= 47 or 58 <= o <= 64 or 91 <= o <= 96
                  or 123 <= o <= 126),
    'print': _cls(lambda o: 32 <= o <= 126),
    'graph': _cls(lambda o: 33 <= o <= 126),
    'cntrl': _cls(lambda o: o < 32 or o == 127),
    'xdigit': _cls(lambda o: 48 <= o <= 57 or 65 <= o <= 70 or 97 <= o <= 102),
}
WORD = CLASSES['alnum'] | frozenset('_')
SPACE = CLASSES['space']

_UP = {chr(i): chr(i - 32) for i in range(97, 123)}
_LO = {chr(i): chr(i + 32) for i in range(65, 91)}
UPPER_TBL = str.maketrans(_UP)
LOWER_TBL = str.maketrans(_LO)


def a_upper(s):
    return s.translate(UPPER_TBL)


def a_lower(s):
    return s.translate(LOWER_TBL)


def case_variants(chars):
    out = set(chars)
    for c in chars:
        if c in _UP:
            out.add(_UP[c])
        elif c in _LO:
            out.add(_LO[c])
    return out


# ---------------------------------------------------------------------------
# Escape processing shared by regex / replacement / text
# ---------------------------------------------------------------------------

SIMPLE_ESC = {'a': '\a', 'f': '\f', 'n': '\n', 'r': '\r', 't': '\t', 'v': '\v'}


def parse_numeric_escape(s, i):
    """s[i] is one of d/o/x/c (the char after the backslash).

    Returns (char, new_index) or None if not a valid numeric escape."""
    kind = s[i]
    if kind == 'c':
        if i + 1 < len(s):
            x = s[i + 1]
            return chr(ord(a_upper(x)) ^ 0x40), i + 2
        return None
    if kind == 'd':
        digits, base, maxlen = '0123456789', 10, 3
    elif kind == 'o':
        digits, base, maxlen = '01234567', 8, 3
    else:
        digits, base, maxlen = '0123456789abcdefABCDEF', 16, 2
    j = i + 1
    while j < len(s) and j - (i + 1) < maxlen and s[j] in digits:
        j += 1
    if j == i + 1:
        return None
    val = int(s[i + 1:j], base) & 0xFF
    return chr(val), j


def convert_regex_escapes(p):
    """GNU sed converts \\t, \\xHH, ... before the regex compiler sees them."""
    out = []
    i = 0
    n = len(p)
    while i < n:
        c = p[i]
        if c == '\\' and i + 1 < n:
            d = p[i + 1]
            if d in 'afrtv':
                out.append(SIMPLE_ESC[d])
                i += 2
                continue
            if d in 'doxc':
                r = parse_numeric_escape(p, i + 1)
                if r is not None:
                    ch, i = r
                    if ch == '\\':
                        out.append('\\\\')
                    else:
                        out.append(ch)
                    continue
            out.append(c)
            out.append(d)
            i += 2
            continue
        out.append(c)
        i += 1
    return ''.join(out)


def process_text_escapes(raw):
    """Escape processing for a/i/c text."""
    out = []
    i = 0
    n = len(raw)
    while i < n:
        c = raw[i]
        if c == '\\' and i + 1 < n:
            d = raw[i + 1]
            if d in SIMPLE_ESC:
                out.append(SIMPLE_ESC[d])
                i += 2
                continue
            if d in 'doxc':
                r = parse_numeric_escape(raw, i + 1)
                if r is not None:
                    ch, i = r
                    out.append(ch)
                    continue
            out.append(d)
            i += 2
            continue
        if c == '\\':
            i += 1
            continue
        out.append(c)
        i += 1
    return ''.join(out)


# ---------------------------------------------------------------------------
# Regular expressions: parser -> AST -> (python re, backtracking VM)
# ---------------------------------------------------------------------------

# AST nodes are tuples:
#   ('set', frozenset)     ('cat', [nodes])   ('alt', [nodes])
#   ('grp', idx, node)     ('rep', node, min, max|None)
#   ('bref', idx)          ('bol',) ('eol',) ('bos',) ('eos',)
#   ('wb',) ('nwb',) ('ws',) ('we',)

ASSERTS = ('bol', 'eol', 'bos', 'eos', 'wb', 'nwb', 'ws', 'we')


class RegexParser(object):
    def __init__(self, pattern, ere, icase, mline):
        self.p = pattern
        self.n = len(pattern)
        self.i = 0
        self.ere = ere
        self.icase = icase
        self.mline = mline
        self.ngroups = 0
        self.has_bref = False
        self.depth = 0

    # -- helpers --
    def lit(self, c):
        if self.icase:
            return ('set', frozenset(case_variants([c])))
        return ('set', frozenset([c]))

    def any_set(self):
        if self.mline:
            return ('set', ALL - frozenset('\n'))
        return ('set', ALL)

    def neg_set(self, chars):
        s = ALL - frozenset(chars)
        if self.mline:
            s = s - frozenset('\n')
        return ('set', s)

    def at_alt(self):
        if self.ere:
            return self.p[self.i] == '|'
        return self.p.startswith('\\|', self.i)

    def at_close(self):
        if self.depth == 0:
            return False
        if self.ere:
            return self.p[self.i] == ')'
        return self.p.startswith('\\)', self.i)

    # -- grammar --
    def parse(self):
        node = self.parse_alt()
        if self.i < self.n:
            raise SedError('unmatched ( or \\(')
        return node

    def parse_alt(self):
        branches = [self.parse_branch()]
        while self.i < self.n and self.at_alt():
            self.i += 1 if self.ere else 2
            branches.append(self.parse_branch())
        if len(branches) == 1:
            return branches[0]
        return ('alt', branches)

    def parse_branch(self):
        items = []
        p = self.p
        while self.i < self.n:
            if self.at_alt() or self.at_close():
                break
            c = p[self.i]
            # anchors
            if c == '^' and (self.ere or not items):
                items.append(('bol',))
                self.i += 1
                continue
            if c == '$':
                if self.ere:
                    items.append(('eol',))
                    self.i += 1
                    continue
                j = self.i + 1
                if (j == self.n or p.startswith('\\)', j)
                        or p.startswith('\\|', j)):
                    items.append(('eol',))
                    self.i += 1
                    continue
            atom = self.parse_atom(items)
            if atom[0] in ASSERTS:
                items.append(atom)
                continue
            # quantifiers
            while self.i < self.n:
                q = self.parse_quant()
                if q is None:
                    break
                mn, mx = q
                atom = ('rep', atom, mn, mx)
            items.append(atom)
        if len(items) == 1:
            return items[0]
        return ('cat', items)

    def parse_quant(self):
        p = self.p
        i = self.i
        c = p[i]
        if self.ere:
            if c == '*':
                self.i += 1
                return (0, None)
            if c == '+':
                self.i += 1
                return (1, None)
            if c == '?':
                self.i += 1
                return (0, 1)
            if c == '{':
                r = self.parse_interval(i + 1, '}')
                if r is not None:
                    return r
            return None
        if c == '*':
            self.i += 1
            return (0, None)
        if c == '\\' and i + 1 < self.n:
            d = p[i + 1]
            if d == '+':
                self.i += 2
                return (1, None)
            if d == '?':
                self.i += 2
                return (0, 1)
            if d == '{':
                r = self.parse_interval(i + 2, '\\}')
                if r is not None:
                    return r
                raise SedError('Invalid preceding regular expression')
        return None

    def parse_interval(self, j, close):
        p = self.p
        k = j
        while k < self.n and p[k].isdigit():
            k += 1
        mn_s = p[j:k]
        mx = None
        if k < self.n and p[k] == ',':
            k2 = k + 1
            while k2 < self.n and p[k2].isdigit():
                k2 += 1
            mx_s = p[k + 1:k2]
            k = k2
            if mx_s:
                mx = int(mx_s)
            else:
                mx = None
            if not mn_s:
                if not self.ere and not mx_s:
                    pass
                mn = 0
            else:
                mn = int(mn_s)
        else:
            if not mn_s:
                return None
            mn = int(mn_s)
            mx = mn
        if not p.startswith(close, k):
            return None
        if mx is not None and mx < mn:
            raise SedError('Invalid range end')
        self.i = k + len(close)
        return (mn, mx)

    def parse_group(self):
        self.ngroups += 1
        idx = self.ngroups
        self.depth += 1
        inner = self.parse_alt()
        self.depth -= 1
        if self.ere:
            if self.i < self.n and self.p[self.i] == ')':
                self.i += 1
            else:
                raise SedError('Unmatched ( or \\(')
        else:
            if self.p.startswith('\\)', self.i):
                self.i += 2
            else:
                raise SedError('Unmatched ( or \\(')
        return ('grp', idx, inner)

    def parse_atom(self, items):
        p = self.p
        c = p[self.i]
        if c == '.':
            self.i += 1
            return self.any_set()
        if c == '[':
            self.i += 1
            return self.parse_bracket()
        if self.ere:
            if c == '(':
                self.i += 1
                return self.parse_group()
        if c == '\\':
            if self.i + 1 >= self.n:
                raise SedError('Trailing backslash')
            d = p[self.i + 1]
            self.i += 2
            if not self.ere and d == '(':
                return self.parse_group()
            if d in '123456789':
                idx = int(d)
                if idx > self.ngroups:
                    raise SedError('Invalid back reference')
                self.has_bref = True
                return ('bref', idx)
            if d == 'w':
                return ('set', WORD)
            if d == 'W':
                return self.neg_set(WORD)
            if d == 's':
                return ('set', SPACE)
            if d == 'S':
                return self.neg_set(SPACE)
            if d == 'b':
                return ('wb',)
            if d == 'B':
                return ('nwb',)
            if d == '<':
                return ('ws',)
            if d == '>':
                return ('we',)
            if d == '`':
                return ('bos',)
            if d == "'":
                return ('eos',)
            if d == 'n':
                return self.lit('\n')
            return self.lit(d)
        self.i += 1
        return self.lit(c)

    def parse_bracket(self):
        p = self.p
        n = self.n
        neg = False
        if self.i < n and p[self.i] == '^':
            neg = True
            self.i += 1
        chars = set()
        first = True
        while True:
            if self.i >= n:
                raise SedError('unterminated address regex')
            c = p[self.i]
            if c == ']' and not first:
                self.i += 1
                break
            first = False
            lo = None
            if c == '[' and self.i + 1 < n and p[self.i + 1] in ':=.':
                kind = p[self.i + 1]
                end = p.find(kind + ']', self.i + 2)
                if end < 0:
                    raise SedError('unterminated address regex')
                name = p[self.i + 2:end]
                self.i = end + 2
                if kind == ':':
                    if name not in CLASSES:
                        raise SedError('Invalid character class name')
                    chars |= CLASSES[name]
                    continue
                if len(name) != 1:
                    raise SedError('Invalid collation character')
                lo = name
            else:
                lo = c
                self.i += 1
            # range?
            if (self.i + 1 < n and p[self.i] == '-' and p[self.i + 1] != ']'):
                self.i += 1
                c2 = p[self.i]
                if c2 == '[' and self.i + 1 < n and p[self.i + 1] in '=.':
                    kind = p[self.i + 1]
                    end = p.find(kind + ']', self.i + 2)
                    if end < 0:
                        raise SedError('unterminated address regex')
                    hi = p[self.i + 2:end]
                    self.i = end + 2
                    if len(hi) != 1:
                        raise SedError('Invalid collation character')
                else:
                    hi = c2
                    self.i += 1
                if ord(hi) < ord(lo):
                    raise SedError('Invalid range end')
                for o in range(ord(lo), ord(hi) + 1):
                    chars.add(chr(o))
            else:
                chars.add(lo)
        if self.icase:
            chars = case_variants(chars)
        if neg:
            return self.neg_set(chars)
        return ('set', frozenset(chars))


# VM opcodes
OP_CHAR, OP_SPLIT, OP_JMP, OP_SAVE, OP_ASSERT, OP_BREF, OP_MATCH, OP_MARK, \
    OP_CHECK = range(9)


def _set_to_py(s):
    if not s:
        return '(?!)'
    codes = sorted(ord(c) for c in s)
    if len(codes) == 1:
        return '\\x%02x' % codes[0]
    if len(codes) == 256:
        return '[\\x00-\\xff]'
    parts = []
    start = prev = codes[0]
    for o in codes[1:]:
        if o == prev + 1:
            prev = o
            continue
        parts.append((start, prev))
        start = prev = o
    parts.append((start, prev))
    out = []
    for a, b in parts:
        if a == b:
            out.append('\\x%02x' % a)
        elif b == a + 1:
            out.append('\\x%02x\\x%02x' % (a, b))
        else:
            out.append('\\x%02x-\\x%02x' % (a, b))
    return '[' + ''.join(out) + ']'


def _nullable(node):
    t = node[0]
    if t == 'set':
        return False
    if t in ASSERTS:
        return True
    if t == 'cat':
        return all(_nullable(x) for x in node[1])
    if t == 'alt':
        return any(_nullable(x) for x in node[1])
    if t == 'grp':
        return _nullable(node[2])
    if t == 'rep':
        return node[2] == 0 or _nullable(node[1])
    if t == 'bref':
        return True
    return True


def _has_unbounded_rep(node):
    t = node[0]
    if t == 'rep':
        return node[3] is None or _has_unbounded_rep(node[1])
    if t in ('cat', 'alt'):
        return any(_has_unbounded_rep(x) for x in node[1])
    if t == 'grp':
        return _has_unbounded_rep(node[2])
    return False


def _risky(node):
    """Nested unbounded repetition of a nullable body (exponential in re)."""
    t = node[0]
    if t == 'rep':
        inner = node[1]
        if node[3] is None and _has_unbounded_rep(inner) and _nullable(inner):
            return True
        return _risky(inner)
    if t in ('cat', 'alt'):
        return any(_risky(x) for x in node[1])
    if t == 'grp':
        return _risky(node[2])
    return False


def _has_group(node):
    t = node[0]
    if t == 'grp':
        return True
    if t in ('cat', 'alt'):
        return any(_has_group(x) for x in node[1])
    if t == 'rep':
        return _has_group(node[1])
    return False


def _empty_group_iter(node):
    """Is there an optional repetition of a nullable body holding a group?"""
    t = node[0]
    if t == 'rep':
        inner = node[1]
        if (node[3] is None or node[3] > node[2]) and _nullable(inner) \
                and _has_group(inner):
            return True
        return _empty_group_iter(inner)
    if t in ('cat', 'alt'):
        return any(_empty_group_iter(x) for x in node[1])
    if t == 'grp':
        return _empty_group_iter(node[2])
    return False


def _fixed(node):
    t = node[0]
    if t == 'set' or t in ASSERTS:
        return True
    if t == 'cat':
        return all(_fixed(x) for x in node[1])
    if t == 'grp':
        return _fixed(node[2])
    if t == 'rep':
        return node[2] == node[3] and _fixed(node[1])
    return False


class Regex(object):
    STEP_LIMIT = 400000

    def __init__(self, pattern, ere, icase=False, mline=False):
        self.source = pattern
        self.icase = icase
        self.mline = mline
        parser = RegexParser(convert_regex_escapes(pattern), ere, icase, mline)
        ast = parser.parse()
        self.ast = ast
        self.ngroups = parser.ngroups
        self.has_bref = parser.has_bref
        self.fixed = _fixed(ast) and not self.has_bref
        self.py_caps_ok = not _empty_group_iter(ast)
        # compile VM
        self.ops = []
        self.A = []
        self.B = []
        self.nloops = 0
        self._emit(ast)
        self._add(OP_MATCH)
        self.nslots = 2 * (self.ngroups + 1) + self.nloops
        # compile python regex
        self.py = None
        if not _risky(ast):
            try:
                flags = re.ASCII
                if icase:
                    flags |= re.IGNORECASE
                self.py = re.compile(self._to_py(ast), flags)
            except (re.error, RecursionError, OverflowError):
                self.py = None

    # ---- python translation ----
    def _to_py(self, node):
        t = node[0]
        if t == 'set':
            return _set_to_py(node[1])
        if t == 'cat':
            return ''.join(self._to_py(x) for x in node[1])
        if t == 'alt':
            return '(?:' + '|'.join(self._to_py(x) for x in node[1]) + ')'
        if t == 'grp':
            return '(' + self._to_py(node[2]) + ')'
        if t == 'rep':
            inner = '(?:' + self._to_py(node[1]) + ')'
            mn, mx = node[2], node[3]
            if mx is None:
                if mn == 0:
                    return inner + '*'
                if mn == 1:
                    return inner + '+'
                return inner + '{%d,}' % mn
            if mn == 0 and mx == 1:
                return inner + '?'
            if mn == mx:
                return inner + '{%d}' % mn
            return inner + '{%d,%d}' % (mn, mx)
        if t == 'bref':
            return '(?:\\%d)' % node[1]
        if t == 'bol':
            return '(?<![^\\n])' if self.mline else '\\A'
        if t == 'eol':
            return '(?![^\\n])' if self.mline else '\\Z'
        if t == 'bos':
            return '\\A'
        if t == 'eos':
            return '\\Z'
        if t == 'wb':
            return '(?:(?<=\\w)(?!\\w)|(?<!\\w)(?=\\w))'
        if t == 'nwb':
            return '(?:(?<=\\w)(?=\\w)|(?<!\\w)(?!\\w))'
        if t == 'ws':
            return '(?<!\\w)(?=\\w)'
        if t == 'we':
            return '(?<=\\w)(?!\\w)'
        raise SedError('internal regex error')

    # ---- VM compilation ----
    def _add(self, op, a=None, b=None):
        self.ops.append(op)
        self.A.append(a)
        self.B.append(b)
        return len(self.ops) - 1

    def _emit(self, node):
        t = node[0]
        if t == 'set':
            self._add(OP_CHAR, node[1])
        elif t == 'cat':
            for x in node[1]:
                self._emit(x)
        elif t == 'alt':
            branches = node[1]
            jumps = []
            for k, br in enumerate(branches):
                if k < len(branches) - 1:
                    sp = self._add(OP_SPLIT)
                    self._emit(br)
                    jumps.append(self._add(OP_JMP))
                    self.A[sp] = sp + 1
                    self.B[sp] = len(self.ops)
                else:
                    self._emit(br)
            end = len(self.ops)
            for j in jumps:
                self.A[j] = end
        elif t == 'grp':
            idx = node[1]
            self._add(OP_SAVE, 2 * idx)
            self._emit(node[2])
            self._add(OP_SAVE, 2 * idx + 1)
        elif t == 'rep':
            inner, mn, mx = node[1], node[2], node[3]
            for _ in range(mn):
                self._emit(inner)
            if mx is None:
                slot = 2 * (self.ngroups + 1) + self.nloops
                self.nloops += 1
                loop = self._add(OP_SPLIT)
                self._add(OP_MARK, slot)
                self._emit(inner)
                self._add(OP_CHECK, slot)
                self._add(OP_JMP, loop)
                self.A[loop] = loop + 1
                self.B[loop] = len(self.ops)
            else:
                splits = []
                slot = None
                if mx > mn:
                    slot = 2 * (self.ngroups + 1) + self.nloops
                    self.nloops += 1
                for _ in range(mx - mn):
                    sp = self._add(OP_SPLIT)
                    self.A[sp] = sp + 1
                    splits.append(sp)
                    self._add(OP_MARK, slot)
                    self._emit(inner)
                    self._add(OP_CHECK, slot)
                end = len(self.ops)
                for sp in splits:
                    self.B[sp] = end
        elif t == 'bref':
            self._add(OP_BREF, node[1])
        else:
            self._add(OP_ASSERT, t)

    # ---- VM execution ----
    def _assert(self, kind, s, pos, n):
        if kind == 'bol':
            return pos == 0 or (self.mline and s[pos - 1] == '\n')
        if kind == 'eol':
            return pos == n or (self.mline and s[pos] == '\n')
        if kind == 'bos':
            return pos == 0
        if kind == 'eos':
            return pos == n
        pw = pos > 0 and s[pos - 1] in WORD
        nw = pos < n and s[pos] in WORD
        if kind == 'wb':
            return pw != nw
        if kind == 'nwb':
            return pw == nw
        if kind == 'ws':
            return (not pw) and nw
        if kind == 'we':
            return pw and not nw
        return False

    def _max_end(self, s, st):
        ops, A, B = self.ops, self.A, self.B
        n = len(s)
        n1 = n + 1
        best = -1
        visited = set()
        stack = [(0, st)]
        while stack:
            pc, pos = stack.pop()
            while True:
                key = pc * n1 + pos
                if key in visited:
                    break
                visited.add(key)
                op = ops[pc]
                if op == OP_CHAR:
                    if pos < n and s[pos] in A[pc]:
                        pc += 1
                        pos += 1
                        continue
                    break
                elif op == OP_SPLIT:
                    stack.append((B[pc], pos))
                    pc = A[pc]
                elif op == OP_JMP:
                    pc = A[pc]
                elif op == OP_ASSERT:
                    if self._assert(A[pc], s, pos, n):
                        pc += 1
                    else:
                        break
                elif op == OP_MATCH:
                    if pos > best:
                        best = pos
                        if best == n:
                            return best
                    break
                else:
                    pc += 1
        return best

    def _find(self, s, st, target):
        ops, A, B = self.ops, self.A, self.B
        n = len(s)
        n1 = n + 1
        mbase = 2 * (self.ngroups + 1)
        loops = self.nloops > 0
        visited = set()
        stack = [(0, st, (-1,) * self.nslots)]
        while stack:
            pc, pos, caps = stack.pop()
            while True:
                if loops:
                    key = (pc * n1 + pos, caps[mbase:])
                else:
                    key = pc * n1 + pos
                if key in visited:
                    break
                visited.add(key)
                op = ops[pc]
                if op == OP_CHAR:
                    if pos < n and s[pos] in A[pc]:
                        pc += 1
                        pos += 1
                        continue
                    break
                elif op == OP_SPLIT:
                    stack.append((B[pc], pos, caps))
                    pc = A[pc]
                elif op == OP_JMP:
                    pc = A[pc]
                elif op == OP_SAVE or op == OP_MARK:
                    k = A[pc]
                    caps = caps[:k] + (pos,) + caps[k + 1:]
                    pc += 1
                elif op == OP_CHECK:
                    if caps[A[pc]] == pos:
                        break
                    pc += 1
                elif op == OP_ASSERT:
                    if self._assert(A[pc], s, pos, n):
                        pc += 1
                    else:
                        break
                elif op == OP_MATCH:
                    if pos == target:
                        return caps
                    break
                else:
                    pc += 1
        return None

    def _bref_search(self, s, st):
        """Exhaustive backtracking (for patterns with back-references).

        Returns (end, caps), (-1, None) for no match, or None if the step
        budget was exhausted."""
        ops, A, B = self.ops, self.A, self.B
        n = len(s)
        icase = self.icase
        best_end = -1
        best_caps = None
        steps = 0
        limit = self.STEP_LIMIT
        stack = [(0, st, (-1,) * self.nslots)]
        while stack:
            pc, pos, caps = stack.pop()
            while True:
                steps += 1
                if steps > limit:
                    return None
                op = ops[pc]
                if op == OP_CHAR:
                    if pos < n and s[pos] in A[pc]:
                        pc += 1
                        pos += 1
                        continue
                    break
                elif op == OP_SPLIT:
                    stack.append((B[pc], pos, caps))
                    pc = A[pc]
                elif op == OP_JMP:
                    pc = A[pc]
                elif op == OP_SAVE or op == OP_MARK:
                    k = A[pc]
                    caps = caps[:k] + (pos,) + caps[k + 1:]
                    pc += 1
                elif op == OP_CHECK:
                    if caps[A[pc]] == pos:
                        break
                    pc += 1
                elif op == OP_ASSERT:
                    if self._assert(A[pc], s, pos, n):
                        pc += 1
                    else:
                        break
                elif op == OP_BREF:
                    g = A[pc]
                    gs, ge = caps[2 * g], caps[2 * g + 1]
                    if gs < 0 or ge < 0:
                        break
                    ln = ge - gs
                    if pos + ln > n:
                        break
                    sub = s[gs:ge]
                    cand = s[pos:pos + ln]
                    if icase:
                        ok = a_lower(sub) == a_lower(cand)
                    else:
                        ok = sub == cand
                    if not ok:
                        break
                    pos += ln
                    pc += 1
                elif op == OP_MATCH:
                    if pos > best_end:
                        best_end = pos
                        best_caps = caps
                        if pos == n:
                            return best_end, best_caps
                    break
        return best_end, best_caps

    def _groups_from_caps(self, caps):
        res = []
        for g in range(1, self.ngroups + 1):
            a, b = caps[2 * g], caps[2 * g + 1]
            if a < 0 or b < 0 or b < a:
                res.append(None)
            else:
                res.append((a, b))
        return res

    @staticmethod
    def _groups_from_py(m, ng):
        res = []
        for g in range(1, ng + 1):
            a, b = m.span(g)
            if a < 0:
                res.append(None)
            else:
                res.append((a, b))
        return res

    def _vm_at(self, s, st):
        """Longest match starting exactly at st: (end, groups) or None."""
        if self.has_bref:
            r = self._bref_search(s, st)
            if r is None:
                return 'budget'
            end, caps = r
            if end < 0:
                return None
            return end, self._groups_from_caps(caps)
        end = self._max_end(s, st)
        if end < 0:
            return None
        caps = self._find(s, st, end)
        if caps is None:
            return None
        return end, self._groups_from_caps(caps)

    def search(self, s, pos=0):
        """Leftmost-longest search. Returns (start, end, groups) or None."""
        n = len(s)
        if pos > n:
            return None
        py = self.py
        if py is not None:
            m = py.search(s, pos)
            if m is None:
                return None
            st, en = m.span()
            if self.fixed or (en == n and self.py_caps_ok):
                return st, en, self._groups_from_py(m, self.ngroups)
            if not self.has_bref:
                end = self._max_end(s, st)
                if end < en:
                    return st, en, self._groups_from_py(m, self.ngroups)
                if end == en and self.py_caps_ok:
                    return st, en, self._groups_from_py(m, self.ngroups)
                caps = self._find(s, st, end)
                if caps is None:
                    return st, en, self._groups_from_py(m, self.ngroups)
                return st, end, self._groups_from_caps(caps)
            r = self._vm_at(s, st)
            if r is not None and r != 'budget' and not self.py_caps_ok \
                    and r[0] >= en:
                return st, r[0], r[1]
            if r is None or r == 'budget' or r[0] <= en:
                return st, en, self._groups_from_py(m, self.ngroups)
            return st, r[0], r[1]
        for st in range(pos, n + 1):
            r = self._vm_at(s, st)
            if r is None:
                continue
            if r == 'budget':
                continue
            return st, r[0], r[1]
        return None


# ---------------------------------------------------------------------------
# Script parsing
# ---------------------------------------------------------------------------

class Addr(object):
    __slots__ = ('kind', 'n', 'step', 'regex')

    def __init__(self, kind, n=0, step=0, regex=None):
        self.kind = kind      # num step last re plus tilde zero
        self.n = n
        self.step = step
        self.regex = regex


class Cmd(object):
    __slots__ = ('name', 'a1', 'a2', 'neg', 'state', 'end', 'text', 'label',
                 'target', 'num', 'regex', 'repl', 'gflag', 'pflag', 'nth',
                 'table', 'block_end')

    def __init__(self, name):
        self.name = name
        self.a1 = None
        self.a2 = None
        self.neg = False
        self.state = 0      # 0 inactive, 1 active
        self.end = 0
        self.text = None
        self.label = None
        self.target = None
        self.num = None
        self.regex = None
        self.repl = None
        self.gflag = False
        self.pflag = False
        self.nth = 1
        self.table = None
        self.block_end = None


class ScriptParser(object):
    def __init__(self, text, ere):
        self.t = text
        self.i = 0
        self.n = len(text)
        self.ere = ere
        self.cmds = []
        self.labels = {}

    def peek(self):
        if self.i < self.n:
            return self.t[self.i]
        return ''

    def getc(self):
        if self.i < self.n:
            c = self.t[self.i]
            self.i += 1
            return c
        self.i += 1
        return ''

    def skip_blanks(self):
        while self.i < self.n and self.t[self.i] in ' \t':
            self.i += 1

    def skip_ws(self):
        while self.i < self.n and self.t[self.i] in ' \t\n\r\v\f':
            self.i += 1

    def read_number(self):
        j = self.i
        while self.i < self.n and self.t[self.i].isdigit():
            self.i += 1
        return int(self.t[j:self.i])

    def err(self, msg):
        raise SedError('-e expression #1, char %d: %s' % (self.i, msg))

    def match_slash(self, delim, regex):
        buf = []
        while True:
            c = self.getc()
            if c == '':
                return None
            if c == '\\':
                c2 = self.getc()
                if c2 == '':
                    return None
                if c2 == delim:
                    if not regex and c2 == '&':
                        buf.append('\\')
                    buf.append(c2)
                elif c2 == 'n' and regex:
                    buf.append('\n')
                elif c2 == '\n':
                    buf.append('\n')
                else:
                    buf.append('\\')
                    buf.append(c2)
            elif c == delim:
                return ''.join(buf)
            else:
                buf.append(c)

    def compile_regex(self, pat, icase, mline):
        if pat == '':
            return None     # use last regex
        try:
            return Regex(pat, self.ere, icase, mline)
        except SedError:
            raise
        except RecursionError:
            raise SedError('regular expression too big')

    def parse_addr(self):
        c = self.peek()
        if c.isdigit() and c != '':
            num = self.read_number()
            if self.peek() == '~':
                self.i += 1
                step = self.read_number() if self.peek().isdigit() else 0
                return Addr('step', num, step)
            return Addr('num', num)
        if c == '$':
            self.i += 1
            return Addr('last')
        if c == '/' or c == '\\':
            self.i += 1
            if c == '\\':
                delim = self.getc()
            else:
                delim = '/'
            pat = self.match_slash(delim, True)
            if pat is None:
                self.err('unterminated address regex')
            icase = mline = False
            while True:
                f = self.peek()
                if f == 'I':
                    icase = True
                    self.i += 1
                elif f == 'M':
                    mline = True
                    self.i += 1
                else:
                    break
            return Addr('re', regex=self.compile_regex(pat, icase, mline))
        return None

    def read_end_of_cmd(self):
        self.skip_blanks()
        c = self.peek()
        if c in (';', '\n', '\r'):
            self.i += 1
        elif c in ('}', '#', ''):
            pass
        else:
            self.err('extra characters after command')

    def read_label(self):
        self.skip_blanks()
        j = self.i
        while self.i < self.n and self.t[self.i] not in ' \t\n\r\v\f;':
            self.i += 1
        label = self.t[j:self.i]
        return label

    def read_text(self):
        self.skip_blanks()
        c = self.getc()
        lead = ''
        if c == '':
            self.err('expected \\ after `a\', `c\' or `i\'')
        if c == '\\':
            c2 = self.getc()
            if c2 == '':
                return '\n'
            if c2 != '\n':
                lead = c2
        else:
            self.i -= 1
        buf = [lead]
        while True:
            c = self.getc()
            if c == '' or c == '\n':
                break
            if c == '\\':
                c2 = self.getc()
                if c2 == '':
                    break
                buf.append('\\' + c2)
                continue
            buf.append(c)
        raw = ''.join(buf)
        return process_text_escapes(raw) + '\n'

    def parse_replacement(self, rep):
        items = []
        lit = []

        def flush():
            if lit:
                items.append(('lit', ''.join(lit)))
                del lit[:]
        i = 0
        n = len(rep)
        while i < n:
            c = rep[i]
            if c == '&':
                flush()
                items.append(('grp', 0))
                i += 1
                continue
            if c == '\\' and i + 1 < n:
                d = rep[i + 1]
                if d.isdigit():
                    flush()
                    items.append(('grp', int(d)))
                    i += 2
                    continue
                if d in 'LUElu':
                    flush()
                    items.append(('case', d))
                    i += 2
                    continue
                if d == '&':
                    lit.append('&')
                    i += 2
                    continue
                if d == '\n':
                    lit.append('\n')
                    i += 2
                    continue
                if d in SIMPLE_ESC:
                    lit.append(SIMPLE_ESC[d])
                    i += 2
                    continue
                if d in 'doxc':
                    r = parse_numeric_escape(rep, i + 1)
                    if r is not None:
                        ch, i = r
                        lit.append(ch)
                        continue
                lit.append(d)
                i += 2
                continue
            if c == '\\':
                i += 1
                continue
            lit.append(c)
            i += 1
        flush()
        return items

    def unescape_y(self, s):
        out = []
        i = 0
        n = len(s)
        while i < n:
            c = s[i]
            if c == '\\' and i + 1 < n:
                d = s[i + 1]
                if d == '\\':
                    out.append('\\')
                    i += 2
                    continue
                if d in SIMPLE_ESC:
                    out.append(SIMPLE_ESC[d])
                    i += 2
                    continue
                if d in 'doxc':
                    r = parse_numeric_escape(s, i + 1)
                    if r is not None:
                        ch, i = r
                        out.append(ch)
                        continue
                out.append(d)
                i += 2
                continue
            out.append(c)
            i += 1
        return ''.join(out)

    def parse(self):
        blocks = []
        while True:
            # skip whitespace and semicolons
            while self.i < self.n and self.t[self.i] in ' \t\n\r\v\f;':
                self.i += 1
            if self.i >= self.n:
                break
            c = self.peek()
            if c == '#':
                while self.i < self.n and self.t[self.i] != '\n':
                    self.i += 1
                continue
            a1 = self.parse_addr()
            a2 = None
            if a1 is not None:
                self.skip_blanks()
                if self.peek() == ',':
                    self.i += 1
                    self.skip_blanks()
                    c = self.peek()
                    if c == '+' or c == '~':
                        self.i += 1
                        if not self.peek().isdigit():
                            self.err('expected number')
                        num = self.read_number()
                        a2 = Addr('plus' if c == '+' else 'tilde', num)
                    else:
                        a2 = self.parse_addr()
                        if a2 is None:
                            self.err('unexpected `,\'')
                        if a2.kind == 'step':
                            # GNU treats N~M as addr2 like a line number N
                            a2 = Addr('num', a2.n)
                if a1.kind == 'num' and a1.n == 0:
                    if a2 is None or a2.kind != 're':
                        self.err('invalid usage of line address 0')
                    a1 = Addr('zero')
            self.skip_blanks()
            neg = False
            while self.peek() == '!':
                neg = True
                self.i += 1
                self.skip_blanks()
            c = self.getc()
            if c == '':
                self.err('missing command')
            cmd = Cmd(c)
            cmd.a1 = a1
            cmd.a2 = a2
            cmd.neg = neg
            if a1 is not None and a1.kind == 'zero':
                cmd.state = 1
            if c == '{':
                blocks.append(len(self.cmds))
                self.cmds.append(cmd)
                continue
            if c == '}':
                if not blocks:
                    self.err('unexpected `}\'')
                if a1 is not None:
                    self.err('} doesn\'t want any addresses')
                op = blocks.pop()
                self.cmds[op].block_end = len(self.cmds)
                self.cmds.append(cmd)
                self.read_end_of_cmd()
                continue
            if c in '=dDgGhHnNpPxzF':
                self.read_end_of_cmd()
            elif c in 'lL':
                self.skip_blanks()
                if self.peek().isdigit():
                    cmd.num = self.read_number()
                self.read_end_of_cmd()
            elif c in 'qQ':
                self.skip_blanks()
                cmd.num = 0
                if self.peek().isdigit():
                    cmd.num = self.read_number()
                self.read_end_of_cmd()
            elif c in 'aic':
                cmd.text = self.read_text()
            elif c == ':':
                if a1 is not None:
                    self.err(': doesn\'t want any addresses')
                label = self.read_label()
                if not label:
                    self.err('":" lacks a label')
                self.labels[label] = len(self.cmds)
                self.skip_blanks()
                if self.peek() == ';':
                    self.i += 1
            elif c in 'btT':
                label = self.read_label()
                cmd.label = label if label else None
                self.read_end_of_cmd()
            elif c == 's':
                delim = self.getc()
                if delim in ('', '\n', '\\'):
                    self.err('unterminated `s\' command')
                pat = self.match_slash(delim, True)
                if pat is None:
                    self.err('unterminated `s\' command')
                rep = self.match_slash(delim, False)
                if rep is None:
                    self.err('unterminated `s\' command')
                icase = mline = False
                while True:
                    f = self.peek()
                    if f == 'g':
                        cmd.gflag = True
                        self.i += 1
                    elif f == 'p':
                        cmd.pflag = True
                        self.i += 1
                    elif f in ('i', 'I'):
                        icase = True
                        self.i += 1
                    elif f in ('m', 'M'):
                        mline = True
                        self.i += 1
                    elif f == 'e':
                        self.i += 1
                    elif f != '' and f.isdigit():
                        cmd.nth = self.read_number()
                        if cmd.nth == 0:
                            self.err('number option to `s\' command may not be zero')
                    elif f == 'w':
                        while self.i < self.n and self.t[self.i] != '\n':
                            self.i += 1
                        break
                    else:
                        break
                cmd.regex = self.compile_regex(pat, icase, mline)
                cmd.repl = self.parse_replacement(rep)
                if cmd.regex is not None:
                    for it in cmd.repl:
                        if it[0] == 'grp' and it[1] > cmd.regex.ngroups:
                            self.err('invalid reference \\%d on `s\' command\'s RHS'
                                     % it[1])
                self.read_end_of_cmd()
            elif c == 'y':
                delim = self.getc()
                src = self.match_slash(delim, False)
                dst = self.match_slash(delim, False) if src is not None else None
                if src is None or dst is None:
                    self.err('unterminated `y\' command')
                src = self.unescape_y(src)
                dst = self.unescape_y(dst)
                if len(src) != len(dst):
                    self.err('strings for `y\' command are different lengths')
                table = {}
                for a, b in zip(src, dst):
                    if ord(a) not in table:
                        table[ord(a)] = b
                cmd.table = table
                self.read_end_of_cmd()
            elif c in 'rRwWe':
                # not supported: consume the argument to end of line
                self.skip_blanks()
                j = self.i
                while self.i < self.n and self.t[self.i] != '\n':
                    self.i += 1
                cmd.label = self.t[j:self.i]
            elif c == 'v':
                self.read_label()
                self.read_end_of_cmd()
            elif c == '#':
                while self.i < self.n and self.t[self.i] != '\n':
                    self.i += 1
                continue
            else:
                self.err('unknown command: `%s\'' % c)
            self.cmds.append(cmd)
        if blocks:
            self.err('unmatched `{\'')
        for idx, cmd in enumerate(self.cmds):
            if cmd.name in 'btT':
                if cmd.label is None:
                    cmd.target = None
                elif cmd.label in self.labels:
                    cmd.target = self.labels[cmd.label]
                else:
                    raise SedError("can't find label for jump to `%s'" % cmd.label)
        return self.cmds


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------

END, DELETE, RESTART, QUIT, QUIT_SILENT = range(5)

LIST_ESC = {'\a': 'a', '\b': 'b', '\f': 'f', '\n': 'n', '\r': 'r', '\t': 't',
            '\v': 'v'}


class Sed(object):
    def __init__(self, cmds, quiet, separate, files, line_len, zero):
        self.cmds = cmds
        self.quiet = quiet
        self.separate = separate
        self.line_len = line_len
        self.delim = '\0' if zero else '\n'
        self.out = []
        self.missing_nl = False
        self.bad = False
        self.sources = []
        for name in files:
            data = self.load(name)
            if data is None:
                continue
            self.sources.append((name, self.split_lines(data)))
        self.src = 0
        self.pos = 0
        self.cur_src = -1
        self.filename = '-'
        self.lineno = 0
        self._ps = ''
        self._ps_tail = []
        self._hold = ''
        self._hold_tail = []
        self.chomped = True
        self.flag = False
        self.append_q = []
        self.last_regex = None

    # Pattern and hold space; appends are buffered to avoid quadratic copying
    @property
    def ps(self):
        if self._ps_tail:
            self._ps_tail.insert(0, self._ps)
            self._ps = ''.join(self._ps_tail)
            self._ps_tail = []
        return self._ps

    @ps.setter
    def ps(self, v):
        self._ps = v
        self._ps_tail = []

    def ps_append(self, sep, text):
        self._ps_tail.append(sep)
        self._ps_tail.append(text)

    @property
    def hold(self):
        if self._hold_tail:
            self._hold_tail.insert(0, self._hold)
            self._hold = ''.join(self._hold_tail)
            self._hold_tail = []
        return self._hold

    @hold.setter
    def hold(self, v):
        self._hold = v
        self._hold_tail = []

    def load(self, name):
        try:
            if name == '-':
                data = sys.stdin.buffer.read()
            else:
                with open(name, 'rb') as f:
                    data = f.read()
        except IsADirectoryError:
            sys.stderr.write("sed: couldn't edit %s: not a regular file\n" % name)
            self.bad = True
            return None
        except OSError as e:
            msg = e.strerror or str(e)
            sys.stderr.write("sed: can't read %s: %s\n" % (name, msg))
            self.bad = True
            return None
        return data.decode('latin-1')

    def split_lines(self, data):
        if not data:
            return []
        parts = data.split(self.delim)
        lines = []
        if parts[-1] == '':
            parts.pop()
            for p in parts:
                lines.append((p, True))
        else:
            last = parts.pop()
            for p in parts:
                lines.append((p, True))
            lines.append((last, False))
        return lines

    # ---- input ----
    def _skip_empty(self):
        while self.src < len(self.sources) and \
                self.pos >= len(self.sources[self.src][1]):
            self.src += 1
            self.pos = 0

    def has_next(self):
        """Is there another input line available for n/N?"""
        if self.separate:
            if self.cur_src >= 0 and self.src == self.cur_src and \
                    self.pos < len(self.sources[self.src][1]):
                return True
            return False
        self._skip_empty()
        return self.src < len(self.sources)

    def is_last(self):
        if self.separate:
            if self.cur_src < 0:
                return True
            if self.src == self.cur_src and \
                    self.pos < len(self.sources[self.src][1]):
                return False
            return True
        self._skip_empty()
        return self.src >= len(self.sources)

    def next_line(self):
        self._skip_empty()
        if self.src >= len(self.sources):
            return None
        name, lines = self.sources[self.src]
        text, nl = lines[self.pos]
        self.pos += 1
        if self.src != self.cur_src:
            self.cur_src = self.src
            self.filename = name
            if self.separate:
                self.lineno = 0
                self.reset_ranges()
        self.lineno += 1
        return text, nl

    def reset_ranges(self):
        for cmd in self.cmds:
            if cmd.a1 is not None and cmd.a1.kind == 'zero':
                cmd.state = 1
            else:
                cmd.state = 0

    # ---- output ----
    def emit(self, text):
        if self.missing_nl:
            self.out.append(self.delim)
            self.missing_nl = False
        self.out.append(text)

    def output_ps(self):
        if self.chomped:
            self.emit(self.ps + self.delim)
        else:
            self.emit(self.ps)
            self.missing_nl = True

    def flush_append(self):
        for t in self.append_q:
            self.emit(t)
        self.append_q = []

    def read_line(self, append):
        self.flush_append()
        r = self.next_line()
        if r is None:
            return False
        text, nl = r
        self.flag = False
        if append:
            self.ps_append(self.delim, text)
        else:
            self.ps = text
        self.chomped = nl
        return True

    # ---- addresses ----
    def match_regex(self, regex):
        if regex is None:
            regex = self.last_regex
            if regex is None:
                raise SedError('no previous regular expression')
        else:
            self.last_regex = regex
        return regex.search(self.ps, 0) is not None

    def match1(self, a):
        k = a.kind
        if k == 'num':
            return self.lineno == a.n
        if k == 're':
            return self.match_regex(a.regex)
        if k == 'last':
            return self.is_last()
        if k == 'step':
            if a.step <= 0:
                return self.lineno == a.n
            return self.lineno >= a.n and (self.lineno - a.n) % a.step == 0
        return False   # zero

    def match_address(self, cmd):
        a1 = cmd.a1
        if a1 is None:
            return True
        a2 = cmd.a2
        if a2 is None:
            return self.match1(a1)
        ln = self.lineno
        if cmd.state == 1:
            k = a2.kind
            if k in ('num', 'plus', 'tilde'):
                if ln >= cmd.end:
                    cmd.state = 0
                return True
            if k == 'last':
                if self.is_last():
                    cmd.state = 0
                return True
            if k == 're':
                if self.match_regex(a2.regex):
                    cmd.state = 0
                return True
            cmd.state = 0
            return True
        if not self.match1(a1):
            return False
        k = a2.kind
        if k == 'num':
            if a2.n <= ln:
                return True
            cmd.end = a2.n
        elif k == 'plus':
            if a2.n == 0:
                return True
            cmd.end = ln + a2.n
        elif k == 'tilde':
            if a2.n <= 0:
                return True
            end = ((ln + a2.n - 1) // a2.n) * a2.n
            if end <= ln:
                return True
            cmd.end = end
        cmd.state = 1
        return True

    # ---- commands ----
    def do_subst(self, cmd):
        regex = cmd.regex
        if regex is None:
            regex = self.last_regex
            if regex is None:
                raise SedError('no previous regular expression')
        else:
            self.last_regex = regex
        s = self.ps
        n = len(s)
        pos = 0
        count = 0
        prev_end = -1
        out = []
        did = False
        nth = cmd.nth
        g = cmd.gflag
        while pos <= n:
            m = regex.search(s, pos)
            if m is None:
                break
            st, en, groups = m
            if st == en and st == prev_end:
                if st >= n:
                    break
                out.append(s[pos:st + 1])
                pos = st + 1
                continue
            count += 1
            out.append(s[pos:st])
            if count >= nth:
                out.append(self.expand(cmd.repl, s, st, en, groups))
                did = True
            else:
                out.append(s[st:en])
            prev_end = en
            if st == en:
                if en < n:
                    out.append(s[en])
                pos = en + 1
            else:
                pos = en
            if did and not g:
                break
        if not did:
            return
        if pos <= n:
            out.append(s[pos:])
        self.ps = ''.join(out)
        self.flag = True
        if cmd.pflag:
            self.output_ps()

    def expand(self, items, s, st, en, groups):
        res = []
        mode = None
        one = None
        for it in items:
            kind = it[0]
            if kind == 'case':
                c = it[1]
                if c == 'L' or c == 'U':
                    mode = c
                elif c == 'E':
                    mode = None
                    one = None
                else:
                    one = c
                continue
            if kind == 'lit':
                text = it[1]
            else:
                gi = it[1]
                if gi == 0:
                    text = s[st:en]
                else:
                    sp = groups[gi - 1] if gi - 1 < len(groups) else None
                    text = s[sp[0]:sp[1]] if sp is not None else ''
            if not text:
                continue
            if mode == 'L':
                text = a_lower(text)
            elif mode == 'U':
                text = a_upper(text)
            if one is not None:
                first = a_upper(text[0]) if one == 'u' else a_lower(text[0])
                text = first + text[1:]
                one = None
            res.append(text)
        return ''.join(res)

    def do_list(self, width):
        out = []
        cur = 0
        for ch in self.ps:
            o = ord(ch)
            if ch == '\\':
                e = '\\\\'
            elif 32 <= o < 127:
                e = ch
            elif ch in LIST_ESC:
                e = '\\' + LIST_ESC[ch]
            else:
                e = '\\%03o' % o
            if width > 1 and cur + len(e) > width - 1:
                out.append('\\\n')
                cur = 0
            out.append(e)
            cur += len(e)
        out.append('$\n')
        self.emit(''.join(out))

    def execute(self):
        cmds = self.cmds
        ncmds = len(cmds)
        pc = 0
        while pc < ncmds:
            cmd = cmds[pc]
            if cmd.a1 is not None:
                matched = self.match_address(cmd)
                if cmd.neg:
                    matched = not matched
            else:
                matched = not cmd.neg
            name = cmd.name
            if not matched:
                if name == '{':
                    pc = cmd.block_end + 1
                else:
                    pc += 1
                continue
            pc += 1
            if name == '{' or name == '}' or name == ':':
                continue
            if name == 's':
                self.do_subst(cmd)
            elif name == 'p':
                self.output_ps()
            elif name == 'd':
                return DELETE, 0
            elif name == 'D':
                idx = self.ps.find('\n')
                if idx < 0:
                    return DELETE, 0
                self.ps = self.ps[idx + 1:]
                return RESTART, 0
            elif name == 'b':
                if cmd.target is None:
                    return END, 0
                pc = cmd.target
            elif name == 't':
                if self.flag:
                    self.flag = False
                    if cmd.target is None:
                        return END, 0
                    pc = cmd.target
            elif name == 'T':
                if not self.flag:
                    if cmd.target is None:
                        return END, 0
                    pc = cmd.target
                else:
                    self.flag = False
            elif name == 'h':
                self.hold = self.ps
            elif name == 'H':
                self._hold_tail.append('\n')
                self._hold_tail.append(self.ps)
            elif name == 'g':
                self.ps = self.hold
            elif name == 'G':
                self.ps_append('\n', self.hold)
            elif name == 'x':
                a, b = self.ps, self.hold
                self.ps, self.hold = b, a
            elif name == 'n':
                if not self.has_next():
                    return END, 0
                if not self.quiet:
                    self.output_ps()
                self.read_line(False)
            elif name == 'N':
                if not self.has_next():
                    return END, 0
                self.read_line(True)
            elif name == 'P':
                idx = self.ps.find('\n')
                if idx < 0:
                    self.emit(self.ps + self.delim)
                else:
                    self.emit(self.ps[:idx] + self.delim)
            elif name == 'a':
                self.append_q.append(cmd.text)
            elif name == 'i':
                self.emit(cmd.text)
            elif name == 'c':
                if cmd.a2 is None or cmd.state != 1:
                    self.emit(cmd.text)
                return DELETE, 0
            elif name == '=':
                self.emit('%d\n' % self.lineno)
            elif name == 'l':
                width = self.line_len if cmd.num is None else cmd.num
                self.do_list(width)
            elif name == 'L':
                pass
            elif name == 'q':
                return QUIT, cmd.num
            elif name == 'Q':
                return QUIT_SILENT, cmd.num
            elif name == 'y':
                self.ps = self.ps.translate(cmd.table)
            elif name == 'z':
                self.ps = ''
            elif name == 'F':
                self.emit(self.filename + '\n')
            # r R w W e v: unsupported, ignored
        return END, 0

    def run(self):
        restart = False
        while True:
            if not restart:
                if not self.read_line(False):
                    break
            restart = False
            res, code = self.execute()
            if res == END:
                if not self.quiet:
                    self.output_ps()
                self.flush_append()
            elif res == DELETE:
                self.flush_append()
            elif res == RESTART:
                self.flush_append()
                restart = True
            elif res == QUIT:
                if not self.quiet:
                    self.output_ps()
                self.flush_append()
                return code
            elif res == QUIT_SILENT:
                return code
        self.flush_append()
        return 2 if self.bad else 0

    def write_out(self):
        data = ''.join(self.out).encode('latin-1')
        self.out = []
        try:
            sys.stdout.buffer.write(data)
            sys.stdout.buffer.flush()
        except BrokenPipeError:
            pass


# ---------------------------------------------------------------------------
# Command line
# ---------------------------------------------------------------------------

def arg_str(a):
    try:
        return os.fsencode(a).decode('latin-1')
    except Exception:
        return a


USAGE = """\
Usage: sed [OPTION]... {script-only-if-no-other-script} [input-file]...

  -n, --quiet, --silent
                 suppress automatic printing of pattern space
  -e script, --expression=script
                 add the script to the commands to be executed
  -E, -r, --regexp-extended
                 use extended regular expressions in the script
  -s, --separate
                 consider files as separate rather than as a single
                 continuous long stream.
"""

LONG_OPTS = {
    'quiet': 'n', 'silent': 'n', 'expression': 'e', 'file': 'f',
    'regexp-extended': 'E', 'separate': 's', 'line-length': 'l',
    'null-data': 'z', 'zero-terminated': 'z', 'unbuffered': 'u',
    'posix': 'posix', 'debug': 'debug', 'sandbox': 'sandbox',
    'binary': 'b', 'follow-symlinks': 'follow', 'help': 'help',
    'version': 'version', 'in-place': 'i',
}


def parse_args(argv):
    quiet = False
    ere = False
    separate = False
    zero = False
    line_len = 70
    scripts = []
    have_script = False
    nonopts = []
    i = 0
    n = len(argv)
    while i < n:
        a = argv[i]
        i += 1
        if a == '--':
            nonopts.extend(argv[i:])
            break
        if a.startswith('--') and len(a) > 2:
            name, eq, val = a[2:].partition('=')
            matches = [k for k in LONG_OPTS if k.startswith(name)]
            if name in LONG_OPTS:
                matches = [name]
            if len(matches) != 1:
                raise SedError("unknown option -- '%s'\n%s" % (name, USAGE))
            opt = LONG_OPTS[matches[0]]
            if opt in ('e', 'f', 'l'):
                if not eq:
                    if i >= n:
                        raise SedError("option '--%s' requires an argument" % name)
                    val = argv[i]
                    i += 1
                if opt == 'e':
                    scripts.append(arg_str(val))
                    have_script = True
                elif opt == 'f':
                    scripts.append(read_script_file(val))
                    have_script = True
                else:
                    line_len = int(val)
            elif opt == 'n':
                quiet = True
            elif opt == 'E':
                ere = True
            elif opt == 's':
                separate = True
            elif opt == 'z':
                zero = True
            elif opt == 'i':
                separate = True
            elif opt == 'help':
                sys.stdout.write(USAGE)
                sys.exit(0)
            elif opt == 'version':
                sys.stdout.write('sed (GNU sed) 4.9\n')
                sys.exit(0)
            continue
        if a.startswith('-') and len(a) > 1:
            j = 1
            while j < len(a):
                c = a[j]
                j += 1
                if c == 'n':
                    quiet = True
                elif c in 'Er':
                    ere = True
                elif c == 's':
                    separate = True
                elif c == 'z':
                    zero = True
                elif c in 'ub':
                    pass
                elif c == 'i':
                    separate = True
                    break
                elif c in 'efl':
                    if j < len(a):
                        val = a[j:]
                    else:
                        if i >= n:
                            raise SedError("option requires an argument -- '%s'\n%s"
                                           % (c, USAGE))
                        val = argv[i]
                        i += 1
                    if c == 'e':
                        scripts.append(arg_str(val))
                        have_script = True
                    elif c == 'f':
                        scripts.append(read_script_file(val))
                        have_script = True
                    else:
                        line_len = int(val)
                    break
                else:
                    raise SedError("invalid option -- '%s'\n%s" % (c, USAGE))
            continue
        nonopts.append(a)
    if not have_script:
        if not nonopts:
            raise SedError(USAGE)
        scripts.append(arg_str(nonopts.pop(0)))
    files = list(nonopts)
    return quiet, ere, separate, zero, line_len, scripts, files


def read_script_file(name):
    try:
        if name == '-':
            data = sys.stdin.buffer.read()
        else:
            with open(name, 'rb') as f:
                data = f.read()
    except OSError as e:
        raise SedError("couldn't open file %s: %s" % (name, e.strerror))
    text = data.decode('latin-1')
    if text.endswith('\n'):
        text = text[:-1]
    return text


def main(argv):
    try:
        quiet, ere, separate, zero, line_len, scripts, files = parse_args(argv)
        script = '\n'.join(scripts)
        if script.startswith('#n') and (len(script) == 2 or script[2] == '\n'):
            quiet = True
        cmds = ScriptParser(script, ere).parse()
    except SedError as e:
        sys.stderr.write('sed: %s\n' % e)
        return e.status
    if not files:
        files = ['-']
    sed = Sed(cmds, quiet, separate, files, line_len, zero)
    try:
        status = sed.run()
    except SedError as e:
        sed.write_out()
        sys.stderr.write('sed: %s\n' % e)
        return 4
    sed.write_out()
    return status


if __name__ == '__main__':
    sys.setrecursionlimit(20000)
    sys.exit(main(sys.argv[1:]))
