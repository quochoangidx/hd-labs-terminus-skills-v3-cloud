"""pysed: a GNU sed 4.9 replacement in pure Python.

Usage: python3 /app/pysed/sed.py [OPTION]... {script-only-if-no-other-script} [input-file]...
"""

import os
import sys

# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class SedError(Exception):
    def __init__(self, msg, status=1):
        Exception.__init__(self, msg)
        self.msg = msg
        self.status = status


# ---------------------------------------------------------------------------
# Character helpers (C locale, bytes decoded as latin-1)
# ---------------------------------------------------------------------------

ALLCHARS = [chr(i) for i in range(256)]
_UPPER_TABLE = {i: i - 32 for i in range(ord('a'), ord('z') + 1)}
_LOWER_TABLE = {i: i + 32 for i in range(ord('A'), ord('Z') + 1)}


def a_upper(s):
    return s.translate(_UPPER_TABLE)


def a_lower(s):
    return s.translate(_LOWER_TABLE)


def _rng(a, b):
    return set(chr(i) for i in range(ord(a), ord(b) + 1))


CLASSES = {
    'alpha': _rng('a', 'z') | _rng('A', 'Z'),
    'digit': _rng('0', '9'),
    'alnum': _rng('a', 'z') | _rng('A', 'Z') | _rng('0', '9'),
    'upper': _rng('A', 'Z'),
    'lower': _rng('a', 'z'),
    'space': set(' \t\n\v\f\r'),
    'blank': set(' \t'),
    'punct': set(chr(i) for i in range(33, 127)
                 if not chr(i).isalnum()),
    'print': set(chr(i) for i in range(32, 127)),
    'graph': set(chr(i) for i in range(33, 127)),
    'cntrl': set(chr(i) for i in range(0, 32)) | {chr(127)},
    'xdigit': _rng('0', '9') | _rng('a', 'f') | _rng('A', 'F'),
}
WORDCHARS = frozenset(CLASSES['alnum'] | {'_'})


def is_word(c):
    return c in WORDCHARS


# ---------------------------------------------------------------------------
# Escape processing
# ---------------------------------------------------------------------------

SIMPLE_ESC = {'a': '\a', 'f': '\f', 'n': '\n', 'r': '\r', 't': '\t',
              'v': '\v'}


def convert_number(text, i, base):
    """text[i] is the letter (d, o or x). Returns (char, new_index)."""
    if base == 16:
        maxd, digits = 2, '0123456789abcdefABCDEF'
    elif base == 8:
        maxd, digits = 3, '01234567'
    else:
        maxd, digits = 3, '0123456789'
    j = i + 1
    n = 0
    while j < len(text) and j - (i + 1) < maxd and text[j] in digits:
        n = n * base + int(text[j], base)
        j += 1
    if j == i + 1:
        return text[i], j
    return chr(n & 0xff), j


def try_escape(text, i):
    """text[i] is the char after a backslash.  If it is one of the
    character-producing escapes, return (char, new_index, numeric) else None."""
    d = text[i]
    if d in SIMPLE_ESC:
        return SIMPLE_ESC[d], i + 1, False
    if d == 'c':
        if i + 1 < len(text):
            x = text[i + 1]
            return chr(ord(a_upper(x)) ^ 0x40), i + 2, True
        return None
    if d == 'd':
        c, j = convert_number(text, i, 10)
        return c, j, True
    if d == 'o':
        c, j = convert_number(text, i, 8)
        return c, j, True
    if d == 'x':
        c, j = convert_number(text, i, 16)
        return c, j, True
    return None


def regex_escapes(text):
    out = []
    i = 0
    n = len(text)
    while i < n:
        c = text[i]
        if c == '\\' and i + 1 < n:
            r = try_escape(text, i + 1)
            if r is not None:
                ch, j, numeric = r
                if numeric and ch == '\\':
                    out.append('\\\\')
                else:
                    out.append(ch)
                i = j
                continue
            out.append(c)
            out.append(text[i + 1])
            i += 2
            continue
        out.append(c)
        i += 1
    return ''.join(out)


def text_escapes(text):
    """Escape processing for a/i/c text: known escapes produce chars, other
    backslashes are removed."""
    out = []
    i = 0
    n = len(text)
    while i < n:
        c = text[i]
        if c == '\\' and i + 1 < n:
            r = try_escape(text, i + 1)
            if r is not None:
                out.append(r[0])
                i = r[1]
                continue
            out.append(text[i + 1])
            i += 2
            continue
        out.append(c)
        i += 1
    return ''.join(out)


# ---------------------------------------------------------------------------
# Regular expressions: parser
# ---------------------------------------------------------------------------

# AST nodes:
#  ('char', c) ('any',) ('set', frozenset) ('assert', kind)
#  ('group', idx, node) ('backref', n) ('cat', [nodes]) ('alt', [nodes])
#  ('rep', node, min, max)

A_BOL, A_EOL, A_BUFSTART, A_BUFEND, A_WORDB, A_NWORDB, A_WSTART, A_WEND = \
    range(8)


