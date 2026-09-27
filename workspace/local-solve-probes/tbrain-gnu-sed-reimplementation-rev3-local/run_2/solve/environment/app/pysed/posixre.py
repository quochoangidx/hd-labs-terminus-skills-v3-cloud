"""A small POSIX (leftmost-longest) regular expression engine for pysed.

Supports GNU BRE and ERE syntax as used by GNU sed 4.9 (without
back-references inside the pattern).  Strings are Python str objects whose
characters are bytes (latin-1 decoded).
"""

ALL = frozenset(chr(i) for i in range(256))


def _cls(pred):
    return frozenset(c for c in ALL if pred(ord(c)))


CLASSES = {
    'alpha': _cls(lambda o: 65 <= o <= 90 or 97 <= o <= 122),
    'digit': _cls(lambda o: 48 <= o <= 57),
    'alnum': _cls(lambda o: 65 <= o <= 90 or 97 <= o <= 122 or 48 <= o <= 57),
    'upper': _cls(lambda o: 65 <= o <= 90),
    'lower': _cls(lambda o: 97 <= o <= 122),
    'space': _cls(lambda o: o in (32, 9, 10, 11, 12, 13)),
    'blank': _cls(lambda o: o in (32, 9)),
    'punct': _cls(lambda o: 33 <= o <= 47 or 58 <= o <= 64 or 91 <= o <= 96 or 123 <= o <= 126),
    'print': _cls(lambda o: 32 <= o <= 126),
    'graph': _cls(lambda o: 33 <= o <= 126),
    'cntrl': _cls(lambda o: o < 32 or o == 127),
    'xdigit': _cls(lambda o: 48 <= o <= 57 or 65 <= o <= 70 or 97 <= o <= 102),
}
WORD = CLASSES['alnum'] | frozenset('_')
NONWORD = ALL - WORD
SPACE = CLASSES['space']
NONSPACE = ALL - SPACE

SIMPLE_ESC = {'a': '\a', 'f': '\f', 'n': '\n', 'r': '\r', 't': '\t', 'v': '\v'}


class RegexError(Exception):
    pass


# AST nodes (tuples):
#  ('lit', ch) ('set', frozenset) ('any',) ('cat', [nodes]) ('alt', [nodes])
#  ('group', idx, node) ('rep', node, min, max) ('assert', kind) ('empty',)

