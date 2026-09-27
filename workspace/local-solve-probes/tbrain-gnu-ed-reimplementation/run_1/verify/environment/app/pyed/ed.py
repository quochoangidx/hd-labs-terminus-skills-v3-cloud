"""pyed: a GNU ed 1.19 replacement in pure Python.

Usage: python3 /app/pyed/ed.py [OPTIONS] [FILE]
"""

import os
import stat
import sys

# ---------------------------------------------------------------------------
# POSIX regular expressions (glibc flavoured), leftmost-longest matching
# ---------------------------------------------------------------------------

RE_DUP_MAX = 0x7fff


class RegexError(Exception):
    pass


_CLASSES = {
    'alpha': lambda c: c.isascii() and c.isalpha(),
    'upper': lambda c: 'A' <= c <= 'Z',
    'lower': lambda c: 'a' <= c <= 'z',
    'digit': lambda c: '0' <= c <= '9',
    'xdigit': lambda c: c in '0123456789abcdefABCDEF',
    'space': lambda c: c in ' \t\n\r\f\v',
    'print': lambda c: 32 <= ord(c) <= 126,
    'punct': lambda c: 33 <= ord(c) <= 126 and not c.isalnum(),
    'graph': lambda c: 33 <= ord(c) <= 126,
    'cntrl': lambda c: ord(c) < 32 or ord(c) == 127,
    'blank': lambda c: c in ' \t',
    'alnum': lambda c: c.isascii() and c.isalnum(),
}

_ALLCHARS = [chr(i) for i in range(256)]

# token kinds
T_CHAR, T_SET, T_ANY, T_OPEN, T_CLOSE, T_ALT, T_STAR, T_PLUS, T_QUEST, \
    T_BRACE, T_CLOSEBRACE, T_BOL, T_EOL, T_BREF, T_END = range(15)