class RegexParser(object):
    def __init__(self, pat, ere, icase, mline):
        self.p = pat
        self.n = len(pat)
        self.i = 0
        self.ere = ere
        self.icase = icase
        self.mline = mline
        self.ngroups = 0
        self.has_backref = False
        self.open_groups = []

    def error(self, msg):
        raise SedError(msg)

    def parse(self):
        node = self.parse_alt(0)
        if self.i < self.n:
            # unmatched close paren
            if self.ere:
                self.error("Unmatched ) or \\)")
            self.error("Unmatched ) or \\)")
        return node

    def at_alt(self):
        p, i = self.p, self.i
        if self.ere:
            return p[i] == '|'
        return p[i] == '\\' and i + 1 < self.n and p[i + 1] == '|'

    def at_close(self, depth):
        if depth == 0:
            return False
        p, i = self.p, self.i
        if self.ere:
            return p[i] == ')'
        return p[i] == '\\' and i + 1 < self.n and p[i + 1] == ')'

    def parse_alt(self, depth):
        branches = [self.parse_branch(depth)]
        while self.i < self.n and self.at_alt():
            self.i += 1 if self.ere else 2
            branches.append(self.parse_branch(depth))
        if len(branches) == 1:
            return branches[0]
        return ('alt', branches)

    def parse_branch(self, depth):
        items = []
        while self.i < self.n and not self.at_alt() and not self.at_close(depth):
            atom = self.parse_atom(items, depth)
            if not (atom[0] == 'assert' and atom[1] == A_BOL):
                atom = self.parse_postfix(atom)
            items.append(atom)
        return ('cat', items)

    def bre_dollar_is_anchor(self, j):
        p = self.p
        if j >= self.n:
            return True
        if p[j] == '\\' and j + 1 < self.n and p[j + 1] in ')|':
            return True
        return False

    def lit(self, c):
        if self.icase:
            lo, up = a_lower(c), a_upper(c)
            if lo != up:
                return ('set', frozenset((lo, up)))
        return ('char', c)

    def make_set(self, chars, negate):
        s = set(chars)
        if self.icase:
            extra = set()
            for c in s:
                extra.add(a_lower(c))
                extra.add(a_upper(c))
            s |= extra
        if negate:
            s = set(ALLCHARS) - s
            if self.mline:
                s.discard('\n')
        return ('set', frozenset(s))

    def parse_atom(self, items, depth):
        p = self.p
        c = p[self.i]
        at_start = (not items) or all(
            it[0] == 'assert' and it[1] == A_BOL for it in items)
        if self.ere:
            if c == '(':
                self.i += 1
                self.ngroups += 1
                idx = self.ngroups
                self.open_groups.append(idx)
                sub = self.parse_alt(depth + 1)
                self.open_groups.pop()
                if self.i >= self.n or p[self.i] != ')':
                    self.error("Unmatched ( or \\(")
                self.i += 1
                return ('group', idx, sub)
            if c == '^':
                self.i += 1
                return ('assert', A_BOL)
            if c == '$':
                self.i += 1
                return ('assert', A_EOL)
            if c in '*+?' and at_start:
                self.i += 1
                return self.lit(c)
            if c == '{' and at_start:
                self.i += 1
                return self.lit(c)
        else:
            if c == '^' and not items:
                self.i += 1
                return ('assert', A_BOL)
            if c == '$' and self.bre_dollar_is_anchor(self.i + 1):
                self.i += 1
                return ('assert', A_EOL)
            if c == '*' and at_start:
                self.i += 1
                return self.lit(c)
        if c == '.':
            self.i += 1
            if self.mline:
                return ('set', frozenset(set(ALLCHARS) - {'\n'}))
            return ('any',)
        if c == '[':
            return self.parse_bracket()
        if c == '\\':
            if self.i + 1 >= self.n:
                self.error("Trailing backslash")
            d = p[self.i + 1]
            self.i += 2
            if not self.ere:
                if d == '(':
                    self.ngroups += 1
                    idx = self.ngroups
                    self.open_groups.append(idx)
                    sub = self.parse_alt(depth + 1)
                    self.open_groups.pop()
                    if not (self.i + 1 < self.n and p[self.i] == '\\'
                            and p[self.i + 1] == ')'):
                        self.error("Unmatched ( or \\(")
                    self.i += 2
                    return ('group', idx, sub)
                if d == ')':
                    self.error("Unmatched ) or \\)")
                if d in '{+?' and at_start:
                    return self.lit(d)
            if d in '123456789':
                k = int(d)
                if k > self.ngroups or k in self.open_groups:
                    if k > self.ngroups:
                        self.error("Invalid back reference")
                self.has_backref = True
                return ('backref', k)
            if d == 'w':
                return ('set', frozenset(WORDCHARS))
            if d == 'W':
                s = set(ALLCHARS) - WORDCHARS
                if self.mline:
                    s.discard('\n')
                return ('set', frozenset(s))
            if d == 's':
                return ('set', frozenset(CLASSES['space']))
            if d == 'S':
                s = set(ALLCHARS) - CLASSES['space']
                if self.mline:
                    s.discard('\n')
                return ('set', frozenset(s))
            if d == 'b':
                return ('assert', A_WORDB)
            if d == 'B':
                return ('assert', A_NWORDB)
            if d == '<':
                return ('assert', A_WSTART)
            if d == '>':
                return ('assert', A_WEND)
            if d == '`':
                return ('assert', A_BUFSTART)
            if d == "'":
                return ('assert', A_BUFEND)
            if d == 'n':
                return self.lit('\n')
            return self.lit(d)
        self.i += 1
        return self.lit(c)

    def parse_interval(self):
        """self.i points just after '{' (ERE) or '\\{' (BRE).  Returns
        (min, max) and advances, or None (position unchanged) if invalid."""
        p = self.p
        j = self.i
        start = j
        while j < self.n and p[j].isdigit():
            j += 1
        m_s = p[start:j]
        comma = False
        n_s = ''
        if j < self.n and p[j] == ',':
            comma = True
            j += 1
            s2 = j
            while j < self.n and p[j].isdigit():
                j += 1
            n_s = p[s2:j]
        if self.ere:
            if j < self.n and p[j] == '}':
                j += 1
            else:
                return None
        else:
            if j + 1 < self.n and p[j] == '\\' and p[j + 1] == '}':
                j += 2
            else:
                self.error("Unmatched \\{")
        if not m_s and not comma:
            if self.ere:
                return None
            self.error("Invalid content of \\{\\}")
        mn = int(m_s) if m_s else 0
        if comma:
            mx = int(n_s) if n_s else None
        else:
            mx = mn
        if mx is not None and mx < mn:
            self.error("Invalid content of \\{\\}")
        if mn > 32767 or (mx is not None and mx > 32767):
            self.error("Regular expression too big")
        self.i = j
        return mn, mx

    def parse_postfix(self, atom):
        p = self.p
        while self.i < self.n:
            c = p[self.i]
            if c == '*':
                self.i += 1
                atom = ('rep', atom, 0, None)
            elif self.ere and c == '+':
                self.i += 1
                atom = ('rep', atom, 1, None)
            elif self.ere and c == '?':
                self.i += 1
                atom = ('rep', atom, 0, 1)
            elif self.ere and c == '{':
                save = self.i
                self.i += 1
                r = self.parse_interval()
                if r is None:
                    self.i = save
                    break
                atom = ('rep', atom, r[0], r[1])
            elif (not self.ere) and c == '\\' and self.i + 1 < self.n \
                    and p[self.i + 1] in '+?{':
                d = p[self.i + 1]
                self.i += 2
                if d == '+':
                    atom = ('rep', atom, 1, None)
                elif d == '?':
                    atom = ('rep', atom, 0, 1)
                else:
                    r = self.parse_interval()
                    atom = ('rep', atom, r[0], r[1])
            else:
                break
        return atom

    def parse_bracket(self):
        p = self.p
        n = self.n
        i = self.i + 1
        negate = False
        if i < n and p[i] == '^':
            negate = True
            i += 1
        chars = set()
        first = True
        while True:
            if i >= n:
                self.error("Unmatched [, [^, [:, [., or [=")
            c = p[i]
            if c == ']' and not first:
                i += 1
                break
            first = False
            start_char = None
            if c == '[' and i + 1 < n and p[i + 1] in ':=.':
                kind = p[i + 1]
                end = p.find(kind + ']', i + 2)
                if end < 0:
                    self.error("Unmatched [, [^, [:, [., or [=")
                name = p[i + 2:end]
                i = end + 2
                if kind == ':':
                    if name not in CLASSES:
                        self.error("Invalid character class name")
                    chars |= CLASSES[name]
                    continue
                if len(name) != 1:
                    self.error("Invalid collation character")
                start_char = name
            else:
                start_char = c
                i += 1
            if i + 1 < n and p[i] == '-' and p[i + 1] != ']':
                i += 1
                if p[i] == '[' and i + 1 < n and p[i + 1] in '.=':
                    kind = p[i + 1]
                    end = p.find(kind + ']', i + 2)
                    if end < 0:
                        self.error("Unmatched [, [^, [:, [., or [=")
                    end_char = p[i + 2:end]
                    i = end + 2
                    if len(end_char) != 1:
                        self.error("Invalid collation character")
                else:
                    end_char = p[i]
                    i += 1
                if ord(end_char) < ord(start_char):
                    self.error("Invalid range end")
                chars |= _rng(start_char, end_char)
            else:
                chars.add(start_char)
        self.i = i
        return self.make_set(chars, negate)