class Parser:
    def __init__(self, pat, ere):
        self.p = pat
        self.i = 0
        self.ere = ere
        self.ngroups = 0

    def peek(self, k=0):
        j = self.i + k
        if j < len(self.p):
            return self.p[j]
        return None

    def at_alt(self):
        if self.ere:
            return self.peek() == '|'
        return self.peek() == '\\' and self.peek(1) == '|'

    def at_close(self, depth):
        if depth == 0:
            return False
        if self.ere:
            return self.peek() == ')'
        return self.peek() == '\\' and self.peek(1) == ')'

    def parse(self):
        node = self.parse_alt(0)
        if self.i < len(self.p):
            # stray close paren etc.: treat rest literally
            rest = []
            while self.i < len(self.p):
                rest.append(('lit', self.p[self.i]))
                self.i += 1
            node = ('cat', [node] + rest)
        return node

    def parse_alt(self, depth):
        branches = [self.parse_concat(depth)]
        while self.at_alt():
            self.i += 1 if self.ere else 2
            branches.append(self.parse_concat(depth))
        if len(branches) == 1:
            return branches[0]
        return ('alt', branches)

    def parse_concat(self, depth):
        items = []
        start = True
        while self.i < len(self.p):
            if self.at_alt() or self.at_close(depth):
                break
            c = self.p[self.i]
            atom = None
            if c == '^':
                if self.ere or start:
                    self.i += 1
                    items.append(('assert', 'bol'))
                    # '*' after a leading '^' is literal in BRE
                    continue
                self.i += 1
                atom = ('lit', '^')
            elif c == '$':
                self.i += 1
                if self.ere:
                    items.append(('assert', 'eol'))
                    start = False
                    continue
                if (self.i >= len(self.p) or self.at_alt() or
                        (depth > 0 and self.at_close(depth))):
                    items.append(('assert', 'eol'))
                    start = False
                    continue
                atom = ('lit', '$')
            elif c == '*' and start:
                self.i += 1
                atom = ('lit', '*')
            elif self.ere and c in '+?' and start:
                self.i += 1
                atom = ('lit', c)
            elif self.ere and c == '{' and start:
                self.i += 1
                atom = ('lit', c)
            elif c == '.':
                self.i += 1
                atom = ('any',)
            elif c == '[':
                atom = self.parse_bracket()
            elif self.ere and c == '(':
                self.i += 1
                self.ngroups += 1
                idx = self.ngroups
                inner = self.parse_alt(depth + 1)
                if self.peek() == ')':
                    self.i += 1
                atom = ('group', idx, inner)
            elif self.ere and c == ')':
                # unmatched ) at top level: literal
                self.i += 1
                atom = ('lit', ')')
            elif c == '\\':
                n = self.peek(1)
                if n is None:
                    self.i += 1
                    atom = ('lit', '\\')
                elif not self.ere and n == '(':
                    self.i += 2
                    self.ngroups += 1
                    idx = self.ngroups
                    inner = self.parse_alt(depth + 1)
                    if self.peek() == '\\' and self.peek(1) == ')':
                        self.i += 2
                    atom = ('group', idx, inner)
                elif not self.ere and n == '{' and start:
                    self.i += 2
                    atom = ('lit', '{')
                else:
                    self.i += 2
                    if n in SIMPLE_ESC:
                        atom = ('lit', SIMPLE_ESC[n])
                    elif n == 'w':
                        atom = ('set', WORD)
                    elif n == 'W':
                        atom = ('set', NONWORD)
                    elif n == 's':
                        atom = ('set', SPACE)
                    elif n == 'S':
                        atom = ('set', NONSPACE)
                    elif n == 'b':
                        items.append(('assert', 'wordb'))
                        start = False
                        continue
                    elif n == 'B':
                        items.append(('assert', 'nwordb'))
                        start = False
                        continue
                    elif n == '<':
                        items.append(('assert', 'wbeg'))
                        start = False
                        continue
                    elif n == '>':
                        items.append(('assert', 'wend'))
                        start = False
                        continue
                    elif n == '`':
                        items.append(('assert', 'bos'))
                        start = False
                        continue
                    elif n == "'":
                        items.append(('assert', 'eos'))
                        start = False
                        continue
                    else:
                        atom = ('lit', n)
            else:
                self.i += 1
                atom = ('lit', c)
            start = False
            atom = self.parse_quantifiers(atom)
            items.append(atom)
        if not items:
            return ('empty',)
        if len(items) == 1:
            return items[0]
        return ('cat', items)

    def try_interval(self, j):
        """Parse an interval body starting at index j (just after '{').
        Returns (min, max, newindex) or None."""
        p = self.p
        k = j
        m = ''
        while k < len(p) and p[k].isdigit():
            m += p[k]
            k += 1
        mx = None
        comma = False
        if k < len(p) and p[k] == ',':
            comma = True
            k += 1
            s = ''
            while k < len(p) and p[k].isdigit():
                s += p[k]
                k += 1
            if s:
                mx = int(s)
        if self.ere:
            if k < len(p) and p[k] == '}':
                k += 1
            else:
                return None
        else:
            if k + 1 < len(p) and p[k] == '\\' and p[k + 1] == '}':
                k += 2
            else:
                return None
        if not m and not comma:
            return None
        mn = int(m) if m else 0
        if not comma:
            mx = mn
        return mn, mx, k

    def parse_quantifiers(self, atom):
        while self.i < len(self.p):
            c = self.p[self.i]
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
                r = self.try_interval(self.i + 1)
                if r is None:
                    break
                mn, mx, self.i = r
                atom = ('rep', atom, mn, mx)
            elif not self.ere and c == '\\' and self.peek(1) in ('+', '?', '{'):
                n = self.peek(1)
                if n == '+':
                    self.i += 2
                    atom = ('rep', atom, 1, None)
                elif n == '?':
                    self.i += 2
                    atom = ('rep', atom, 0, 1)
                else:
                    r = self.try_interval(self.i + 2)
                    if r is None:
                        break
                    mn, mx, self.i = r
                    atom = ('rep', atom, mn, mx)
            else:
                break
        return atom

    def parse_bracket(self):
        p = self.p
        i = self.i + 1
        neg = False
        if i < len(p) and p[i] == '^':
            neg = True
            i += 1
        chars = set()
        first = True
        prev_char = None  # last single char added (for ranges)
        while i < len(p):
            c = p[i]
            if c == ']' and not first:
                i += 1
                break
            first = False
            if c == '[' and i + 1 < len(p) and p[i + 1] in ':.=':
                kind = p[i + 1]
                end = p.find(kind + ']', i + 2)
                if end >= 0:
                    name = p[i + 2:end]
                    i = end + 2
                    if kind == ':':
                        chars |= CLASSES.get(name, frozenset())
                    else:
                        chars |= set(name)
                    prev_char = None
                    continue
            # single char (possibly escape)
            ch, i = self._bracket_char(i)
            # range?
            if (i + 1 < len(p) and p[i] == '-' and p[i + 1] != ']'):
                hi, i2 = self._bracket_char(i + 1)
                lo_o, hi_o = ord(ch), ord(hi)
                for o in range(lo_o, hi_o + 1):
                    chars.add(chr(o))
                i = i2
                prev_char = None
                continue
            chars.add(ch)
            prev_char = ch
        self.i = i
        s = frozenset(chars)
        if neg:
            s = ALL - s
        return ('set', s)

    def _bracket_char(self, i):
        p = self.p
        c = p[i]
        if c == '\\' and i + 1 < len(p):
            n = p[i + 1]
            if n in SIMPLE_ESC:
                return SIMPLE_ESC[n], i + 2
            if n == '\\':
                return '\\', i + 2
            if n == ']':
                return '\\', i + 1
        return c, i + 1