class _Parser:
    def __init__(self, pat, ere, icase):
        self.p = pat
        self.n = len(pat)
        self.ere = ere
        self.icase = icase
        self.i = 0
        self.ngroups = 0
        self.completed = set()
        self.depth = 0

    # -- tokenizer -------------------------------------------------------
    def peek(self, caret_ok):
        """Return (kind, value, length) of the token at self.i."""
        p, i, n = self.p, self.i, self.n
        if i >= n:
            return (T_END, None, 0)
        c = p[i]
        ere = self.ere
        if c == '\\':
            if i + 1 >= n:
                raise RegexError('Trailing backslash')
            d = p[i + 1]
            if d == '|':
                return (T_CHAR, '|', 2) if ere else (T_ALT, None, 2)
            if '1' <= d <= '9':
                return (T_BREF, int(d), 2)
            if not ere:
                if d == '(':
                    return (T_OPEN, None, 2)
                if d == ')':
                    return (T_CLOSE, None, 2)
                if d == '+':
                    return (T_PLUS, None, 2)
                if d == '?':
                    return (T_QUEST, None, 2)
                if d == '{':
                    return (T_BRACE, None, 2)
                if d == '}':
                    return (T_CLOSEBRACE, None, 2)
            return (T_CHAR, d, 2)
        if c == '[':
            return (T_SET, None, 1)
        if c == '.':
            return (T_ANY, None, 1)
        if c == '*':
            return (T_STAR, None, 1)
        if ere:
            if c == '|':
                return (T_ALT, None, 1)
            if c == '(':
                return (T_OPEN, None, 1)
            if c == ')':
                return (T_CLOSE, None, 1)
            if c == '+':
                return (T_PLUS, None, 1)
            if c == '?':
                return (T_QUEST, None, 1)
            if c == '{':
                return (T_BRACE, None, 1)
            if c == '^':
                return (T_BOL, None, 1)
            if c == '$':
                return (T_EOL, None, 1)
            return (T_CHAR, c, 1)
        if c == '^':
            if i == 0 or caret_ok:
                return (T_BOL, None, 1)
            return (T_CHAR, c, 1)
        if c == '$':
            if i + 1 == n:
                return (T_EOL, None, 1)
            if p[i + 1] == '\\' and i + 2 < n and p[i + 2] in ')|':
                return (T_EOL, None, 1)
            return (T_CHAR, c, 1)
        return (T_CHAR, c, 1)

    # -- grammar ---------------------------------------------------------
    def parse(self):
        node = self.parse_alt(True)
        if self.i < self.n:
            raise RegexError('Unmatched ) or \\)')
        return node

    def parse_alt(self, caret_ok):
        branches = [self.parse_branch(caret_ok)]
        while True:
            kind, val, ln = self.peek(False)
            if kind != T_ALT:
                break
            self.i += ln
            branches.append(self.parse_branch(True))
        if len(branches) == 1:
            return branches[0]
        return ('alt', branches)

    def parse_branch(self, caret_ok):
        items = []
        start = True
        while True:
            kind, val, ln = self.peek(caret_ok)
            if kind == T_END or kind == T_ALT:
                break
            if kind == T_CLOSE and self.depth > 0:
                break
            node, is_anchor = self.parse_expression(kind, val, ln, start)
            caret_ok = False
            items.append(node)
            start = is_anchor
        if len(items) == 1:
            return items[0]
        return ('cat', items)

    def parse_expression(self, kind, val, ln, start):
        ere = self.ere
        if kind == T_BOL or kind == T_EOL:
            self.i += ln
            return (('bol',) if kind == T_BOL else ('eol',)), True
        if kind in (T_STAR, T_PLUS, T_QUEST, T_BRACE):
            # repetition operator at the start of an expression
            if ere or kind == T_BRACE:
                raise RegexError('Invalid preceding regular expression')
            ch = {T_STAR: '*', T_PLUS: '+', T_QUEST: '?'}[kind]
            self.i += ln
            node = self.char_node(ch)
        elif kind == T_CLOSE:
            # unmatched close at depth 0
            if not ere:
                raise RegexError('Unmatched ) or \\)')
            self.i += ln
            node = self.char_node(')')
        elif kind == T_CLOSEBRACE:
            self.i += ln
            node = self.char_node('}')
        elif kind == T_CHAR:
            self.i += ln
            node = self.char_node(val)
        elif kind == T_ANY:
            self.i += ln
            node = ('set', None, True)
        elif kind == T_SET:
            self.i += ln
            node = self.parse_bracket()
        elif kind == T_OPEN:
            self.i += ln
            self.ngroups += 1
            idx = self.ngroups
            self.depth += 1
            k2, v2, l2 = self.peek(True)
            if k2 == T_CLOSE:
                inner = ('cat', [])
            else:
                inner = self.parse_alt(True)
            k2, v2, l2 = self.peek(False)
            if k2 != T_CLOSE:
                raise RegexError('Unmatched ( or \\(')
            self.i += l2
            self.depth -= 1
            self.completed.add(idx)
            node = ('group', idx, inner)
        elif kind == T_BREF:
            if val not in self.completed:
                raise RegexError('Invalid back reference')
            self.i += ln
            node = ('bref', val)
        else:
            raise RegexError('internal')
        # postfix duplication operators
        while True:
            k, v, l = self.peek(False)
            if k not in (T_STAR, T_PLUS, T_QUEST, T_BRACE):
                break
            self.i += l
            if k == T_STAR:
                node = ('rep', node, 0, None)
            elif k == T_PLUS:
                node = ('rep', node, 1, None)
            elif k == T_QUEST:
                node = ('rep', node, 0, 1)
            else:
                mn, mx = self.parse_interval()
                node = ('rep', node, mn, mx)
            if not ere:
                k3, v3, l3 = self.peek(False)
                if k3 in (T_STAR, T_BRACE):
                    raise RegexError('Invalid preceding regular expression')
        return node, False

    def parse_interval(self):
        p, n = self.p, self.n

        def number():
            j = self.i
            while self.i < n and p[self.i].isdigit():
                self.i += 1
            if self.i == j:
                return -1
            v = int(p[j:self.i])
            return v

        mn = number()
        if mn == -1:
            if self.i < n and p[self.i] == ',':
                mn = 0
            else:
                raise RegexError('Invalid content of \\{\\}')
        if self.i < n and p[self.i] == ',':
            self.i += 1
            mx = number()
            if mx == -1:
                mx = None
        else:
            mx = mn
        # closing
        if self.ere:
            if self.i < n and p[self.i] == '}':
                self.i += 1
            else:
                raise RegexError('Invalid content of \\{\\}')
        else:
            if self.i + 1 < n and p[self.i] == '\\' and p[self.i + 1] == '}':
                self.i += 2
            else:
                raise RegexError('Invalid content of \\{\\}')
        if mx is not None and mn > mx:
            raise RegexError('Invalid content of \\{\\}')
        if (mx if mx is not None else mn) > RE_DUP_MAX:
            raise RegexError('Regular expression too big')
        return mn, mx

    def char_node(self, c):
        if self.icase:
            return ('set', frozenset((c, c.lower(), c.upper())), False)
        return ('char', c)

    def parse_bracket(self):
        p, n = self.p, self.n
        neg = False
        chars = set()
        if self.i < n and p[self.i] == '^':
            neg = True
            self.i += 1
        first = True

        def element():
            # returns ('c', ch) or ('class', name)
            if self.i >= n:
                raise RegexError('Unmatched [, [^, [:, [., or [=')
            c = p[self.i]
            if c == '[' and self.i + 1 < n and p[self.i + 1] in '.=:':
                d = p[self.i + 1]
                j = self.i + 2
                k = p.find(d + ']', j)
                if k < 0:
                    raise RegexError('Unmatched [, [^, [:, [., or [=')
                name = p[j:k]
                self.i = k + 2
                if d == ':':
                    if name not in _CLASSES:
                        raise RegexError('Invalid character class name')
                    return ('class', name)
                if len(name) != 1:
                    raise RegexError('Invalid collation character')
                return ('c', name) if d == '.' else ('eq', name)
            self.i += 1
            return ('c', c)

        while True:
            if self.i >= n:
                raise RegexError('Unmatched [, [^, [:, [., or [=')
            c = p[self.i]
            if c == ']' and not first:
                self.i += 1
                break
            was_first = first
            first = False
            e1 = element()
            if e1[0] == 'class':
                f = _CLASSES[e1[1]]
                for ch in _ALLCHARS:
                    if f(ch):
                        chars.add(ch)
                continue
            if e1[0] == 'eq':
                chars.add(e1[1])
                continue
            # possible range
            if self.i < n and p[self.i] == '-' and self.i + 1 < n and p[self.i + 1] != ']':
                if e1 == ('c', '-') and not was_first:
                    pass
                self.i += 1
                e2 = element()
                if e2[0] != 'c':
                    raise RegexError('Invalid range end')
                a, b = ord(e1[1]), ord(e2[1])
                if a > b:
                    raise RegexError('Invalid range end')
                for o in range(a, b + 1):
                    chars.add(chr(o))
                continue
            chars.add(e1[1])
        if self.icase:
            extra = set()
            for ch in chars:
                extra.add(ch.lower())
                extra.add(ch.upper())
            chars |= extra
        return ('set', frozenset(chars), neg)


# NFA opcodes
OP_CHAR, OP_SET, OP_SPLIT, OP_SAVE, OP_BOL, OP_EOL, OP_BREF, OP_MATCH, OP_JMP = range(9)