# ---------------------------------------------------------------------------
# Regular expressions: compiler and backtracking matcher
# ---------------------------------------------------------------------------

OP_CHAR, OP_SET, OP_ANY, OP_ASSERT, OP_SAVE, OP_SPLIT, OP_JMP, \
    OP_BACKREF, OP_MATCH = range(9)


class Regex(object):
    def __init__(self, pattern, ere, icase, mline):
        self.pattern = pattern
        self.icase = icase
        self.mline = mline
        parser = RegexParser(regex_escapes(pattern), ere, icase, mline)
        ast = parser.parse()
        self.ngroups = parser.ngroups
        self.has_backref = parser.has_backref
        self.nslots = 2 * (self.ngroups + 1)
        prog = []
        prog.append([OP_SAVE, 0, None])
        self._emit(ast, prog)
        prog.append([OP_SAVE, 1, None])
        prog.append([OP_MATCH, None, None])
        self.prog = [tuple(x) for x in prog]
        self.first_char = None
        if len(self.prog) > 1 and self.prog[1][0] == OP_CHAR:
            self.first_char = self.prog[1][1]
        fs, nullable = self._first(ast)
        self.first_set = None if nullable else frozenset(fs)

    def _first(self, node):
        """Return (set of possible first chars, can-match-empty)."""
        t = node[0]
        if t == 'char':
            return {node[1]}, False
        if t == 'set':
            return set(node[1]), False
        if t == 'any':
            return set(ALLCHARS), False
        if t == 'assert':
            return set(), True
        if t == 'group':
            return self._first(node[2])
        if t == 'backref':
            return set(ALLCHARS), True
        if t == 'cat':
            acc = set()
            for sub in node[1]:
                fs, nl = self._first(sub)
                acc |= fs
                if not nl:
                    return acc, False
            return acc, True
        if t == 'alt':
            acc = set()
            anynull = False
            for sub in node[1]:
                fs, nl = self._first(sub)
                acc |= fs
                anynull = anynull or nl
            return acc, anynull
        if t == 'rep':
            fs, nl = self._first(node[1])
            if node[3] == 0:
                return set(), True
            return fs, nl or node[2] == 0
        return set(ALLCHARS), True

    def _emit(self, node, prog):
        t = node[0]
        if t == 'char':
            prog.append([OP_CHAR, node[1], None])
        elif t == 'set':
            prog.append([OP_SET, node[1], None])
        elif t == 'any':
            prog.append([OP_ANY, None, None])
        elif t == 'assert':
            prog.append([OP_ASSERT, node[1], None])
        elif t == 'group':
            idx = node[1]
            prog.append([OP_SAVE, 2 * idx, None])
            self._emit(node[2], prog)
            prog.append([OP_SAVE, 2 * idx + 1, None])
        elif t == 'backref':
            prog.append([OP_BACKREF, node[1], None])
        elif t == 'cat':
            for sub in node[1]:
                self._emit(sub, prog)
        elif t == 'alt':
            jumps = []
            branches = node[1]
            for k, br in enumerate(branches):
                if k < len(branches) - 1:
                    split = [OP_SPLIT, len(prog) + 1, None]
                    prog.append(split)
                    self._emit(br, prog)
                    j = [OP_JMP, None, None]
                    prog.append(j)
                    jumps.append(j)
                    split[2] = len(prog)
                else:
                    self._emit(br, prog)
            for j in jumps:
                j[1] = len(prog)
        elif t == 'rep':
            sub, mn, mx = node[1], node[2], node[3]
            for _ in range(mn):
                self._emit(sub, prog)
            if mx is None:
                loop = len(prog)
                split = [OP_SPLIT, loop + 1, None]
                prog.append(split)
                self._emit(sub, prog)
                prog.append([OP_JMP, loop, None])
                split[2] = len(prog)
            else:
                splits = []
                for _ in range(mx - mn):
                    split = [OP_SPLIT, len(prog) + 1, None]
                    prog.append(split)
                    splits.append(split)
                    self._emit(sub, prog)
                for s in splits:
                    s[2] = len(prog)
        else:
            raise SedError("internal regex error")

    def search(self, s, start=0, first_only=False):
        """Leftmost-longest search.  Returns list of slot positions or None."""
        n = len(s)
        visited = set()
        fc = self.first_char
        fset = self.first_set
        st = start
        while st <= n:
            if fc is not None:
                k = s.find(fc, st)
                if k < 0:
                    return None
                st = k
            elif fset is not None:
                while st < n and s[st] not in fset:
                    st += 1
                if st >= n:
                    return None
            r = self._run(s, st, visited, first_only)
            if r is not None:
                return r
            if self.has_backref:
                visited = set()
            st += 1
        return None

    def _run(self, s, st, visited, first_only):
        prog = self.prog
        n = len(s)
        n1 = n + 1
        mline = self.mline
        icase = self.icase
        backref_mode = self.has_backref
        caps = [-1] * self.nslots
        stack = [(0, st)]
        best = -1
        best_caps = None
        pop = stack.pop
        push = stack.append
        vadd = visited.add
        while stack:
            pc, pos = pop()
            if pc < 0:
                caps[-1 - pc] = pos
                continue
            while True:
                op = prog[pc]
                code = op[0]
                if code == OP_CHAR:
                    if pos < n and s[pos] == op[1]:
                        pc += 1
                        pos += 1
                        continue
                    break
                elif code == OP_SET:
                    if pos < n and s[pos] in op[1]:
                        pc += 1
                        pos += 1
                        continue
                    break
                elif code == OP_ANY:
                    if pos < n:
                        pc += 1
                        pos += 1
                        continue
                    break
                elif code == OP_SPLIT:
                    if backref_mode:
                        key = (pc, pos, tuple(caps))
                    else:
                        key = pc * n1 + pos
                    if key in visited:
                        break
                    vadd(key)
                    push((op[2], pos))
                    pc = op[1]
                    continue
                elif code == OP_JMP:
                    pc = op[1]
                    continue
                elif code == OP_SAVE:
                    slot = op[1]
                    push((-1 - slot, caps[slot]))
                    caps[slot] = pos
                    pc += 1
                    continue
                elif code == OP_ASSERT:
                    k = op[1]
                    if k == A_BOL:
                        ok = pos == 0 or (mline and s[pos - 1] == '\n')
                    elif k == A_EOL:
                        ok = pos == n or (mline and s[pos] == '\n')
                    elif k == A_BUFSTART:
                        ok = pos == 0
                    elif k == A_BUFEND:
                        ok = pos == n
                    else:
                        before = pos > 0 and s[pos - 1] in WORDCHARS
                        after = pos < n and s[pos] in WORDCHARS
                        if k == A_WORDB:
                            ok = before != after
                        elif k == A_NWORDB:
                            ok = before == after
                        elif k == A_WSTART:
                            ok = after and not before
                        else:
                            ok = before and not after
                    if ok:
                        pc += 1
                        continue
                    break
                elif code == OP_BACKREF:
                    g = op[1]
                    a = caps[2 * g]
                    b = caps[2 * g + 1]
                    if a < 0 or b < 0:
                        break
                    ln = b - a
                    if pos + ln > n:
                        break
                    if icase:
                        if a_lower(s[pos:pos + ln]) != a_lower(s[a:b]):
                            break
                    elif s[pos:pos + ln] != s[a:b]:
                        break
                    pos += ln
                    pc += 1
                    continue
                elif code == OP_MATCH:
                    if pos > best:
                        best = pos
                        best_caps = caps[:]
                        if first_only or pos == n:
                            return best_caps
                    break
                else:
                    break
        return best_caps