# ---------------------------------------------------------------------------
# Compiler to a Pike VM program

CHAR, SET, ANY, SPLIT, JMP, SAVE, ASSERT, MATCH = range(8)


class Compiler:
    def __init__(self):
        self.prog = []

    def emit(self, *ins):
        self.prog.append(list(ins))
        return len(self.prog) - 1

    def comp(self, node):
        t = node[0]
        if t == 'lit':
            self.emit(CHAR, node[1])
        elif t == 'set':
            self.emit(SET, node[1])
        elif t == 'any':
            self.emit(ANY, None)
        elif t == 'empty':
            pass
        elif t == 'cat':
            for n in node[1]:
                self.comp(n)
        elif t == 'alt':
            branches = node[1]
            jumps = []
            for k, b in enumerate(branches):
                if k < len(branches) - 1:
                    sp = self.emit(SPLIT, None, None)
                    self.prog[sp][1] = sp + 1
                    self.comp(b)
                    jumps.append(self.emit(JMP, None))
                    self.prog[sp][2] = len(self.prog)
                else:
                    self.comp(b)
            for j in jumps:
                self.prog[j][1] = len(self.prog)
        elif t == 'group':
            idx = node[1]
            self.emit(SAVE, 2 * idx)
            self.comp(node[2])
            self.emit(SAVE, 2 * idx + 1)
        elif t == 'assert':
            self.emit(ASSERT, node[1])
        elif t == 'rep':
            sub, mn, mx = node[1], node[2], node[3]
            for _ in range(mn):
                self.comp(sub)
            if mx is None:
                sp = self.emit(SPLIT, None, None)
                self.prog[sp][1] = sp + 1
                self.comp(sub)
                self.emit(JMP, sp)
                self.prog[sp][2] = len(self.prog)
            else:
                splits = []
                for _ in range(mx - mn):
                    sp = self.emit(SPLIT, None, None)
                    self.prog[sp][1] = sp + 1
                    splits.append(sp)
                    self.comp(sub)
                for sp in splits:
                    self.prog[sp][2] = len(self.prog)
        else:
            raise RegexError('bad node %r' % (t,))