class Regex:
    def __init__(self, pattern, ere=False, icase=False):
        parser = _Parser(pattern, ere, icase)
        ast = parser.parse()
        self.nsub = parser.ngroups
        self.icase = icase
        self.has_bref = False
        self.ops = []
        match = self._emit([OP_MATCH])
        self.start = self._compile(ast, match)

    def _emit(self, op):
        self.ops.append(op)
        return len(self.ops) - 1

    def _compile(self, node, k):
        t = node[0]
        if t == 'char':
            return self._emit([OP_CHAR, node[1], k])
        if t == 'set':
            return self._emit([OP_SET, node[1], node[2], k])
        if t == 'cat':
            for item in reversed(node[1]):
                k = self._compile(item, k)
            return k
        if t == 'alt':
            starts = [self._compile(b, k) for b in node[1]]
            s = starts[-1]
            for st in reversed(starts[:-1]):
                s = self._emit([OP_SPLIT, st, s])
            return s
        if t == 'group':
            idx = node[1]
            close = self._emit([OP_SAVE, 2 * idx + 1, k])
            inner = self._compile(node[2], close)
            return self._emit([OP_SAVE, 2 * idx, inner])
        if t == 'bol':
            return self._emit([OP_BOL, k])
        if t == 'eol':
            return self._emit([OP_EOL, k])
        if t == 'bref':
            self.has_bref = True
            return self._emit([OP_BREF, node[1], k])
        if t == 'rep':
            sub, mn, mx = node[1], node[2], node[3]
            if mx is None:
                loop = self._emit([OP_SPLIT, None, k])
                body = self._compile(sub, loop)
                self.ops[loop][1] = body
                s = loop
            else:
                s = k
                for _ in range(mx - mn):
                    body = self._compile(sub, s)
                    s = self._emit([OP_SPLIT, body, k])
            for _ in range(mn):
                s = self._compile(sub, s)
            return s
        raise RegexError('internal')

    def _run(self, text, start, notbol, want_caps):
        """Explore from `start`; return (end, caps) of the longest match
        (highest-priority path for that end), or None."""
        ops = self.ops
        n = len(text)
        icase = self.icase
        has_bref = self.has_bref
        ncap = 2 * (self.nsub + 1)
        caps0 = (-1,) * ncap
        stack = [(self.start, start, caps0)]
        visited = set()
        best_end = -1
        best_caps = None
        while stack:
            st, p, caps = stack.pop()
            key = (st, p, caps) if has_bref else (st, p)
            if key in visited:
                continue
            visited.add(key)
            op = ops[st]
            code = op[0]
            if code == OP_CHAR:
                if p < n and text[p] == op[1]:
                    stack.append((op[2], p + 1, caps))
            elif code == OP_SET:
                if p < n:
                    s = op[1]
                    if s is None:
                        stack.append((op[3], p + 1, caps))
                    else:
                        c = text[p]
                        if (c in s) != op[2]:
                            stack.append((op[3], p + 1, caps))
            elif code == OP_SPLIT:
                stack.append((op[2], p, caps))
                stack.append((op[1], p, caps))
            elif code == OP_SAVE:
                if want_caps or has_bref:
                    lst = list(caps)
                    lst[op[1]] = p
                    caps = tuple(lst)
                stack.append((op[2], p, caps))
            elif code == OP_BOL:
                if p == 0 and not notbol:
                    stack.append((op[1], p, caps))
            elif code == OP_EOL:
                if p == n:
                    stack.append((op[1], p, caps))
            elif code == OP_BREF:
                g = op[1]
                a, b = caps[2 * g], caps[2 * g + 1]
                if a >= 0 and b >= 0:
                    ln = b - a
                    if p + ln <= n:
                        if icase:
                            ok = text[a:b].lower() == text[p:p + ln].lower()
                        else:
                            ok = text[a:b] == text[p:p + ln]
                        if ok:
                            stack.append((op[2], p + ln, caps))
            elif code == OP_MATCH:
                if p > best_end:
                    best_end = p
                    best_caps = caps
                    if not want_caps or p == n:
                        break
        if best_end < 0:
            return None
        return best_end, best_caps

    def search(self, text, pos=0, notbol=False, want_caps=True):
        n = len(text)
        for s in range(pos, n + 1):
            r = self._run(text, s, notbol or s > 0, want_caps)
            if r is not None:
                end, caps = r
                groups = [(s, end)]
                for g in range(1, self.nsub + 1):
                    a, b = caps[2 * g], caps[2 * g + 1]
                    if a >= 0 and b >= 0:
                        groups.append((a, b))
                    else:
                        groups.append((-1, -1))
                return groups
        return None

    def test(self, text):
        return self.search(text, 0, False, False) is not None


# ---------------------------------------------------------------------------
# The editor
# ---------------------------------------------------------------------------

class EdError(Exception):
    pass


class Quit(Exception):
    pass


QUIT = 'quit'
EMOD = 'emod'
ERR = 'err'

PF_L, PF_N, PF_P = 1, 2, 4


class Line:
    __slots__ = ('t',)

    def __init__(self, t):
        self.t = t


class Cur:
    """A cursor over a command buffer."""
    __slots__ = ('s', 'i')

    def __init__(self, s, i=0):
        self.s = s
        self.i = i

    def peek(self, off=0):
        j = self.i + off
        if j < len(self.s):
            return self.s[j]
        return ''

    def get(self):
        c = self.peek()
        self.i += 1
        return c

    def at_end(self):
        return self.i >= len(self.s)


def strip_escapes(s):
    out = []
    i = 0
    while i < len(s):
        c = s[i]
        if c == '\\' and i + 1 < len(s):
            i += 1
            c = s[i]
        out.append(c)
        i += 1
    return ''.join(out)


def trailing_escape(s, end):
    """True if s[:end] ends with an odd number of backslashes."""
    cnt = 0
    j = end - 1
    while j >= 0 and s[j] == '\\':
        cnt += 1
        j -= 1
    return cnt % 2 == 1