# ---------------------------------------------------------------------------
# Script parsing
# ---------------------------------------------------------------------------

RANGE_INACTIVE, RANGE_ACTIVE, RANGE_CLOSED = range(3)

REPL_ASIS = 0
REPL_UPPERCASE = 1
REPL_LOWERCASE = 2
REPL_UPPERCASE_FIRST = 4
REPL_LOWERCASE_FIRST = 8
REPL_MODIFIERS = REPL_UPPERCASE_FIRST | REPL_LOWERCASE_FIRST


class Addr(object):
    __slots__ = ('kind', 'n1', 'n2', 'regex')

    def __init__(self, kind, n1=0, n2=0, regex=None):
        self.kind = kind   # 'num','step','last','re','zero','plus','mult'
        self.n1 = n1
        self.n2 = n2
        self.regex = regex


class Cmd(object):
    def __init__(self):
        self.a1 = None
        self.a2 = None
        self.negate = False
        self.name = None
        self.range_state = RANGE_INACTIVE
        self.range_end = 0
        self.text = None
        self.label = None
        self.target = None
        self.int_arg = -1
        self.block_end = None
        # s command
        self.regex = None
        self.repl = None
        self.glob = False
        self.numb = 1
        self.sprint = 0
        # y command
        self.ymap = None

    def reset_range(self):
        if self.a1 is not None and self.a1.kind == 'zero':
            self.range_state = RANGE_ACTIVE
        else:
            self.range_state = RANGE_INACTIVE


EOF = None


class EmptyRegex(object):
    pass


EMPTY_REGEX = EmptyRegex()