def _isword(c):
    return c in WORD


class Regex:
    def __init__(self, pattern, ere):
        parser = Parser(pattern, ere)
        ast = parser.parse()
        self.ngroups = parser.ngroups
        comp = Compiler()
        comp.comp(ast)
        comp.emit(MATCH, None)
        self.prog = [tuple(x) for x in comp.prog]
        self.pattern = pattern
        self.anchored = bool(self.prog) and self.prog[0][0] == ASSERT and self.prog[0][1] == 'bol'

    def _check(self, kind, s, i, n):
        if kind == 'bol' or kind == 'bos':
            return i == 0
        if kind == 'eol' or kind == 'eos':
            return i == n
        a = i > 0 and s[i - 1] in WORD
        b = i < n and s[i] in WORD
        if kind == 'wordb':
            return a != b
        if kind == 'nwordb':
            return a == b
        if kind == 'wbeg':
            return (not a) and b
        if kind == 'wend':
            return a and not b
        return False

    def _add(self, lst, visited, pc, caps, s, i, n):
        prog = self.prog
        stack = [(pc, caps)]
        while stack:
            pc, caps = stack.pop()
            if pc in visited:
                continue
            visited.add(pc)
            ins = prog[pc]
            op = ins[0]
            if op == JMP:
                stack.append((ins[1], caps))
            elif op == SPLIT:
                stack.append((ins[2], caps))
                stack.append((ins[1], caps))
            elif op == SAVE:
                c2 = list(caps)
                c2[ins[1]] = i
                stack.append((pc + 1, c2))
            elif op == ASSERT:
                if self._check(ins[1], s, i, n):
                    stack.append((pc + 1, caps))
            else:
                lst.append((pc, caps))

    def search(self, s, pos=0):
        """Return list of capture positions [s0,e0,s1,e1,...] for the
        leftmost-longest match starting at or after pos, or None."""
        n = len(s)
        prog = self.prog
        ncap = 2 * (self.ngroups + 1)
        best = None
        best_start = None
        clist = []
        i = pos
        if pos > n:
            return None
        base = [None] * ncap
        c0 = list(base)
        c0[0] = i
        self._add(clist, set(), 0, c0, s, i, n)
        anchored = self.anchored
        while True:
            nlist = []
            visited = set()
            ch = s[i] if i < n else None
            for pc, caps in clist:
                ins = prog[pc]
                op = ins[0]
                if op == MATCH:
                    st = caps[0]
                    if best is None or st < best_start or (st == best_start):
                        if best is None or st < best_start or i >= best[1]:
                            best = list(caps)
                            best[1] = i
                            best_start = st
                    continue
                if ch is None:
                    continue
                if best is not None and caps[0] > best_start:
                    continue
                if op == CHAR:
                    if ch == ins[1]:
                        self._add(nlist, visited, pc + 1, caps, s, i + 1, n)
                elif op == SET:
                    if ch in ins[1]:
                        self._add(nlist, visited, pc + 1, caps, s, i + 1, n)
                elif op == ANY:
                    self._add(nlist, visited, pc + 1, caps, s, i + 1, n)
            if i >= n:
                break
            i += 1
            if best is None and not anchored:
                c0 = list(base)
                c0[0] = i
                self._add(nlist, visited, 0, c0, s, i, n)
            elif best is not None:
                nlist = [t for t in nlist if t[1][0] <= best_start]
            if not nlist:
                if best is not None or anchored:
                    break
            clist = nlist
        return best


_cache = {}


def compile_regex(pattern, ere):
    key = (pattern, ere)
    r = _cache.get(key)
    if r is None:
        r = Regex(pattern, ere)
        _cache[key] = r
    return r