class Ed:
    def __init__(self, ere, loose, scripted, data):
        self.ere = ere
        self.loose = loose
        self.scripted = scripted
        self.data = data
        self.dpos = 0
        self.out = []
        self.buf = []
        self.cur = 0
        self.modified = False
        self.def_fn = ''
        self.marks = {}
        self.last_re = None
        self.subst_re = None
        self.rtemplate = None
        self.undo_snap = None
        self.undo_atoms = False
        self.active = None
        self.first_addr = 0
        self.second_addr = 0
        # s command persistent state
        self.s_pflags = 0
        self.s_pmask = PF_P
        self.s_snum = 1
        try:
            st = os.fstat(0)
            self.stdin_reg = stat.S_ISREG(st.st_mode)
        except OSError:
            self.stdin_reg = False

    # -- io -----------------------------------------------------------------
    def write(self, s):
        self.out.append(s)

    def flush(self):
        if self.out:
            sys.stdout.buffer.write(''.join(self.out).encode('latin-1'))
            self.out = []
        sys.stdout.buffer.flush()

    def get_stdin_line(self):
        d = self.data
        if self.dpos >= len(d):
            return ''
        j = d.find('\n', self.dpos)
        if j < 0:
            line = d[self.dpos:] + '\n'
            self.dpos = len(d)
        else:
            line = d[self.dpos:j + 1]
            self.dpos = j + 1
        return line

    # -- buffer helpers -----------------------------------------------------
    def last(self):
        return len(self.buf)

    def clear_undo(self):
        self.undo_snap = (list(self.buf), self.cur, self.modified)
        self.undo_atoms = False

    def reset_undo(self):
        self.undo_snap = None
        self.undo_atoms = False

    def changed(self):
        self.modified = True
        self.undo_atoms = True

    def unset_active(self, nodes):
        if self.active is not None:
            ids = set(id(x) for x in nodes)
            for k, x in enumerate(self.active):
                if x is not None and id(x) in ids:
                    self.active[k] = None

    def node_addr(self, node):
        for k, x in enumerate(self.buf):
            if x is node:
                return k + 1
        return -1

    def invalid_address(self):
        raise EdError('Invalid address')

    # -- parsing helpers ----------------------------------------------------
    @staticmethod
    def skip_blanks(c):
        while c.peek() in (' ', '\t'):
            c.i += 1

    @staticmethod
    def parse_int(c):
        j = c.i
        while c.peek().isdigit():
            c.i += 1
        v = int(c.s[j:c.i])
        if v > 2147483647:
            raise EdError('Number out of range')
        return v

    def get_marked_addr(self, ch):
        if not ('a' <= ch <= 'z'):
            raise EdError('Invalid mark character')
        node = self.marks.get(ch)
        if node is None:
            if self.last() == 0:
                return 0
            self.invalid_address()
        a = self.node_addr(node)
        if a < 0:
            self.invalid_address()
        return a

    def extract_pattern(self, c, delim):
        s = c.s
        j = c.i
        n = len(s)
        while j < n and s[j] != delim and s[j] != '\n':
            if s[j] == '[':
                j = self.parse_char_class(s, j + 1)
                if j < 0:
                    raise EdError('Unbalanced brackets ([])')
            elif s[j] == '\\':
                j += 1
                if j >= n or s[j] == '\n':
                    raise EdError('Trailing backslash (\\)')
            j += 1
        pat = s[c.i:j]
        c.i = j
        return pat

    @staticmethod
    def parse_char_class(s, p):
        n = len(s)
        if p < n and s[p] == '^':
            p += 1
        if p < n and s[p] == ']':
            p += 1
        while p < n and s[p] != ']' and s[p] != '\n':
            if s[p] == '[' and p + 1 < n and s[p + 1] in '.:=':
                d = s[p + 1]
                p += 2
                while True:
                    if p >= n or s[p] == '\n':
                        return -1
                    if s[p] == ']' and s[p - 1] == d:
                        break
                    p += 1
            p += 1
        if p < n and s[p] == ']':
            return p
        return -1

    def compile(self, pat, icase):
        if pat == '':
            if self.last_re is None:
                raise EdError('No previous pattern')
            if icase:
                raise EdError('Suffix I is invalid with empty regex')
            return self.last_re
        try:
            r = Regex(pat, self.ere, icase)
        except RegexError as e:
            raise EdError(str(e))
        self.last_re = r
        return r

    def get_search_regex(self, c):
        """Parse /RE/[I] at the cursor (cursor on the delimiter)."""
        delim = c.get()
        if delim == ' ' or delim == '\n' or delim == '':
            raise EdError('Invalid pattern delimiter')
        pat = self.extract_pattern(c, delim)
        if c.peek() == delim:
            c.i += 1
        icase = False
        if c.peek() == 'I':
            c.i += 1
            icase = True
        return self.compile(pat, icase)

    def next_matching_addr(self, c):
        forward = c.peek() == '/'
        r = self.get_search_regex(c)
        addr = self.cur
        last = self.last()
        while True:
            if forward:
                addr = addr + 1 if addr < last else 0
            else:
                addr = addr - 1 if addr > 0 else last
            if addr:
                if r.test(self.buf[addr - 1].t):
                    return addr
            if addr == self.cur:
                break
        raise EdError('No match')

    def extract_addresses(self, c):
        first = True
        self.first_addr = -1
        self.second_addr = -1
        self.skip_blanks(c)
        while True:
            ch = c.peek()
            if ch.isdigit() and ch != '':
                n = self.parse_int(c)
                if first:
                    first = False
                    self.second_addr = n
                else:
                    self.second_addr += n
            elif ch in (' ', '\t'):
                c.i += 1
                self.skip_blanks(c)
            elif ch in ('+', '-'):
                if first:
                    first = False
                    self.second_addr = self.cur
                if c.peek(1).isdigit() and c.peek(1) != '':
                    c.i += 1
                    n = self.parse_int(c)
                    self.second_addr += (-n if ch == '-' else n)
                else:
                    c.i += 1
                    self.second_addr += (1 if ch == '+' else -1)
            elif ch in ('.', '$'):
                if not first:
                    self.invalid_address()
                first = False
                c.i += 1
                self.second_addr = self.cur if ch == '.' else self.last()
            elif ch in ('/', '?'):
                if not first:
                    self.invalid_address()
                self.second_addr = self.next_matching_addr(c)
                first = False
            elif ch == "'":
                if not first:
                    self.invalid_address()
                first = False
                c.i += 1
                self.second_addr = self.get_marked_addr(c.get())
            elif ch in (',', ';', '%'):
                if first:
                    if self.first_addr < 0:
                        self.first_addr = self.cur if ch == ';' else 1
                        self.second_addr = self.last()
                else:
                    if self.second_addr < 0 or self.second_addr > self.last():
                        self.invalid_address()
                    if ch == ';':
                        self.cur = self.second_addr
                    self.first_addr = self.second_addr
                    first = True
                c.i += 1
            else:
                if not first and (self.second_addr < 0 or self.second_addr > self.last()):
                    self.invalid_address()
                cnt = 0
                if self.second_addr >= 0:
                    cnt = 2 if self.first_addr >= 0 else 1
                if cnt <= 0:
                    self.second_addr = self.cur
                if cnt <= 1:
                    self.first_addr = self.second_addr
                return cnt

    def check_addr_range(self, n, m, addr_cnt):
        if addr_cnt == 0:
            self.first_addr = n
            self.second_addr = m
        if self.first_addr < 1 or self.first_addr > self.second_addr or \
                self.second_addr > self.last():
            self.invalid_address()

    def check_addr_range2(self, addr_cnt):
        self.check_addr_range(self.cur, self.cur, addr_cnt)

    def get_third_addr(self, c):
        f, s = self.first_addr, self.second_addr
        self.extract_addresses(c)
        a = self.second_addr
        if a < 0 or a > self.last():
            self.invalid_address()
        self.first_addr, self.second_addr = f, s
        return a

    @staticmethod
    def get_command_suffix(c, pflags=0):
        while True:
            ch = c.peek()
            if ch == 'l':
                f = PF_L
            elif ch == 'n':
                f = PF_N
            elif ch == 'p':
                f = PF_P
            else:
                break
            if pflags & f:
                raise EdError('Invalid command suffix')
            pflags |= f
            c.i += 1
        if c.get() != '\n':
            raise EdError('Invalid command suffix')
        return pflags

    @staticmethod
    def unexpected_address(addr_cnt):
        if addr_cnt > 0:
            raise EdError('Unexpected address')

    @staticmethod
    def unexpected_suffix(ch):
        if ch not in (' ', '\t', '\n', '\v', '\f', '\r'):
            raise EdError('Unexpected command suffix')

    def get_filename(self, c):
        self.skip_blanks(c)
        if c.peek() != '\n' and c.peek() != '':
            j = c.s.find('\n', c.i)
            if j < 0:
                j = len(c.s)
            name = c.s[c.i:j]
            c.i = j
        else:
            name = ''
            if not self.def_fn:
                raise EdError('No current filename')
        if c.peek() == '\n':
            c.i += 1
        return name

    # -- file io ------------------------------------------------------------
    def read_file(self, fname, addr):
        try:
            with open(strip_escapes(fname), 'rb') as f:
                raw = f.read()
        except OSError:
            raise EdError('Cannot open input file')
        text = raw.decode('latin-1')
        lines = text.split('\n')
        if lines and lines[-1] == '':
            lines.pop()
        nodes = [Line(t) for t in lines]
        self.buf[addr:addr] = nodes
        self.cur = addr + len(nodes)
        if nodes:
            self.undo_atoms = True
        if not self.scripted:
            self.write('%d\n' % len(raw))
        return len(nodes)

    def write_file(self, fname, mode, frm, to):
        if frm == 0:
            nodes = []
        else:
            nodes = self.buf[frm - 1:to]
        data = ''.join(x.t + '\n' for x in nodes).encode('latin-1')
        try:
            with open(strip_escapes(fname), mode) as f:
                f.write(data)
        except OSError:
            raise EdError('Cannot open output file')
        if not self.scripted:
            self.write('%d\n' % len(data))
        return len(nodes)

    # -- line operations ----------------------------------------------------
    def print_lines(self, frm, to, pflags):
        if frm == 0:
            self.invalid_address()
        for a in range(frm, to + 1):
            t = self.buf[a - 1].t
            if pflags & PF_N:
                self.write('%d\t' % a)
            if pflags & PF_L:
                self.write(self.list_line(t))
            else:
                self.write(t + '\n')
        self.cur = to

    @staticmethod
    def list_line(t):
        out = []
        col = 0
        esc = {'\a': '\\a', '\b': '\\b', '\f': '\\f', '\n': '\\n',
               '\r': '\\r', '\t': '\\t', '\v': '\\v', '\\': '\\\\', '$': '\\$'}
        for ch in t:
            if ch in esc:
                piece = esc[ch]
            elif 32 <= ord(ch) < 127:
                piece = ch
            else:
                piece = '\\%03o' % ord(ch)
            if col + len(piece) > 71:
                out.append('\\\n')
                col = 0
            out.append(piece)
            col += len(piece)
        out.append('$\n')
        return ''.join(out)

    def delete_lines(self, frm, to, isglobal):
        removed = self.buf[frm - 1:to]
        del self.buf[frm - 1:to]
        if isglobal:
            self.unset_active(removed)
        self.cur = frm if frm <= self.last() else self.last()
        self.changed()

    def append_lines(self, c, pos, isglobal):
        """Read input lines, inserting them after address `pos`."""
        while True:
            if not isglobal:
                line = self.get_stdin_line()
                if line == '':
                    return
            else:
                if c.at_end():
                    return
                j = c.s.find('\n', c.i)
                if j < 0:
                    line = c.s[c.i:] + '\n'
                    c.i = len(c.s)
                else:
                    line = c.s[c.i:j + 1]
                    c.i = j + 1
            if line == '.\n':
                return
            node = Line(line[:-1])
            self.buf.insert(pos, node)
            pos += 1
            self.cur = pos
            self.changed()

    def join_lines(self, frm, to, isglobal):
        removed = self.buf[frm - 1:to]
        node = Line(''.join(x.t for x in removed))
        self.buf[frm - 1:to] = [node]
        if isglobal:
            self.unset_active(removed)
        self.cur = frm
        self.changed()

    def move_lines(self, frm, to, addr, isglobal):
        seg = self.buf[frm - 1:to]
        if addr == frm - 1 or addr == to:
            self.cur = to
            self.modified = True
        else:
            del self.buf[frm - 1:to]
            if addr > to:
                addr -= len(seg)
            self.buf[addr:addr] = seg
            self.cur = addr + len(seg)
            self.changed()
        if isglobal:
            self.unset_active(seg)

    def copy_lines(self, frm, to, addr):
        seg = [Line(x.t) for x in self.buf[frm - 1:to]]
        self.buf[addr:addr] = seg
        self.cur = addr + len(seg)
        self.changed()

    def undo(self, isglobal):
        if self.undo_snap is None or not self.undo_atoms:
            raise EdError('Nothing to undo')
        sb, sc, sm = self.undo_snap
        self.undo_snap = (self.buf, self.cur, self.modified)
        self.buf = list(sb)
        self.cur = sc
        self.modified = sm
        if isglobal and self.active is not None:
            for k in range(len(self.active)):
                self.active[k] = None

    # -- substitution -------------------------------------------------------
    def extract_replacement(self, c, isglobal):
        delim = c.get()
        s = c.s
        if c.peek() == '%' and (c.peek(1) == delim or (
                c.peek(1) == '\n' and (not isglobal or c.i + 2 >= len(s)))):
            c.i += 1
            if self.rtemplate is None:
                raise EdError('No previous substitution')
            return
        out = []
        while c.peek() != delim:
            ch = c.peek()
            if ch == '':
                break
            if ch == '\n' and (not isglobal or c.i + 1 >= len(c.s)):
                break
            c.i += 1
            out.append(ch)
            if ch == '\\':
                ch2 = c.peek()
                if ch2 == '':
                    break
                c.i += 1
                out.append(ch2)
                if ch2 == '\n' and not isglobal:
                    line = self.get_stdin_line()
                    if line == '':
                        raise EdError('Unexpected end of file')
                    c.s = line
                    c.i = 0
        self.rtemplate = ''.join(out)

    def apply_template(self, text, groups, nsub):
        t = self.rtemplate
        out = []
        i = 0
        n = len(t)
        while i < n:
            ch = t[i]
            if ch == '&':
                a, b = groups[0]
                out.append(text[a:b])
            elif ch == '\\' and i + 1 < n and '1' <= t[i + 1] <= '9' and \
                    int(t[i + 1]) <= nsub:
                g = int(t[i + 1])
                a, b = groups[g]
                if a >= 0:
                    out.append(text[a:b])
                i += 1
            else:
                if ch == '\\':
                    i += 1
                    if i >= n:
                        break
                    ch = t[i]
                out.append(ch)
            i += 1
        return ''.join(out)

    def replace_matching_text(self, text, regex, snum):
        glob = snum <= 0
        m = regex.search(text, 0, False)
        if m is None:
            return None
        out = []
        pos = 0
        changed = False
        matchno = 0
        prev_empty = False
        first = True
        n = len(text)
        while True:
            so, eo = m[0]
            if glob and not first and so == eo and so == pos and prev_empty:
                raise EdError('Infinite substitution loop')
            first = False
            if glob or snum == matchno + 1:
                matchno += 1
                out.append(text[pos:so])
                out.append(self.apply_template(text, m, regex.nsub))
                changed = True
            else:
                matchno += 1
                out.append(text[pos:eo])
            pos = eo
            if pos >= n:
                break
            prev_empty = (so == eo)
            if not glob and changed:
                break
            m = regex.search(text, pos, True)
            if m is None:
                break
        out.append(text[pos:])
        if not changed:
            return None
        return ''.join(out)

    def search_and_replace(self, frm, to, snum, isglobal):
        regex = self.subst_re
        i = frm
        end = to
        last_sub = -1
        while i <= end:
            node = self.buf[i - 1]
            res = self.replace_matching_text(node.t, regex, snum)
            if res is not None:
                parts = res.split('\n')
                new = [Line(t) for t in parts]
                self.buf[i - 1:i] = new
                if isglobal:
                    self.unset_active([node])
                k = len(new)
                last_sub = i + k - 1
                end += k - 1
                i += k
                self.changed()
            else:
                i += 1
        if last_sub < 0:
            if not isglobal:
                raise EdError('No match')
            return
        self.cur = last_sub

    def command_s(self, c, addr_cnt, isglobal):
        self.check_addr_range2(addr_cnt)
        SF_G, SF_P, SF_R, SF_NONE = 1, 2, 4, 8
        sflags = 0
        while True:
            ch = c.peek()
            if ch.isdigit() and ch != '':
                self.s_snum = self.parse_int(c)
                sflags |= SF_NONE
            elif ch == '\n':
                sflags |= SF_NONE
            elif ch == 'g':
                sflags |= SF_G
                c.i += 1
            elif ch == 'p':
                sflags |= SF_P
                c.i += 1
            elif ch == 'r':
                sflags |= SF_R
                c.i += 1
            else:
                if sflags:
                    raise EdError('Invalid command suffix')
            if not (sflags and c.peek() != '\n'):
                break
        if sflags:
            if self.subst_re is None or self.rtemplate is None:
                raise EdError('No previous substitution')
            if sflags & SF_G:
                self.s_snum = 1 if self.s_snum <= 0 else 0
            if sflags & SF_P:
                self.s_pflags ^= self.s_pmask
            if sflags & SF_R:
                if self.last_re is None:
                    raise EdError('No previous pattern')
                self.subst_re = self.last_re
            c.i += 1  # the newline
        else:
            delim = c.peek()
            if delim in (' ', '\n', '') or delim == '\\':
                raise EdError('Invalid pattern delimiter')
            c.i += 1
            pat = self.extract_pattern(c, delim)
            if c.peek() != delim:
                raise EdError('Missing pattern delimiter')
            # compile now unless I suffix may follow; decide after suffixes
            self.extract_replacement(c, isglobal)
            pflags = 0
            snum = 1
            icase = False
            if c.peek() == '\n':
                pflags = PF_P
            else:
                if c.peek() == delim:
                    c.i += 1
                gseen = False
                cseen = False
                while True:
                    ch = c.peek()
                    if ch == 'g':
                        if gseen or cseen:
                            raise EdError('Invalid command suffix')
                        gseen = True
                        snum = 0
                        c.i += 1
                    elif ch.isdigit() and ch != '':
                        if gseen or cseen:
                            raise EdError('Invalid command suffix')
                        cseen = True
                        snum = self.parse_int(c)
                        if snum <= 0:
                            raise EdError('Invalid count')
                    elif ch in ('l', 'n', 'p'):
                        f = {'l': PF_L, 'n': PF_N, 'p': PF_P}[ch]
                        if pflags & f:
                            raise EdError('Invalid command suffix')
                        pflags |= f
                        c.i += 1
                    elif ch in ('I', 'i'):
                        if icase:
                            raise EdError('Invalid command suffix')
                        icase = True
                        c.i += 1
                    else:
                        break
                if c.get() != '\n':
                    raise EdError('Invalid command suffix')
            self.subst_re = self.compile(pat, icase)
            self.s_pflags = pflags
            self.s_pmask = pflags if pflags else PF_P
            self.s_snum = snum
        if not isglobal:
            self.clear_undo()
        self.search_and_replace(self.first_addr, self.second_addr,
                                self.s_snum, isglobal)
        return self.s_pflags

    # -- global -------------------------------------------------------------
    def get_extended_line(self, c, strip):
        s = c.s
        j = s.find('\n', c.i)
        if j < 0:
            return
        line = s[c.i:j + 1]
        if len(line) < 2 or not trailing_escape(line, len(line) - 1):
            return
        buf = line[:-2] + ('' if strip else '\n')
        while True:
            l2 = self.get_stdin_line()
            if l2 == '':
                raise EdError('Unexpected end of file')
            if len(l2) < 2 or not trailing_escape(l2, len(l2) - 1):
                buf += l2
                break
            buf += l2[:-2] + ('' if strip else '\n')
        c.s = buf
        c.i = 0

    def exec_global(self, c):
        self.get_extended_line(c, False)
        cmd = c.s[c.i:]
        self.clear_undo()
        k = 0
        while True:
            node = None
            while k < len(self.active):
                node = self.active[k]
                k += 1
                if node is not None:
                    break
                node = None
            if node is None:
                break
            a = self.node_addr(node)
            if a < 0:
                continue
            self.cur = a
            gc = Cur(cmd)
            while not gc.at_end():
                st = self.exec_command(gc, 0, True)
                if st == QUIT:
                    raise Quit()
                if st != 0:
                    raise EdError('global command failed')

    def build_active_list(self, c, match):
        delim = c.peek()
        if delim in (' ', '\n', ''):
            raise EdError('Invalid pattern delimiter')
        r = self.get_search_regex(c)
        self.active = []
        for a in range(self.first_addr, self.second_addr + 1):
            node = self.buf[a - 1]
            if r.test(node.t) == match:
                self.active.append(node)

    # -- commands -----------------------------------------------------------
    def exec_command(self, c, prev_status, isglobal):
        try:
            return self._exec(c, prev_status, isglobal)
        except (Quit, KeyboardInterrupt):
            raise
        except EdError:
            return ERR
        except Exception:  # defensive: never crash on odd input
            return ERR

    def _exec(self, c, prev_status, isglobal):
        pflags = 0
        addr_cnt = self.extract_addresses(c)
        self.skip_blanks(c)
        cmd = c.get()
        if cmd == 'a':
            pflags = self.get_command_suffix(c)
            if not isglobal:
                self.clear_undo()
            self.cur = self.second_addr
            self.append_lines(c, self.second_addr, isglobal)
        elif cmd == 'i':
            pflags = self.get_command_suffix(c)
            if not isglobal:
                self.clear_undo()
            a = self.second_addr
            self.cur = a
            self.append_lines(c, a - 1 if a > 0 else 0, isglobal)
        elif cmd == 'c':
            if self.first_addr == 0:
                self.first_addr = 1
            if self.second_addr == 0:
                self.second_addr = 1
            self.check_addr_range2(addr_cnt)
            pflags = self.get_command_suffix(c)
            if not isglobal:
                self.clear_undo()
            frm = self.first_addr
            self.delete_lines(frm, self.second_addr, isglobal)
            self.append_lines(c, frm - 1, isglobal)
        elif cmd == 'd':
            self.check_addr_range2(addr_cnt)
            pflags = self.get_command_suffix(c)
            if not isglobal:
                self.clear_undo()
            self.delete_lines(self.first_addr, self.second_addr, isglobal)
        elif cmd in ('e', 'E'):
            if cmd == 'e' and self.modified and prev_status != EMOD:
                return EMOD
            self.unexpected_address(addr_cnt)
            self.unexpected_suffix(c.peek())
            fn = self.get_filename(c)
            self.buf = []
            self.cur = 0
            self.reset_undo()
            if fn:
                self.def_fn = fn
            self.modified = False
            try:
                self.read_file(fn if fn else self.def_fn, 0)
            finally:
                self.reset_undo()
                self.modified = False
        elif cmd == 'f':
            self.unexpected_address(addr_cnt)
            self.unexpected_suffix(c.peek())
            self.skip_blanks(c)
            if c.peek() != '\n' and c.peek() != '':
                fn = self.get_filename(c)
                self.def_fn = fn
            else:
                c.i += 1
            if not self.def_fn:
                raise EdError('No current filename')
            self.write(strip_escapes(self.def_fn) + '\n')
        elif cmd in ('g', 'v', 'G', 'V'):
            if isglobal:
                raise EdError('Cannot nest global commands')
            if cmd in ('G', 'V'):
                raise EdError('Unknown command')
            self.check_addr_range(1, self.last(), addr_cnt)
            self.build_active_list(c, cmd == 'g')
            try:
                self.exec_global(c)
            finally:
                self.active = None
        elif cmd == 'j':
            self.check_addr_range(self.cur, self.cur + 1, addr_cnt)
            pflags = self.get_command_suffix(c)
            if not isglobal:
                self.clear_undo()
            if self.first_addr < self.second_addr:
                self.join_lines(self.first_addr, self.second_addr, isglobal)
        elif cmd == 'k':
            ch = c.get()
            if self.second_addr == 0:
                self.invalid_address()
            pflags = self.get_command_suffix(c)
            if not ('a' <= ch <= 'z'):
                raise EdError('Invalid mark character')
            self.marks[ch] = self.buf[self.second_addr - 1]
        elif cmd in ('l', 'n', 'p'):
            n = {'l': PF_L, 'n': PF_N, 'p': PF_P}[cmd]
            self.check_addr_range2(addr_cnt)
            pflags = self.get_command_suffix(c, 0)
            self.print_lines(self.first_addr, self.second_addr, pflags | n)
            pflags = 0
        elif cmd == 'm':
            self.check_addr_range2(addr_cnt)
            addr = self.get_third_addr(c)
            if self.first_addr <= addr < self.second_addr:
                raise EdError('Invalid destination')
            pflags = self.get_command_suffix(c)
            if not isglobal:
                self.clear_undo()
            self.move_lines(self.first_addr, self.second_addr, addr, isglobal)
        elif cmd == 't':
            self.check_addr_range2(addr_cnt)
            addr = self.get_third_addr(c)
            pflags = self.get_command_suffix(c)
            if not isglobal:
                self.clear_undo()
            self.copy_lines(self.first_addr, self.second_addr, addr)
        elif cmd in ('P', 'q', 'Q'):
            self.unexpected_address(addr_cnt)
            pflags = self.get_command_suffix(c)
            if cmd == 'P':
                pass
            elif cmd == 'q' and self.modified and prev_status != EMOD:
                return EMOD
            else:
                return QUIT
        elif cmd == 'r':
            self.unexpected_suffix(c.peek())
            if addr_cnt == 0:
                self.second_addr = self.last()
            fn = self.get_filename(c)
            if not self.def_fn:
                self.def_fn = fn
            if not isglobal:
                self.clear_undo()
            n = self.read_file(fn if fn else self.def_fn, self.second_addr)
            if n:
                self.modified = True
        elif cmd == 's':
            pflags = self.command_s(c, addr_cnt, isglobal)
        elif cmd == 'u':
            self.unexpected_address(addr_cnt)
            pflags = self.get_command_suffix(c)
            self.undo(isglobal)
        elif cmd in ('w', 'W'):
            q = c.peek()
            if q == 'q':
                c.i += 1
            self.unexpected_suffix(c.peek())
            fn = self.get_filename(c)
            if addr_cnt == 0 and self.last() == 0:
                self.first_addr = self.second_addr = 0
            else:
                self.check_addr_range(1, self.last(), addr_cnt)
            if not self.def_fn:
                self.def_fn = fn
            n = self.write_file(fn if fn else self.def_fn,
                                'ab' if cmd == 'W' else 'wb',
                                self.first_addr, self.second_addr)
            if n == self.last():
                self.modified = False
            elif q == 'q' and self.modified and prev_status != EMOD:
                return EMOD
            if q == 'q':
                return QUIT
        elif cmd == '=':
            pflags = self.get_command_suffix(c)
            self.write('%d\n' % (self.second_addr if addr_cnt else self.last()))
        elif cmd == '\n':
            self.first_addr = 1
            self.check_addr_range(1, self.cur + (0 if isglobal else 1), addr_cnt)
            self.print_lines(self.second_addr, self.second_addr, 0)
        elif cmd == '#':
            j = c.s.find('\n', c.i)
            c.i = len(c.s) if j < 0 else j + 1
        else:
            raise EdError('Unknown command')
        if pflags:
            self.print_lines(self.cur, self.cur, pflags)
        return 0

    # -- main loop ----------------------------------------------------------
    def main_loop(self):
        status = 0
        err_status = 0
        while True:
            line = self.get_stdin_line()
            if line == '':
                if not self.modified or status == EMOD:
                    status = QUIT
                else:
                    status = EMOD
            else:
                try:
                    status = self.exec_command(Cur(line), status, False)
                except Quit:
                    status = QUIT
            if status == 0:
                continue
            if status == QUIT:
                return err_status
            self.write('?\n')
            if not self.loose and err_status == 0:
                err_status = 1
            if self.stdin_reg:
                return err_status


def main(argv):
    ere = loose = scripted = False
    fname = None
    for arg in argv:
        if len(arg) > 1 and arg[0] == '-':
            for ch in arg[1:]:
                if ch == 'E':
                    ere = True
                elif ch == 'l':
                    loose = True
                elif ch == 's':
                    scripted = True
                else:
                    sys.stderr.write('ed: invalid option -- %s\n' % ch)
                    return 1
        elif fname is None:
            fname = arg
        else:
            sys.stderr.write('ed: too many arguments\n')
            return 1
    try:
        data = sys.stdin.buffer.read().decode('latin-1')
    except (OSError, ValueError, AttributeError):
        data = ''
    ed = Ed(ere, loose, scripted, data)
    try:
        if fname is not None:
            ed.def_fn = fname
            try:
                ed.read_file(fname, 0)
            except EdError:
                sys.stderr.write('%s: No such file or directory\n' % fname)
                if ed.stdin_reg:
                    ed.flush()
                    return 2
            ed.reset_undo()
            ed.modified = False
        status = ed.main_loop()
    finally:
        ed.flush()
    return status


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