class ScriptParser(object):
    def __init__(self, text, ere):
        self.s = text
        self.n = len(text)
        self.i = 0
        self.ere = ere

    def error(self, msg):
        raise SedError("-e expression #1, char %d: %s" % (self.i, msg))

    def getc(self):
        if self.i >= self.n:
            self.i += 1
            return EOF
        c = self.s[self.i]
        self.i += 1
        return c

    def ungetc(self):
        self.i -= 1

    def peek(self):
        if self.i >= self.n:
            return EOF
        return self.s[self.i]

    def in_nonblank(self):
        while True:
            c = self.getc()
            if c is EOF or c not in ' \t':
                return c

    def in_integer(self, c):
        digits = c
        while True:
            d = self.peek()
            if d is not EOF and d.isdigit():
                digits += d
                self.i += 1
            else:
                break
        return int(digits)

    def match_slash(self, slash, regex):
        buf = []
        while True:
            ch = self.getc()
            if ch is EOF or ch == '\n':
                return None
            if ch == slash:
                return ''.join(buf)
            if ch == '\\':
                ch = self.getc()
                if ch is EOF:
                    return None
                elif ch == 'n' and regex:
                    ch = '\n'
                elif ch != '\n' and (ch != slash or (not regex and ch == '&')):
                    buf.append('\\')
            buf.append(ch)

    def make_regex(self, pattern, icase, mline):
        if pattern == '':
            if icase or mline:
                self.error("no previous regular expression")
            return EMPTY_REGEX
        return Regex(pattern, self.ere, icase, mline)

    def compile_address(self, ch):
        """Returns an Addr or None (and leaves ch unconsumed)."""
        if ch == '/' or ch == '\\':
            if ch == '\\':
                ch = self.getc()
                if ch is EOF or ch == '\n':
                    self.error("unexpected `,'")
            pat = self.match_slash(ch, True)
            if pat is None:
                self.error("unterminated address regex")
            icase = mline = False
            while True:
                c = self.in_nonblank()
                if c == 'I':
                    icase = True
                elif c == 'M':
                    mline = True
                else:
                    if c is not EOF:
                        self.ungetc()
                    else:
                        self.i -= 1
                    break
            return Addr('re', regex=self.make_regex(pat, icase, mline))
        if ch is not EOF and ch.isdigit():
            num = self.in_integer(ch)
            c = self.in_nonblank()
            if c == '~':
                c2 = self.in_nonblank()
                if c2 is not EOF and c2.isdigit():
                    step = self.in_integer(c2)
                else:
                    if c2 is not EOF:
                        self.ungetc()
                    else:
                        self.i -= 1
                    step = 0
                return Addr('step', num, step)
            if c is not EOF:
                self.ungetc()
            else:
                self.i -= 1
            return Addr('num', num)
        if ch == '+' or ch == '~':
            c = self.in_nonblank()
            if c is not EOF and c.isdigit():
                num = self.in_integer(c)
            else:
                if c is not EOF:
                    self.ungetc()
                else:
                    self.i -= 1
                num = 0
            return Addr('plus' if ch == '+' else 'mult', num)
        if ch == '$':
            return Addr('last')
        return None

    def read_end_of_cmd(self):
        ch = self.in_nonblank()
        if ch == '}' or ch == '#':
            self.ungetc()
        elif ch is not EOF and ch != '\n' and ch != ';':
            self.error("extra characters after command")

    def read_label(self):
        ch = self.in_nonblank()
        buf = []
        while ch is not EOF and ch != '\n' and ch not in ' \t\r\v\f' \
                and ch != ';':
            buf.append(ch)
            ch = self.getc()
        return ''.join(buf)

    def read_text(self):
        ch = self.in_nonblank()
        if ch is EOF:
            self.error("expected \\ after `a', `c' or `i'")
        if ch == '\\':
            ch = self.getc()
        else:
            self.ungetc()
            ch = '\n'
        if ch is EOF:
            self.error("expected \\ after `a', `c' or `i'")
        buf = []
        if ch != '\n':
            buf.append(ch)
        ch = self.getc()
        while ch is not EOF and ch != '\n':
            if ch == '\\':
                ch = self.getc()
                if ch is not EOF:
                    buf.append('\\')
            if ch is EOF:
                break
            buf.append(ch)
            ch = self.getc()
        buf.append('\n')
        return text_escapes(''.join(buf))

    def setup_replacement(self, text):
        nodes = []   # [prefix, subst_id, repl_type]
        repl_type = REPL_ASIS
        cur = []
        i = 0
        n = len(text)
        while i < n:
            c = text[i]
            if c == '\\':
                if i + 1 < n:
                    r = try_escape(text, i + 1)
                    if r is not None:
                        ch, j, numeric = r
                        if numeric and ch in '&\\':
                            node = [''.join(cur), -1, repl_type]
                            nodes.append(node)
                            cur = []
                            repl_type &= ~REPL_MODIFIERS
                            node[0] += ch
                        else:
                            cur.append(ch)
                        i = j
                        continue
                node = [''.join(cur), -1, repl_type]
                nodes.append(node)
                cur = []
                repl_type &= ~REPL_MODIFIERS
                i += 1
                if i >= n:
                    node[0] += '\\'
                    break
                d = text[i]
                if d in '0123456789':
                    node[1] = int(d)
                elif d == 'L':
                    repl_type = REPL_LOWERCASE
                elif d == 'U':
                    repl_type = REPL_UPPERCASE
                elif d == 'E':
                    repl_type = REPL_ASIS
                elif d == 'l':
                    repl_type |= REPL_LOWERCASE_FIRST
                elif d == 'u':
                    repl_type |= REPL_UPPERCASE_FIRST
                else:
                    node[0] += d
                i += 1
            elif c == '&':
                node = [''.join(cur), 0, repl_type]
                nodes.append(node)
                cur = []
                repl_type &= ~REPL_MODIFIERS
                i += 1
            else:
                cur.append(c)
                i += 1
        if cur:
            nodes.append([''.join(cur), -1, repl_type])
        return [tuple(x) for x in nodes]

    def parse_y_part(self, text):
        out = []
        i = 0
        n = len(text)
        while i < n:
            c = text[i]
            if c == '\\' and i + 1 < n:
                d = text[i + 1]
                if d == '\\':
                    out.append('\\')
                    i += 2
                    continue
                r = try_escape(text, i + 1)
                if r is not None:
                    out.append(r[0])
                    i = r[1]
                    continue
                self.error("unknown option to `y'")
            out.append(c)
            i += 1
        return out

    def parse(self):
        cmds = []
        blocks = []
        quiet = False
        s = self.s
        if s.startswith('#n') and (len(s) == 2 or s[2] == '\n'):
            quiet = True
        while True:
            ch = self.getc()
            while ch is not EOF and (ch == ';' or ch in ' \t\n\r\v\f'):
                ch = self.getc()
            if ch is EOF:
                break
            cmd = Cmd()
            a = self.compile_address(ch)
            if a is not None:
                if a.kind in ('plus', 'mult'):
                    self.error("unexpected `,'")
                cmd.a1 = a
                ch = self.in_nonblank()
                if ch == ',':
                    ch = self.in_nonblank()
                    a2 = self.compile_address(ch)
                    if a2 is None:
                        self.error("unexpected `,'")
                    if a2.kind == 'step':
                        a2 = Addr('num', a2.n1)
                    cmd.a2 = a2
                    ch = self.in_nonblank()
                if cmd.a1.kind == 'num' and cmd.a1.n1 == 0:
                    if cmd.a2 is None or cmd.a2.kind != 're':
                        self.error("invalid usage of line address 0")
                    cmd.a1 = Addr('zero')
                if cmd.a2 is not None and cmd.a2.kind == 'num' \
                        and cmd.a2.n1 == 0:
                    self.error("invalid usage of line address 0")
            if ch == '!':
                cmd.negate = True
                ch = self.in_nonblank()
                while ch is not EOF and ch in ' \t':
                    ch = self.getc()
                if ch == '!':
                    self.error("multiple `!'s")
            if ch is EOF or ch == '\n':
                self.error("missing command")
            cmd.name = ch
            cmd.reset_range()
            if ch == '#':
                if cmd.a1 is not None:
                    self.error("comments don't accept any addresses")
                while True:
                    c = self.getc()
                    if c is EOF or c == '\n':
                        break
                continue
            elif ch == '{':
                blocks.append(len(cmds))
                cmds.append(cmd)
                continue
            elif ch == '}':
                if not blocks:
                    self.error("unexpected `}'")
                if cmd.a1 is not None:
                    self.error("} doesn't want any addresses")
                start = blocks.pop()
                cmds[start].block_end = len(cmds)
                cmds.append(cmd)
                self.read_end_of_cmd()
                continue
            elif ch in 'aic':
                cmd.text = self.read_text()
            elif ch == ':':
                if cmd.a1 is not None:
                    self.error(": doesn't want any addresses")
                label = self.read_label()
                if not label:
                    self.error("\":\" lacks a label")
                cmd.label = label
            elif ch in 'btT':
                cmd.label = self.read_label()
            elif ch in 'qQl':
                c = self.in_nonblank()
                if c is not EOF and c.isdigit():
                    cmd.int_arg = self.in_integer(c)
                else:
                    cmd.int_arg = -1
                    if c is not EOF:
                        self.ungetc()
                    else:
                        self.i -= 1
                self.read_end_of_cmd()
            elif ch in '=dDgGhHnNpPxzF':
                self.read_end_of_cmd()
            elif ch == 'v':
                self.read_label()
            elif ch == 's':
                slash = self.getc()
                if slash is EOF or slash == '\n' or slash == '\\':
                    self.error("unterminated `s' command")
                pat = self.match_slash(slash, True)
                if pat is None:
                    self.error("unterminated `s' command")
                rep = self.match_slash(slash, False)
                if rep is None:
                    self.error("unterminated `s' command")
                icase = mline = False
                while True:
                    c = self.getc()
                    if c in ('i', 'I'):
                        icase = True
                    elif c in ('m', 'M'):
                        mline = True
                    elif c == 'p':
                        cmd.sprint += 1
                    elif c == 'g':
                        cmd.glob = True
                    elif c is not EOF and c.isdigit():
                        v = self.in_integer(c)
                        if v == 0:
                            self.error("number option to `s' command may not be zero")
                        cmd.numb = v
                    elif c == '}' or c == '#':
                        self.ungetc()
                        break
                    elif c is EOF or c == '\n' or c == ';':
                        break
                    elif c in ' \t\r':
                        continue
                    elif c == 'e':
                        self.error("the `e' flag is not supported")
                    elif c == 'w':
                        self.error("the `w' flag is not supported")
                    else:
                        self.error("unknown option to `s'")
                cmd.regex = self.make_regex(pat, icase, mline)
                cmd.repl = self.setup_replacement(rep)
                if cmd.regex is not EMPTY_REGEX:
                    for node in cmd.repl:
                        if node[1] > cmd.regex.ngroups:
                            self.error("invalid reference \\%d on `s' command's RHS" % node[1])
            elif ch == 'y':
                slash = self.getc()
                if slash is EOF or slash == '\n' or slash == '\\':
                    self.error("unterminated `y' command")
                src = self.match_slash(slash, False)
                if src is None:
                    self.error("unterminated `y' command")
                dst = self.match_slash(slash, False)
                if dst is None:
                    self.error("unterminated `y' command")
                a = self.parse_y_part(src)
                b = self.parse_y_part(dst)
                if len(a) != len(b):
                    self.error("strings for `y' command are different lengths")
                m = {}
                for x, y in zip(a, b):
                    if x not in m:
                        m[x] = y
                cmd.ymap = {ord(k): v for k, v in m.items()}
                self.read_end_of_cmd()
            else:
                self.error("unknown command: `%s'" % ch)
            cmds.append(cmd)
        if blocks:
            self.i = self.n
            self.error("unmatched `{'")
        # resolve labels
        labels = {}
        for idx, c in enumerate(cmds):
            if c.name == ':':
                if c.label in labels:
                    raise SedError("-e expression #1, char 0: duplicate label `%s'" % c.label)
                labels[c.label] = idx
        for c in cmds:
            if c.name in 'btT':
                if c.label == '':
                    c.target = None
                elif c.label in labels:
                    c.target = labels[c.label]
                else:
                    raise SedError("-e expression #1, char 0: can't find label for jump to `%s'" % c.label)
        return cmds, quiet


# ---------------------------------------------------------------------------
# Input and output
# ---------------------------------------------------------------------------

class Output(object):
    def __init__(self):
        self.buf = []
        self.missing_newline = False
        self.out = sys.stdout.buffer

    def _missing(self):
        if self.missing_newline:
            self.buf.append('\n')
            self.missing_newline = False

    def pattern(self, text, add_nl, delim='\n'):
        self._missing()
        self.buf.append(text)
        if add_nl:
            self.buf.append(delim)
        else:
            self.missing_newline = True
        if len(self.buf) > 512:
            self.flush()

    def raw(self, text):
        self._missing()
        self.buf.append(text)
        if len(self.buf) > 512:
            self.flush()

    def flush(self):
        if self.buf:
            data = ''.join(self.buf).encode('latin-1')
            self.buf = []
            try:
                self.out.write(data)
            except BrokenPipeError:
                pass
        try:
            self.out.flush()
        except BrokenPipeError:
            pass


class Input(object):
    def __init__(self, files, separate, delim, output):
        self.files = list(files)
        self.fidx = 0
        self.separate = separate
        self.delim = delim
        self.lines = []
        self.pos = 0
        self.bad = False
        self.line_number = 0
        self.cur_name = '-'
        self.output = output
        self.have_file = False

    def _load(self, name):
        """Return list of (text, chomped) or None if unreadable."""
        try:
            if name == '-':
                data = sys.stdin.buffer.read()
            else:
                if os.path.isdir(name):
                    self.output.flush()
                    sys.stderr.write("sed: couldn't edit %s: not a regular file\n" % name
                                     if False else
                                     "sed: read error on %s: Is a directory\n" % name)
                    raise SystemExit(4)
                with open(name, 'rb') as f:
                    data = f.read()
        except SystemExit:
            raise
        except OSError as e:
            msg = e.strerror or str(e)
            sys.stderr.write("sed: can't read %s: %s\n" % (name, msg))
            self.bad = True
            return None
        text = data.decode('latin-1')
        if not text:
            return []
        parts = text.split(self.delim)
        if parts[-1] == '':
            parts.pop()
            return [(p, True) for p in parts]
        res = [(p, True) for p in parts[:-1]]
        res.append((parts[-1], False))
        return res

    def _open_next(self):
        """Open the next file.  Returns False if no more files."""
        if self.fidx >= len(self.files):
            return False
        name = self.files[self.fidx]
        self.fidx += 1
        lines = self._load(name)
        self.lines = lines if lines is not None else []
        self.pos = 0
        self.cur_name = name
        self.new_file = True
        return True

    def read_line(self, cmds=None):
        while self.pos >= len(self.lines):
            if not self._open_next():
                return None
            if self.separate:
                self.line_number = 0
                if cmds is not None:
                    for c in cmds:
                        c.reset_range()
        r = self.lines[self.pos]
        self.pos += 1
        self.line_number += 1
        return r

    def at_eof(self):
        """True if there is no next line (for n/N and the `$' address)."""
        if self.pos < len(self.lines):
            return False
        if self.separate:
            return True
        while self.fidx < len(self.files):
            self._open_next()
            if self.lines:
                return False
        return True

    def is_last(self):
        return self.at_eof()


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------

ACT_END, ACT_DELETE, ACT_RESTART, ACT_QUIT, ACT_QUIT_SILENT, ACT_EOF_QUIT = \
    range(6)


class Sed(object):
    def __init__(self, cmds, quiet, files, separate, zero, line_len):
        self.cmds = cmds
        self.quiet = quiet
        self.delim = '\0' if zero else '\n'
        self.out = Output()
        self.inp = Input(files, separate, self.delim, self.out)
        self.line_len = line_len
        self.ps = ''
        self.hs = ''
        self.chomped = True
        self.replaced = False
        self.appends = []
        self.last_regex = None
        self.separate = separate

    # -- regex helpers --
    def resolve(self, rx):
        if rx is EMPTY_REGEX:
            if self.last_regex is None:
                raise SedError("no previous regular expression")
            return self.last_regex
        self.last_regex = rx
        return rx

    def re_match(self, rx):
        rx = self.resolve(rx)
        return rx.search(self.ps, 0, True) is not None

    # -- addresses --
    def match_one(self, a):
        k = a.kind
        ln = self.inp.line_number
        if k == 'num':
            return ln == a.n1
        if k == 'step':
            if a.n2 <= 0:
                return ln == a.n1
            if ln < a.n1:
                return False
            return (ln - a.n1) % a.n2 == 0
        if k == 'last':
            return self.inp.is_last()
        if k == 're':
            return self.re_match(a.regex)
        if k == 'zero':
            return False
        return False

    def match_address(self, cmd):
        if cmd.a1 is None:
            return True
        if cmd.a2 is None:
            return self.match_one(cmd.a1)
        ln = self.inp.line_number
        a2 = cmd.a2
        if cmd.range_state == RANGE_ACTIVE:
            if a2.kind in ('num', 'plus', 'mult'):
                end = cmd.range_end
                if ln >= end:
                    cmd.range_state = RANGE_CLOSED
                return ln <= end
            if self.match_one(a2):
                cmd.range_state = RANGE_CLOSED
            return True
        if not self.match_one(cmd.a1):
            return False
        if a2.kind == 'num':
            if a2.n1 <= ln:
                cmd.range_state = RANGE_CLOSED
                return True
            cmd.range_end = a2.n1
        elif a2.kind == 'plus':
            if a2.n1 == 0:
                cmd.range_state = RANGE_CLOSED
                return True
            cmd.range_end = ln + a2.n1
        elif a2.kind == 'mult':
            if a2.n1 <= 0 or ln % a2.n1 == 0:
                cmd.range_state = RANGE_CLOSED
                return True
            cmd.range_end = (ln // a2.n1 + 1) * a2.n1
        cmd.range_state = RANGE_ACTIVE
        return True

    # -- output helpers --
    def dump_append(self):
        for t in self.appends:
            self.out.raw(t)
        self.appends = []

    def autoprint(self):
        if not self.quiet:
            self.out.pattern(self.ps, self.chomped, self.delim)

    def do_list(self, line_len):
        out = []
        width = 0
        obuf = []
        for c in self.ps:
            o = ord(c)
            if c == '\\':
                e = '\\\\'
            elif 32 <= o < 127:
                e = c
            elif c == '\a':
                e = '\\a'
            elif c == '\b':
                e = '\\b'
            elif c == '\f':
                e = '\\f'
            elif c == '\n':
                e = '\\n'
            elif c == '\r':
                e = '\\r'
            elif c == '\t':
                e = '\\t'
            elif c == '\v':
                e = '\\v'
            else:
                e = '\\%03o' % o
            if line_len > 1 and width + len(e) > line_len - 1:
                obuf.append('\\\n')
                width = 0
            obuf.append(e)
            width += len(e)
        obuf.append('$\n')
        self.out.raw(''.join(obuf))

    def do_subst(self, cmd):
        rx = self.resolve(cmd.regex)
        s = self.ps
        n = len(s)
        start = 0
        last_end = -1
        count = 0
        out = []
        did = False
        tail_done = False
        while start <= n:
            caps = rx.search(s, start)
            if caps is None:
                break
            ms, me = caps[0], caps[1]
            if ms == me and ms == last_end:
                if ms >= n:
                    break
                out.append(s[start:ms + 1])
                start = ms + 1
                continue
            out.append(s[start:ms])
            count += 1
            if count < cmd.numb:
                out.append(s[ms:me])
            else:
                did = True
                self.append_replacement(out, cmd.repl, s, caps)
                if not cmd.glob:
                    out.append(s[me:])
                    tail_done = True
                    break
            last_end = me
            if ms == me:
                if ms < n:
                    out.append(s[ms])
                start = me + 1
            else:
                start = me
        if not did:
            return
        if not tail_done and start <= n:
            out.append(s[start:])
        self.ps = ''.join(out)
        self.replaced = True
        if cmd.sprint:
            for _ in range(cmd.sprint):
                self.out.pattern(self.ps, self.chomped, self.delim)

    @staticmethod
    def str_append_modified(out, text, typ):
        if typ == REPL_ASIS:
            out.append(text)
            return
        if not text:
            return
        if typ & REPL_UPPERCASE_FIRST:
            out.append(a_upper(text[0]))
            text = text[1:]
        elif typ & REPL_LOWERCASE_FIRST:
            out.append(a_lower(text[0]))
            text = text[1:]
        if not text:
            return
        typ &= ~REPL_MODIFIERS
        if typ == REPL_UPPERCASE:
            out.append(a_upper(text))
        elif typ == REPL_LOWERCASE:
            out.append(a_lower(text))
        else:
            out.append(text)

    def append_replacement(self, out, repl, s, caps):
        repl_mask = 0
        nslots = len(caps)
        for prefix, sid, rtype in repl:
            if rtype & REPL_MODIFIERS:
                curr = rtype
            else:
                curr = rtype | repl_mask
            repl_mask = 0
            if prefix:
                self.str_append_modified(out, prefix, curr)
                curr &= ~REPL_MODIFIERS
            if sid >= 0:
                if 2 * sid + 1 < nslots:
                    a, b = caps[2 * sid], caps[2 * sid + 1]
                else:
                    a = b = -1
                if a < 0 or b < 0:
                    a = b = 0
                if a == b and (rtype & REPL_MODIFIERS):
                    repl_mask = curr & REPL_MODIFIERS
                elif a != b:
                    self.str_append_modified(out, s[a:b], curr)

    def read_next(self):
        r = self.inp.read_line(self.cmds if self.separate else None)
        if r is None:
            return False
        self.ps, self.chomped = r
        self.replaced = False
        return True

    def execute(self):
        cmds = self.cmds
        ncmds = len(cmds)
        pc = 0
        while pc < ncmds:
            cmd = cmds[pc]
            if cmd.a1 is not None or cmd.negate:
                if self.match_address(cmd) == cmd.negate:
                    if cmd.name == '{':
                        pc = cmd.block_end + 1
                    else:
                        pc += 1
                    continue
            name = cmd.name
            if name == '{' or name == '}' or name == ':' or name == 'v':
                pass
            elif name == 's':
                self.do_subst(cmd)
            elif name == 'p':
                self.out.pattern(self.ps, self.chomped, self.delim)
            elif name == 'd':
                return ACT_DELETE, 0
            elif name == 'D':
                k = self.ps.find(self.delim)
                if k < 0:
                    return ACT_DELETE, 0
                self.ps = self.ps[k + 1:]
                return ACT_RESTART, 0
            elif name == 'b':
                if cmd.target is None:
                    return ACT_END, 0
                pc = cmd.target
                continue
            elif name == 't':
                if self.replaced:
                    self.replaced = False
                    if cmd.target is None:
                        return ACT_END, 0
                    pc = cmd.target
                    continue
            elif name == 'T':
                if not self.replaced:
                    if cmd.target is None:
                        return ACT_END, 0
                    pc = cmd.target
                    continue
                self.replaced = False
            elif name == 'h':
                self.hs = self.ps
            elif name == 'H':
                self.hs = self.hs + self.delim + self.ps
            elif name == 'g':
                self.ps = self.hs
            elif name == 'G':
                self.ps = self.ps + self.delim + self.hs
            elif name == 'x':
                self.ps, self.hs = self.hs, self.ps
            elif name == 'n':
                if self.inp.at_eof():
                    return ACT_EOF_QUIT, 0
                self.autoprint()
                self.dump_append()
                self.read_next()
            elif name == 'N':
                if self.inp.at_eof():
                    return ACT_EOF_QUIT, 0
                self.dump_append()
                ps = self.ps
                self.read_next()
                self.ps = ps + self.delim + self.ps
            elif name == 'P':
                k = self.ps.find(self.delim)
                if k >= 0:
                    self.out.pattern(self.ps[:k], True, self.delim)
                else:
                    self.out.pattern(self.ps, self.chomped, self.delim)
            elif name == '=':
                self.out.raw('%d\n' % self.inp.line_number)
            elif name == 'a':
                self.appends.append(cmd.text)
            elif name == 'i':
                self.out.raw(cmd.text)
            elif name == 'c':
                if cmd.a2 is None or cmd.range_state != RANGE_ACTIVE:
                    self.out.raw(cmd.text)
                return ACT_DELETE, 0
            elif name == 'l':
                ll = self.line_len if cmd.int_arg == -1 else cmd.int_arg
                self.do_list(ll)
            elif name == 'q':
                return ACT_QUIT, (cmd.int_arg if cmd.int_arg >= 0 else 0)
            elif name == 'Q':
                return ACT_QUIT_SILENT, (cmd.int_arg if cmd.int_arg >= 0 else 0)
            elif name == 'y':
                self.ps = self.ps.translate(cmd.ymap)
            elif name == 'z':
                self.ps = ''
            elif name == 'F':
                self.out.raw('%s\n' % self.inp.cur_name)
            pc += 1
        return ACT_END, 0

    def run(self):
        restart = False
        try:
            while True:
                if not restart:
                    if not self.read_next():
                        break
                    self.replaced = False
                restart = False
                act, code = self.execute()
                if act == ACT_END:
                    self.autoprint()
                    self.dump_append()
                elif act == ACT_DELETE:
                    self.dump_append()
                elif act == ACT_RESTART:
                    self.dump_append()
                    restart = True
                elif act == ACT_QUIT:
                    self.autoprint()
                    self.dump_append()
                    return code
                elif act == ACT_QUIT_SILENT:
                    return code
                elif act == ACT_EOF_QUIT:
                    self.autoprint()
                    self.dump_append()
            return 2 if self.inp.bad else 0
        finally:
            self.out.flush()


# ---------------------------------------------------------------------------
# Command line
# ---------------------------------------------------------------------------

USAGE = """\
Usage: sed [OPTION]... {script-only-if-no-other-script} [input-file]...

  -n, --quiet, --silent
                 suppress automatic printing of pattern space
      --debug
                 annotate program execution
  -e script, --expression=script
                 add the script to the commands to be executed
  -f script-file, --file=script-file
                 add the contents of script-file to the commands to be executed
  --follow-symlinks
                 follow symlinks when processing in place
  -i[SUFFIX], --in-place[=SUFFIX]
                 edit files in place (makes backup if SUFFIX supplied)
  -l N, --line-length=N
                 specify the desired line-wrap length for the `l' command
  --posix
                 disable all GNU extensions.
  -E, -r, --regexp-extended
                 use extended regular expressions in the script
                 (for portability use POSIX -E).
  -s, --separate
                 consider files as separate rather than as a single
                 continuous long stream.
      --sandbox
                 operate in sandbox mode (disable e/r/w commands).
  -u, --unbuffered
                 load minimal amounts of data from the input files and flush
                 the output buffers more often
  -z, --null-data
                 separate lines by NUL characters
      --help     display this help and exit
      --version  output version information and exit

If no -e, --expression, -f, or --file option is given, then the first
non-option argument is taken as the sed script to interpret.  All
remaining arguments are names of input files; if no input files are
specified, then the standard input is read.

GNU sed home page: <https://www.gnu.org/software/sed/>.
General help using GNU software: <https://www.gnu.org/gethelp/>.
E-mail bug reports to: <bug-sed@gnu.org>.
"""

VERSION = """\
sed (GNU sed) 4.9
Copyright (C) 2022 Free Software Foundation, Inc.
License GPLv3+: GNU GPL version 3 or later <https://gnu.org/licenses/gpl.html>.
This is free software: you are free to change and redistribute it.
There is NO WARRANTY, to the extent permitted by law.

Written by Jay Fenlason, Tom Lord, Ken Pizzini,
Paolo Bonzini, Jim Meyering, and Assaf Gordon.

This sed program was built without SELinux support.

GNU sed home page: <https://www.gnu.org/software/sed/>.
General help using GNU software: <https://www.gnu.org/gethelp/>.
E-mail bug reports to: <bug-sed@gnu.org>.
"""

LONG_OPTS = {
    # name: (takes_arg, key)  takes_arg: 0 none, 1 required, 2 optional
    'quiet': (0, 'n'), 'silent': (0, 'n'),
    'regexp-extended': (0, 'E'),
    'separate': (0, 's'),
    'expression': (1, 'e'),
    'file': (1, 'f'),
    'line-length': (1, 'l'),
    'null-data': (0, 'z'), 'zero-terminated': (0, 'z'),
    'unbuffered': (0, 'u'),
    'binary': (0, 'b'),
    'posix': (0, 'posix'),
    'debug': (0, 'debug'),
    'sandbox': (0, 'sandbox'),
    'follow-symlinks': (0, 'follow'),
    'in-place': (2, 'i'),
    'help': (0, 'help'),
    'version': (0, 'version'),
}

SHORT_NOARG = set('nrEsuzb')
SHORT_ARG = set('efl')


def usage_error(msg=None):
    if msg:
        sys.stderr.write("sed: %s\n" % msg)
    sys.stderr.write(USAGE)
    return 1


def main(argv):
    opts = []
    nonopts = []
    i = 0
    while i < len(argv):
        a = argv[i]
        i += 1
        if a == '--':
            nonopts.extend(argv[i:])
            break
        if a.startswith('--'):
            body = a[2:]
            if '=' in body:
                name, val = body.split('=', 1)
                has_val = True
            else:
                name, val, has_val = body, None, False
            if name in LONG_OPTS:
                matches = [name]
            else:
                matches = [k for k in LONG_OPTS if k.startswith(name)]
                keys = set(LONG_OPTS[k][1] for k in matches)
                if len(keys) == 1:
                    matches = matches[:1]
            if len(matches) != 1:
                if not matches:
                    sys.stderr.write("sed: unrecognized option '%s'\n" % a)
                else:
                    sys.stderr.write("sed: option '%s' is ambiguous\n" % a)
                sys.stderr.write(USAGE)
                return 1
            takes, key = LONG_OPTS[matches[0]]
            if takes == 1 and not has_val:
                if i >= len(argv):
                    sys.stderr.write("sed: option '%s' requires an argument\n" % a)
                    sys.stderr.write(USAGE)
                    return 1
                val = argv[i]
                i += 1
            elif takes == 0 and has_val:
                sys.stderr.write("sed: option '--%s' doesn't allow an argument\n" % matches[0])
                sys.stderr.write(USAGE)
                return 1
            opts.append((key, val))
            continue
        if a.startswith('-') and len(a) > 1:
            j = 1
            while j < len(a):
                c = a[j]
                j += 1
                if c in SHORT_NOARG:
                    opts.append((c, None))
                elif c in SHORT_ARG:
                    if j < len(a):
                        val = a[j:]
                    else:
                        if i >= len(argv):
                            sys.stderr.write("sed: option requires an argument -- '%s'\n" % c)
                            sys.stderr.write(USAGE)
                            return 1
                        val = argv[i]
                        i += 1
                    opts.append((c, val))
                    break
                elif c == 'i':
                    opts.append(('i', a[j:] if j < len(a) else None))
                    break
                else:
                    sys.stderr.write("sed: invalid option -- '%s'\n" % c)
                    sys.stderr.write(USAGE)
                    return 1
            continue
        nonopts.append(a)

    quiet = False
    ere = False
    separate = False
    zero = False
    line_len = 70
    script_parts = []
    have_script = False
    for key, val in opts:
        if key == 'n':
            quiet = True
        elif key in ('E', 'r'):
            ere = True
        elif key == 's':
            separate = True
        elif key == 'z':
            zero = True
        elif key == 'e':
            script_parts.append(val)
            have_script = True
        elif key == 'f':
            try:
                if val == '-':
                    data = sys.stdin.buffer.read()
                else:
                    with open(val, 'rb') as f:
                        data = f.read()
            except OSError as e:
                sys.stderr.write("sed: couldn't open file %s: %s\n" % (val, e.strerror))
                return 1
            t = data.decode('latin-1')
            if t.endswith('\n'):
                t = t[:-1]
            script_parts.append(t)
            have_script = True
        elif key == 'l':
            try:
                line_len = int(val)
            except ValueError:
                sys.stderr.write("sed: invalid line length: %s\n" % val)
                return 1
        elif key == 'i':
            sys.stderr.write("sed: in-place editing is not supported\n")
            return 1
        elif key == 'help':
            sys.stdout.write(USAGE)
            sys.stdout.flush()
            return 0
        elif key == 'version':
            sys.stdout.write(VERSION)
            sys.stdout.flush()
            return 0
    if not have_script:
        if not nonopts:
            return usage_error()
        script_parts.append(nonopts.pop(0))
    script = '\n'.join(script_parts)
    files = nonopts if nonopts else ['-']

    try:
        parser = ScriptParser(script, ere)
        cmds, hash_n = parser.parse()
    except SedError as e:
        sys.stderr.write("sed: %s\n" % e.msg)
        return e.status
    if hash_n:
        quiet = True
    sed = Sed(cmds, quiet, files, separate, zero, line_len)
    try:
        return sed.run()
    except SedError as e:
        sys.stderr.write("sed: %s\n" % e.msg)
        return 4


if __name__ == "__main__":
    sys.setrecursionlimit(10000)
    try:
        code = main(sys.argv[1:])
    except KeyboardInterrupt:
        code = 130
    sys.exit(code)
