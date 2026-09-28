"""pyed: a GNU ed 1.19 replacement in pure Python.

Usage: python3 /app/pyed/ed.py [OPTIONS] [FILE]
"""

import sys
import os

sys.setrecursionlimit(100000)

# ---------------------------------------------------------------------------
# Regular expressions (POSIX BRE / ERE, leftmost-longest, glibc flavoured)
# ---------------------------------------------------------------------------

RE_DUP_MAX = 32767
REP_CAP = 1000


class RegexError(Exception):
    pass


def _cls_members(name):
    r = []
    for i in range(256):
        c = chr(i)
        o = i
        if name == 'alnum':
            ok = c.isascii() and c.isalnum()
        elif name == 'alpha':
            ok = c.isascii() and c.isalpha()
        elif name == 'blank':
            ok = c in ' \t'
        elif name == 'cntrl':
            ok = o < 32 or o == 127
        elif name == 'digit':
            ok = '0' <= c <= '9'
        elif name == 'graph':
            ok = 33 <= o <= 126
        elif name == 'lower':
            ok = 'a' <= c <= 'z'
        elif name == 'print':
            ok = 32 <= o <= 126
        elif name == 'punct':
            ok = 33 <= o <= 126 and not (c.isascii() and c.isalnum())
        elif name == 'space':
            ok = c in ' \t\n\r\f\v'
        elif name == 'upper':
            ok = 'A' <= c <= 'Z'
        elif name == 'xdigit':
            ok = c in '0123456789abcdefABCDEF'
        else:
            raise RegexError('Invalid character class name')
        if ok:
            r.append(c)
    return r


CLASS_NAMES = ('alnum', 'alpha', 'blank', 'cntrl', 'digit', 'graph', 'lower',
               'print', 'punct', 'space', 'upper', 'xdigit')

# token kinds
T_CHAR, T_ANY, T_SET, T_OPEN, T_CLOSE, T_ALT, T_STAR, T_PLUS, T_QUES, \
    T_IOPEN, T_ICLOSE, T_BOL, T_EOL, T_BREF, T_END = range(15)


class _Parser:
    def __init__(self, pat, ere, icase):
        self.p = pat
        self.n = len(pat)
        self.i = 0
        self.ere = ere
        self.icase = icase
        self.ngroups = 0
        self.completed = set()
        self.has_bref = False
        self.tok = None
        self.tval = None

    def lc(self, c):
        return c.lower() if self.icase else c

    # -- tokenizer --
    def fetch(self, caret_ok=False):
        p = self.p
        if self.i >= self.n:
            self.tok, self.tval = T_END, None
            return
        c = p[self.i]
        start = self.i
        self.i += 1
        if c == '\\':
            if self.i >= self.n:
                raise RegexError('Trailing backslash')
            d = p[self.i]
            self.i += 1
            if not self.ere:
                if d == '(':
                    self.tok = T_OPEN
                    return
                if d == ')':
                    self.tok = T_CLOSE
                    return
                if d == '|':
                    self.tok = T_ALT
                    return
                if d == '{':
                    self.tok = T_IOPEN
                    return
                if d == '}':
                    self.tok, self.tval = T_ICLOSE, '}'
                    return
                if d == '+':
                    self.tok, self.tval = T_PLUS, '+'
                    return
                if d == '?':
                    self.tok, self.tval = T_QUES, '?'
                    return
            if '1' <= d <= '9':
                self.tok, self.tval = T_BREF, int(d)
                return
            self.tok, self.tval = T_CHAR, self.lc(d)
            return
        if c == '[':
            self.tok, self.tval = T_SET, self.parse_bracket()
            return
        if c == '.':
            self.tok = T_ANY
            return
        if c == '*':
            self.tok, self.tval = T_STAR, '*'
            return
        if c == '^':
            if self.ere or start == 0 or caret_ok:
                self.tok = T_BOL
                return
            self.tok, self.tval = T_CHAR, '^'
            return
        if c == '$':
            if self.ere or self.i >= self.n:
                self.tok = T_EOL
                return
            if p.startswith('\\)', self.i) or p.startswith('\\|', self.i):
                self.tok = T_EOL
                return
            self.tok, self.tval = T_CHAR, '$'
            return
        if self.ere:
            if c == '(':
                self.tok = T_OPEN
                return
            if c == ')':
                self.tok, self.tval = T_CLOSE, ')'
                return
            if c == '|':
                self.tok = T_ALT
                return
            if c == '{':
                self.tok = T_IOPEN
                return
            if c == '}':
                self.tok, self.tval = T_ICLOSE, '}'
                return
            if c == '+':
                self.tok, self.tval = T_PLUS, '+'
                return
            if c == '?':
                self.tok, self.tval = T_QUES, '?'
                return
        self.tok, self.tval = T_CHAR, self.lc(c)

    def parse_bracket(self):
        p = self.p
        n = self.n
        neg = False
        members = set()
        if self.i < n and p[self.i] == '^':
            neg = True
            self.i += 1
        first = True

        def elem():
            # returns ('c', ch) or ('cls', list)
            if self.i >= n:
                raise RegexError('Unmatched [')
            c = p[self.i]
            if c == '[' and self.i + 1 < n and p[self.i + 1] in '.:=':
                kind = p[self.i + 1]
                j = p.find(kind + ']', self.i + 2)
                if j < 0:
                    raise RegexError('Unmatched [')
                name = p[self.i + 2:j]
                self.i = j + 2
                if kind == ':':
                    if name not in CLASS_NAMES:
                        raise RegexError('Invalid character class name')
                    if self.icase and name in ('upper', 'lower'):
                        name = 'alpha'
                    return ('cls', _cls_members(name))
                if len(name) != 1:
                    raise RegexError('Invalid collation character')
                if kind == '=':
                    return ('eq', self.lc(name))
                return ('c', self.lc(name))
            self.i += 1
            return ('c', self.lc(c))

        while True:
            if self.i >= n:
                raise RegexError('Unmatched [')
            c = p[self.i]
            if c == ']' and not first:
                self.i += 1
                break
            if c == '-' and not first:
                # '-' not first: must be last
                if self.i + 1 < n and p[self.i + 1] == ']':
                    members.add('-')
                    self.i += 1
                    first = False
                    continue
                raise RegexError('Invalid range end')
            first = False
            e = elem()
            if (e[0] == 'c' and self.i + 1 < n and p[self.i] == '-'
                    and p[self.i + 1] != ']'):
                self.i += 1
                e2 = elem()
                if e2[0] != 'c':
                    raise RegexError('Invalid range end')
                a, b = ord(e[1]), ord(e2[1])
                if a > b:
                    raise RegexError('Invalid range end')
                for o in range(a, b + 1):
                    members.add(chr(o))
            elif e[0] == 'cls':
                members.update(e[1])
            else:
                members.add(e[1])
        if self.icase:
            members = set(m.lower() for m in members)
        return (frozenset(members), neg)

    # -- grammar --
    def parse(self):
        self.fetch(caret_ok=True)
        tree = self.parse_reg_exp(0)
        if self.tok != T_END:
            if self.tok == T_CLOSE:
                raise RegexError('Unmatched ) or \\)')
            raise RegexError('Invalid regular expression')
        return tree

    def branch_end(self, nest):
        return (self.tok == T_ALT or self.tok == T_END
                or (nest > 0 and self.tok == T_CLOSE))

    def parse_reg_exp(self, nest):
        alts = []
        if self.branch_end(nest):
            alts.append(('cat', []))
        else:
            alts.append(self.parse_branch(nest))
        while self.tok == T_ALT:
            self.fetch(caret_ok=True)
            if self.branch_end(nest):
                alts.append(('cat', []))
            else:
                alts.append(self.parse_branch(nest))
        if len(alts) == 1:
            return alts[0]
        return ('alt', alts)

    def parse_branch(self, nest):
        items = [self.parse_expression(nest)]
        while not self.branch_end(nest):
            items.append(self.parse_expression(nest))
        return ('cat', items)

    def parse_expression(self, nest):
        t = self.tok
        if t == T_CHAR or t == T_ICLOSE:
            c = self.tval
            atom = ('pred', ('lit', c))
            self.fetch()
        elif t == T_ANY:
            atom = ('pred', ('any',))
            self.fetch()
        elif t == T_SET:
            atom = ('pred', ('set', self.tval[0], self.tval[1]))
            self.fetch()
        elif t == T_OPEN:
            self.ngroups += 1
            idx = self.ngroups
            self.fetch(caret_ok=True)
            if self.tok == T_CLOSE:
                inner = ('cat', [])
            else:
                inner = self.parse_reg_exp(nest + 1)
            if self.tok != T_CLOSE:
                raise RegexError('Unmatched ( or \\(')
            self.completed.add(idx)
            atom = ('group', idx, inner)
            self.fetch()
        elif t == T_CLOSE:
            if not self.ere:
                raise RegexError('Unmatched ) or \\)')
            atom = ('pred', ('lit', ')'))
            self.fetch()
        elif t == T_BREF:
            if self.tval not in self.completed:
                raise RegexError('Invalid back reference')
            self.has_bref = True
            atom = ('bref', self.tval)
            self.fetch()
        elif t == T_BOL or t == T_EOL:
            atom = ('bol',) if t == T_BOL else ('eol',)
            self.fetch()
            return atom
        elif t in (T_STAR, T_PLUS, T_QUES, T_IOPEN):
            if self.ere:
                raise RegexError('Invalid preceding regular expression')
            if t == T_IOPEN:
                raise RegexError('Invalid preceding regular expression')
            atom = ('pred', ('lit', self.tval))
            self.fetch()
        else:
            raise RegexError('Invalid regular expression')
        while self.tok in (T_STAR, T_PLUS, T_QUES, T_IOPEN):
            t = self.tok
            if t == T_STAR:
                atom = ('rep', atom, 0, None)
                self.fetch()
            elif t == T_PLUS:
                atom = ('rep', atom, 1, None)
                self.fetch()
            elif t == T_QUES:
                atom = ('rep', atom, 0, 1)
                self.fetch()
            else:
                mn, mx = self.parse_interval()
                atom = ('rep', atom, mn, mx)
                self.fetch()
            if not self.ere and self.tok in (T_STAR, T_IOPEN):
                raise RegexError('Invalid preceding regular expression')
        return atom

    def parse_interval(self):
        p = self.p
        n = self.n

        def number():
            j = self.i
            while self.i < n and p[self.i].isdigit() and p[self.i].isascii():
                self.i += 1
            if j == self.i:
                return None
            return int(p[j:self.i])

        def close():
            if self.ere:
                if self.i < n and p[self.i] == '}':
                    self.i += 1
                    return True
                return False
            if p.startswith('\\}', self.i):
                self.i += 2
                return True
            return False

        mn = number()
        if mn is None:
            if self.i < n and p[self.i] == ',':
                mn = 0
            else:
                if self.i >= n:
                    raise RegexError('Unmatched \\{')
                raise RegexError('Invalid content of \\{\\}')
        if self.i < n and p[self.i] == ',':
            self.i += 1
            mx = number()
            if mx is None:
                mx = -1
        else:
            mx = mn
        if not close():
            if self.i >= n:
                raise RegexError('Unmatched \\{')
            raise RegexError('Invalid content of \\{\\}')
        if mx != -1 and mn > mx:
            raise RegexError('Invalid content of \\{\\}')
        if (mn if mx == -1 else mx) > RE_DUP_MAX:
            raise RegexError('Regular expression too big')
        return mn, (None if mx == -1 else mx)


def _make_pred(spec):
    k = spec[0]
    if k == 'lit':
        c = spec[1]
        return lambda ch: ch == c
    if k == 'any':
        return lambda ch: True
    members, neg = spec[1], spec[2]
    if neg:
        return lambda ch: ch not in members
    return lambda ch: ch in members


def _prep(node):
    """Replace pred specs by callables and cap repeat counts."""
    t = node[0]
    if t == 'pred':
        return ('pred', _make_pred(node[1]))
    if t == 'cat':
        return ('cat', [_prep(x) for x in node[1]])
    if t == 'alt':
        return ('alt', [_prep(x) for x in node[1]])
    if t == 'group':
        return ('group', node[1], _prep(node[2]))
    if t == 'rep':
        mn, mx = node[2], node[3]
        mn = min(mn, REP_CAP)
        if mx is not None:
            mx = min(mx, REP_CAP)
        return ('rep', _prep(node[1]), mn, mx)
    return node


def _compile_prog(tree):
    prog = []

    def emit(op):
        prog.append(op)
        return len(prog) - 1

    def comp(nd):
        t = nd[0]
        if t == 'pred':
            emit(['C', nd[1]])
        elif t == 'cat':
            for x in nd[1]:
                comp(x)
        elif t == 'alt':
            alts = nd[1]
            jumps = []
            for k, a in enumerate(alts):
                if k < len(alts) - 1:
                    sp = emit(['S', None, None])
                    prog[sp][1] = sp + 1
                    comp(a)
                    jumps.append(emit(['J', None]))
                    prog[sp][2] = len(prog)
                else:
                    comp(a)
            for j in jumps:
                prog[j][1] = len(prog)
        elif t == 'group':
            emit(['SAVE', 2 * nd[1]])
            comp(nd[2])
            emit(['SAVE', 2 * nd[1] + 1])
        elif t == 'bol':
            emit(['BOL'])
        elif t == 'eol':
            emit(['EOL'])
        elif t == 'rep':
            body, mn, mx = nd[1], nd[2], nd[3]
            for _ in range(mn):
                comp(body)
            if mx is None:
                l1 = emit(['S', None, None])
                prog[l1][1] = l1 + 1
                comp(body)
                emit(['J', l1])
                prog[l1][2] = len(prog)
            else:
                splits = []
                for _ in range(mx - mn):
                    sp = emit(['S', None, None])
                    prog[sp][1] = sp + 1
                    splits.append(sp)
                    comp(body)
                for sp in splits:
                    prog[sp][2] = len(prog)
        else:
            raise RegexError('internal')

    comp(tree)
    emit(['M'])
    return prog


class Regex:
    def __init__(self, pattern, ere, icase):
        ps = _Parser(pattern, ere, icase)
        tree = ps.parse()
        self.icase = icase
        self.ngroups = ps.ngroups
        self.has_bref = ps.has_bref
        self.tree = _prep(tree)
        if not self.has_bref:
            self.prog = _compile_prog(self.tree)

    def search(self, s, start=0, notbol=False):
        """Return (so, eo, groups) or None; groups is a list indexed 0..9."""
        subj = s.lower() if self.icase else s
        if self.has_bref:
            r = self._bt_search(subj, start, notbol)
        else:
            r = self._pike_search(subj, start, notbol)
        if r is None:
            return None
        so, eo, caps = r
        groups = [(so, eo)]
        for g in range(1, 10):
            if g <= self.ngroups and caps[2 * g] >= 0 and caps[2 * g + 1] >= 0:
                groups.append((caps[2 * g], caps[2 * g + 1]))
            else:
                groups.append(None)
        return so, eo, groups

    def _pike_search(self, s, start, notbol):
        prog = self.prog
        n = len(s)
        nslots = 2 * (self.ngroups + 1)
        init = tuple([-1] * nslots)
        best = None

        def addthread(lst, vis, pc0, caps0, st, pos):
            stack = [(pc0, caps0)]
            while stack:
                pc, caps = stack.pop()
                if pc in vis:
                    continue
                vis.add(pc)
                op = prog[pc]
                k = op[0]
                if k == 'J':
                    stack.append((op[1], caps))
                elif k == 'S':
                    stack.append((op[2], caps))
                    stack.append((op[1], caps))
                elif k == 'SAVE':
                    c = list(caps)
                    c[op[1]] = pos
                    stack.append((pc + 1, tuple(c)))
                elif k == 'BOL':
                    if pos == 0 and not notbol:
                        stack.append((pc + 1, caps))
                elif k == 'EOL':
                    if pos == n:
                        stack.append((pc + 1, caps))
                else:
                    lst.append((pc, caps, st))

        clist = []
        cvis = set()
        for pos in range(start, n + 1):
            if best is None:
                addthread(clist, cvis, 0, init, pos, pos)
            if not clist:
                if best is not None:
                    break
                cvis = set()
                continue
            nlist = []
            nvis = set()
            ch = s[pos] if pos < n else None
            for pc, caps, st in clist:
                if best is not None and st > best[0]:
                    continue
                op = prog[pc]
                if op[0] == 'M':
                    if (best is None or st < best[0]
                            or (st == best[0] and pos > best[1])):
                        best = (st, pos, caps)
                elif ch is not None and op[1](ch):
                    addthread(nlist, nvis, pc + 1, caps, st, pos + 1)
            clist, cvis = nlist, nvis
        return best

    def _bt_search(self, s, start, notbol):
        n = len(s)
        nslots = 2 * (self.ngroups + 1)
        init = tuple([-1] * nslots)

        def setslot(c, i, v):
            return c[:i] + (v,) + c[i + 1:]

        def m(nd, pos, caps, k):
            t = nd[0]
            if t == 'pred':
                if pos < n and nd[1](s[pos]):
                    return k(pos + 1, caps)
                return False
            if t == 'cat':
                items = nd[1]
                ln = len(items)

                def step(i, p, c):
                    if i == ln:
                        return k(p, c)
                    return m(items[i], p, c, lambda p2, c2: step(i + 1, p2, c2))
                return step(0, pos, caps)
            if t == 'alt':
                for a in nd[1]:
                    if m(a, pos, caps, k):
                        return True
                return False
            if t == 'group':
                gi = nd[1]
                return m(nd[2], pos, caps,
                         lambda p2, c2: k(p2, setslot(setslot(c2, 2 * gi, pos), 2 * gi + 1, p2)))
            if t == 'bref':
                gi = nd[1]
                a, b = caps[2 * gi], caps[2 * gi + 1]
                if a < 0 or b < 0:
                    return False
                sub = s[a:b]
                if s.startswith(sub, pos):
                    return k(pos + len(sub), caps)
                return False
            if t == 'bol':
                if pos == 0 and not notbol:
                    return k(pos, caps)
                return False
            if t == 'eol':
                if pos == n:
                    return k(pos, caps)
                return False
            if t == 'rep':
                body, mn, mx = nd[1], nd[2], nd[3]

                def it(cnt, p, c):
                    if mx is None or cnt < mx:
                        def after(p2, c2):
                            if p2 == p and cnt >= mn:
                                return False
                            return it(cnt + 1, p2, c2)
                        if m(body, p, c, after):
                            return True
                    if cnt >= mn:
                        return k(p, c)
                    return False
                return it(0, pos, caps)
            raise RegexError('internal')

        for st in range(start, n + 1):
            best = [None]

            def final(p, c):
                if best[0] is None or p > best[0][0]:
                    best[0] = (p, c)
                return p == n
            m(self.tree, st, init, final)
            if best[0] is not None:
                return st, best[0][0], best[0][1]
        return None


# ---------------------------------------------------------------------------
# The editor
# ---------------------------------------------------------------------------

QUIT = -1
ERR = -2
EMOD = -3

PF_L, PF_N, PF_P = 1, 2, 4


class EdError(Exception):
    pass


class Node(object):
    __slots__ = ('text',)

    def __init__(self, text):
        self.text = text


class Buf(object):
    __slots__ = ('s', 'i')

    def __init__(self, s):
        self.s = s + '\0'
        self.i = 0

    def cur(self):
        return self.s[self.i] if self.i < len(self.s) else '\0'

    def peek(self, k):
        j = self.i + k
        return self.s[j] if j < len(self.s) else '\0'

    def get(self):
        c = self.cur()
        self.i += 1
        return c

    def skip_blanks(self):
        s = self.s
        while self.i < len(s) and s[self.i] in ' \t\r\f\v':
            self.i += 1


def isspace(c):
    return c in ' \t\n\r\f\v'


def isdigit(c):
    return '0' <= c <= '9'


def strip_escapes(s):
    out = []
    i = 0
    while i < len(s):
        if s[i] == '\\' and i + 1 < len(s):
            i += 1
        out.append(s[i])
        i += 1
    return ''.join(out)


class Input(object):
    def __init__(self):
        self.f = sys.stdin.buffer

    def readline(self):
        b = self.f.readline()
        if not b:
            return None
        s = b.decode('latin-1')
        if not s.endswith('\n'):
            s += '\n'
        return s


class Ed(object):
    def __init__(self, ere, loose, scripted):
        self.ere = ere
        self.loose = loose
        self.scripted = scripted
        self.lines = []
        self.current = 0
        self.modified = False
        self.def_filename = ''
        self.marks = {}
        self.u_lines = None
        self.u_current = 0
        self.u_modified = False
        self.u_count = 0
        self.u_valid = False
        self.last_regex = None
        self.subst_regex = None
        self.rbuf = None
        self.s_g = False
        self.s_snum = 1
        self.s_pflags = 0
        self.s_pmask = PF_P
        self.active = None
        self.inactive = set()
        self.out = []
        self.inp = Input()
        self.first_addr = 0
        self.second_addr = 0
        self.addr_cnt = 0

    # -- output --
    def write(self, s):
        self.out.append(s)
        if len(self.out) > 256:
            self.flush()

    def flush(self):
        if self.out:
            sys.stdout.buffer.write(''.join(self.out).encode('latin-1'))
            self.out = []
        sys.stdout.buffer.flush()

    @property
    def last(self):
        return len(self.lines)

    # -- undo --
    def clear_undo_stack(self):
        self.u_lines = list(self.lines)
        self.u_current = self.current
        self.u_modified = self.modified
        self.u_count = 0
        self.u_valid = True

    def reset_undo_state(self):
        self.u_lines = None
        self.u_count = 0
        self.u_valid = False

    def push_undo(self):
        self.u_count += 1

    def undo(self, isglobal):
        if self.u_count <= 0 or not self.u_valid:
            raise EdError('Nothing to undo')
        ol, oc, om = self.lines, self.current, self.modified
        self.lines = self.u_lines
        self.current = self.u_current
        self.modified = self.u_modified
        self.u_lines, self.u_current, self.u_modified = list(ol), oc, om
        self.lines = list(self.lines)
        if isglobal:
            self.active = []

    # -- buffer ops --
    def node_addr(self, node):
        if node is not None:
            for i, n in enumerate(self.lines):
                if n is node:
                    return i + 1
        if self.lines:
            raise EdError('Invalid address')
        return 0

    def unset_active(self, nodes):
        if self.active is not None:
            for n in nodes:
                self.inactive.add(id(n))

    def delete_lines(self, frm, to):
        removed = self.lines[frm - 1:to]
        self.push_undo()
        self.unset_active(removed)
        del self.lines[frm - 1:to]
        self.current = frm - 1
        self.modified = True

    def insert_texts(self, addr, texts):
        nodes = [Node(t) for t in texts]
        self.lines[addr:addr] = nodes
        if nodes:
            self.push_undo()
            self.modified = True
        self.current = addr + len(nodes)

    def inc_current(self):
        self.current += 1
        if self.current > self.last:
            self.current = self.last

    # -- helpers --
    def check_addr_range(self, n, m):
        if self.addr_cnt == 0:
            self.first_addr = n
            self.second_addr = m
        if (self.first_addr < 1 or self.first_addr > self.second_addr
                or self.second_addr > self.last):
            raise EdError('Invalid address')

    def check_addr_range2(self):
        self.check_addr_range(self.current, self.current)

    def check_second_addr(self, addr):
        if self.addr_cnt == 0:
            self.second_addr = addr
        if self.second_addr < 1 or self.second_addr > self.last:
            raise EdError('Invalid address')

    def unexpected_address(self):
        if self.addr_cnt > 0:
            raise EdError('Unexpected address')

    def unexpected_suffix(self, b):
        if not isspace(b.cur()):
            raise EdError('Unexpected command suffix')

    def get_command_suffix(self, b):
        pflags = 0
        while True:
            ch = b.cur()
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
            b.i += 1
        if b.get() != '\n':
            raise EdError('Invalid command suffix')
        return pflags

    def parse_int(self, b):
        j = b.i
        while isdigit(b.cur()):
            b.i += 1
        v = int(b.s[j:b.i])
        if v > 2147483647:
            raise EdError('Number out of range')
        return v

    def trailing_escape(self, s, pos):
        # pos: index of the newline; count backslashes before it
        k = 0
        j = pos - 1
        while j >= 0 and s[j] == '\\':
            k += 1
            j -= 1
        return k % 2 == 1

    def get_extended_line(self, b, strip):
        s = b.s
        j = s.find('\n', b.i)
        if j < 0:
            return
        line = s[b.i:j + 1]
        if len(line) < 2 or not self.trailing_escape(line, len(line) - 1):
            return
        text = line[:-2] + ('' if strip else '\n')
        while True:
            nl = self.inp.readline()
            if nl is None:
                raise EdError('Unexpected end of file')
            text += nl
            if len(nl) < 2 or not self.trailing_escape(nl, len(nl) - 1):
                break
            text = text[:-2] + ('' if strip else '\n')
        b.s = text + '\0'
        b.i = 0

    def get_filename(self, b, traditional_f=False):
        b.skip_blanks()
        if b.cur() != '\n':
            self.get_extended_line(b, True)
        elif not traditional_f and not self.def_filename:
            raise EdError('No current filename')
        j = b.s.find('\n', b.i)
        if j < 0:
            j = len(b.s) - 1
        name = b.s[b.i:j]
        b.i = j
        while b.cur() == '\n':
            b.i += 1
        return name

    # -- regex handling --
    def compile_regex(self, pat, icase):
        try:
            rx = Regex(pat, self.ere, icase)
        except RegexError as e:
            self.last_regex = None
            raise EdError(str(e))
        except RecursionError:
            self.last_regex = None
            raise EdError('Regular expression too big')
        self.last_regex = rx
        return rx

    def parse_char_class(self, s, p):
        # p at char after '['; return index of closing ']' or -1
        if s[p] == '^':
            p += 1
        if s[p] == ']':
            p += 1
        while s[p] != ']' and s[p] != '\n' and s[p] != '\0':
            if s[p] == '[' and s[p + 1] in '.:=':
                d = s[p + 1]
                p += 2
                c = s[p] if p < len(s) else '\0'
                while not (s[p] == ']' and c == d):
                    c = s[p]
                    if c == '\n' or c == '\0':
                        return -1
                    p += 1
                    if p >= len(s):
                        return -1
            p += 1
            if p >= len(s):
                return -1
        return p if s[p] == ']' else -1

    def extract_pattern(self, b, delim):
        s = b.s
        p = b.i
        while s[p] != delim and s[p] != '\n' and s[p] != '\0':
            if s[p] == '[':
                q = self.parse_char_class(s, p + 1)
                if q < 0:
                    raise EdError('Unbalanced brackets ([])')
                p = q
            elif s[p] == '\\':
                p += 1
                if s[p] == '\n' or s[p] == '\0':
                    raise EdError('Trailing backslash (\\)')
            p += 1
        pat = s[b.i:p]
        b.i = p
        return pat

    def get_compiled_regex(self, b):
        delim = b.cur()
        if delim == ' ' or delim == '\n' or delim == '\0':
            raise EdError('Invalid pattern delimiter')
        b.i += 1
        pat = self.extract_pattern(b, delim)
        if b.cur() == delim:
            b.i += 1
        icase = False
        if b.cur() == 'I':
            icase = True
            b.i += 1
        if pat == '':
            if icase:
                raise EdError('Suffix I invalid with empty regex')
            if self.last_regex is None:
                raise EdError('No previous pattern')
            return self.last_regex
        return self.compile_regex(pat, icase)

    def next_matching_node_addr(self, b, forward):
        rx = self.get_compiled_regex(b)
        addr = self.current
        while True:
            if forward:
                addr = addr + 1 if addr < self.last else 0
            else:
                addr = addr - 1 if addr > 0 else self.last
            if addr:
                if rx.search(self.lines[addr - 1].text) is not None:
                    return addr
            if addr == self.current:
                break
        raise EdError('No match')

    def mark_addr(self, c):
        if not ('a' <= c <= 'z'):
            raise EdError('Invalid mark character')
        return self.node_addr(self.marks.get(c))

    # -- addresses --
    def next_addr(self, b):
        b.skip_blanks()
        hd = b.i
        addr = self.current
        first = True
        while True:
            c = b.cur()
            if isdigit(c):
                n = self.parse_int(b)
                addr = n if first else addr + n
            elif c in ' \t':
                b.skip_blanks()
                continue
            elif c == '+' or c == '-':
                b.i += 1
                if isdigit(b.cur()):
                    n = self.parse_int(b)
                    addr += -n if c == '-' else n
                else:
                    addr += -1 if c == '-' else 1
            elif c == '.' or c == '$':
                if not first:
                    raise EdError('Invalid address')
                b.i += 1
                addr = self.current if c == '.' else self.last
            elif c == '/' or c == '?':
                if not first:
                    raise EdError('Invalid address')
                addr = self.next_matching_node_addr(b, c == '/')
            elif c == "'":
                if not first:
                    raise EdError('Invalid address')
                b.i += 1
                addr = self.mark_addr(b.get())
            elif (c == ',' or c == ';' or c == '%') and first:
                b.i += 1
                self.addr_cnt += 1
                self.second_addr = self.current if c == ';' else 1
                a = self.next_addr(b)
                addr = self.last if a is None else a
            else:
                if b.i == hd:
                    return None
                if addr < 0 or addr > self.last:
                    raise EdError('Invalid address')
                return addr
            first = False

    def extract_addresses(self, b):
        self.addr_cnt = 0
        self.first_addr = self.second_addr = self.current
        a = None
        while True:
            a = self.next_addr(b)
            if a is None:
                break
            self.addr_cnt += 1
            self.first_addr = self.second_addr
            self.second_addr = a
            c = b.cur()
            if c != ',' and c != ';':
                break
            b.i += 1
            if c == ';':
                self.current = a
        self.addr_cnt = min(self.addr_cnt, 2)
        if self.addr_cnt == 1 or self.second_addr != a:
            self.first_addr = self.second_addr
        return self.addr_cnt

    def get_third_addr(self, b):
        o1, o2, oc = self.first_addr, self.second_addr, self.addr_cnt
        self.extract_addresses(b)
        addr = self.second_addr
        self.first_addr, self.second_addr, self.addr_cnt = o1, o2, oc
        if addr < 0 or addr > self.last:
            raise EdError('Invalid address')
        return addr

    # -- printing --
    def print_lines(self, frm, to, pflags):
        if frm == 0:
            raise EdError('Invalid address')
        for i in range(frm, to + 1):
            t = self.lines[i - 1].text
            if pflags & PF_N:
                self.write('%d\t' % i)
            if pflags & PF_L:
                self.write(self.list_text(t))
            else:
                self.write(t + '\n')
        self.current = to

    def list_text(self, t):
        out = []
        col = 0
        for ch in t:
            o = ord(ch)
            if ch == '\\':
                e = '\\\\'
            elif ch == '$':
                e = '\\$'
            elif 32 <= o < 127:
                e = ch
            elif ch in '\a\b\f\n\r\t\v':
                e = '\\' + 'abfnrtv'['\a\b\f\n\r\t\v'.index(ch)]
            else:
                e = '\\%03o' % o
            if col + len(e) >= 72:
                out.append('\\\n')
                col = 0
            out.append(e)
            col += len(e)
        out.append('$\n')
        return ''.join(out)

    # -- files --
    def read_file(self, name, addr):
        fn = strip_escapes(name)
        try:
            with open(fn, 'rb') as f:
                data = f.read()
        except (OSError, IOError) as e:
            sys.stderr.write('%s: %s\n' % (name, e.strerror if hasattr(e, 'strerror') else e))
            raise EdError('Cannot open input file')
        text = data.decode('latin-1')
        size = len(data)
        if text:
            if not text.endswith('\n'):
                text += '\n'
                sys.stderr.write('Newline appended\n')
            texts = text[:-1].split('\n')
        else:
            texts = []
        self.insert_texts(addr, texts)
        if not self.scripted:
            self.write('%d\n' % size)
        return len(texts)

    def write_file(self, name, mode, frm, to):
        fn = strip_escapes(name)
        if frm == 0:
            chunk = ''
        else:
            chunk = ''.join(n.text + '\n' for n in self.lines[frm - 1:to])
        data = chunk.encode('latin-1')
        try:
            with open(fn, mode) as f:
                f.write(data)
        except (OSError, IOError) as e:
            sys.stderr.write('%s: %s\n' % (name, e.strerror if hasattr(e, 'strerror') else e))
            raise EdError('Cannot open output file')
        if not self.scripted:
            self.write('%d\n' % len(data))
        return (to - frm + 1) if (frm and frm <= to) else 0

    # -- input mode --
    def append_lines(self, b, addr, insert, isglobal):
        self.current = addr
        while True:
            if not isglobal:
                line = self.inp.readline()
                if line is None:
                    return
            else:
                if b.cur() == '\0':
                    return
                j = b.s.find('\n', b.i)
                if j < 0:
                    return
                line = b.s[b.i:j + 1]
                b.i = j + 1
            if line == '.\n':
                return
            if insert:
                insert = False
                if self.current > 0:
                    self.current -= 1
            node = Node(line[:-1])
            self.lines.insert(self.current, node)
            self.current += 1
            self.push_undo()
            self.modified = True

    # -- substitution --
    def apply_template(self, tmpl, s, m):
        so, eo, groups = m
        out = []
        i = 0
        n = len(tmpl)
        while i < n:
            ch = tmpl[i]
            if ch == '&':
                out.append(s[so:eo])
            elif ch == '\\' and i + 1 < n:
                i += 1
                d = tmpl[i]
                if '1' <= d <= '9':
                    g = groups[int(d)]
                    if g is not None:
                        out.append(s[g[0]:g[1]])
                else:
                    out.append(d)
            else:
                out.append(ch)
            i += 1
        return ''.join(out)

    def replace_text(self, s, rx, g, snum, tmpl):
        m = rx.search(s, 0, False)
        if m is None:
            return None
        out = []
        pos = 0
        matchno = 0
        changed = False
        infloop = False
        n = len(s)
        while True:
            so, eo, groups = m
            matchno += 1
            if g or matchno == snum:
                out.append(s[pos:so])
                out.append(self.apply_template(tmpl, s, m))
                changed = True
            else:
                out.append(s[pos:eo])
            pos = eo
            if so == eo:
                if infloop:
                    raise EdError('Infinite substitution loop')
                infloop = True
            else:
                infloop = False
            if pos >= n:
                break
            if changed and not g:
                break
            m = rx.search(s, pos, True)
            if m is None:
                break
        out.append(s[pos:])
        if not changed:
            return None
        return ''.join(out)

    def search_and_replace(self, frm, to, g, snum, isglobal):
        rx = self.subst_regex
        tmpl = self.rbuf
        saved = self.current
        self.current = frm - 1
        found = False
        last_sub = None
        for _ in range(to - frm + 1):
            self.inc_current()
            node = self.lines[self.current - 1]
            new = self.replace_text(node.text, rx, g, snum, tmpl)
            if new is not None:
                addr = self.current
                self.delete_lines(addr, addr)
                texts = new.split('\n')
                nodes = [Node(t) for t in texts]
                self.lines[addr - 1:addr - 1] = nodes
                self.push_undo()
                self.modified = True
                self.current = addr - 1 + len(nodes)
                last_sub = self.current
                found = True
        if not found:
            self.current = saved
            if not isglobal:
                raise EdError('No match')
        else:
            self.current = last_sub

    def extract_replacement(self, b, delim, isglobal):
        if b.cur() == '%' and (b.peek(1) == delim or
                               (b.peek(1) == '\n' and (not isglobal or b.peek(2) == '\0'))):
            b.i += 1
            if self.rbuf is None:
                raise EdError('No previous substitution')
        else:
            out = []
            while b.cur() != delim:
                ch = b.cur()
                if ch == '\n' and (not isglobal or b.peek(1) == '\0'):
                    break
                if ch == '\0':
                    break
                out.append(ch)
                b.i += 1
                if ch == '\\':
                    d = b.cur()
                    out.append(d)
                    b.i += 1
                    if d == '\n' and not isglobal:
                        nl = self.inp.readline()
                        if nl is None:
                            raise EdError('Unexpected end of file')
                        b.s = nl + '\0'
                        b.i = 0
            self.rbuf = ''.join(out)
        if b.cur() == delim:
            b.i += 1
            return False
        return True

    def command_s(self, b, isglobal):
        self.check_addr_range2()
        SGG, SGP, SGR, SGF = 1, 2, 4, 8
        sflags = 0
        snum_new = None
        while True:
            ch = b.cur()
            if isdigit(ch):
                snum_new = self.parse_int(b)
                if snum_new <= 0:
                    raise EdError('Invalid command suffix')
                sflags |= SGF
            elif ch == '\n':
                sflags |= SGF
            elif ch == 'g':
                sflags |= SGG
                b.i += 1
            elif ch == 'p':
                sflags |= SGP
                b.i += 1
            elif ch == 'r':
                sflags |= SGR
                b.i += 1
            else:
                if sflags:
                    raise EdError('Invalid command suffix')
                break
            if b.cur() == '\n':
                break
        if sflags:
            if self.subst_regex is None or self.rbuf is None:
                raise EdError('No previous substitution')
            if snum_new is not None:
                self.s_snum = snum_new
                self.s_g = False
            if sflags & SGG:
                self.s_g = not self.s_g
                self.s_snum = 1
            if sflags & SGP:
                self.s_pflags ^= self.s_pmask
            if sflags & SGR:
                if self.last_regex is not None:
                    self.subst_regex = self.last_regex
            b.i += 1  # newline
        else:
            delim = b.cur()
            if delim == ' ' or delim == '\n' or delim == '\0':
                raise EdError('Invalid pattern delimiter')
            b.i += 1
            pat = self.extract_pattern(b, delim)
            if b.cur() != delim:
                raise EdError('Missing pattern delimiter')
            b.i += 1
            missing = self.extract_replacement(b, delim, isglobal)
            pflags = 0
            g = False
            snum = 0
            icase = False
            if missing:
                pflags = PF_P
                if b.cur() == '\n':
                    b.i += 1
            else:
                while True:
                    ch = b.cur()
                    if isdigit(ch):
                        if snum or g:
                            raise EdError('Invalid command suffix')
                        snum = self.parse_int(b)
                        if snum <= 0:
                            raise EdError('Invalid command suffix')
                        continue
                    if ch == 'g':
                        if g or snum:
                            raise EdError('Invalid command suffix')
                        g = True
                    elif ch in 'lnp':
                        f = {'l': PF_L, 'n': PF_N, 'p': PF_P}[ch]
                        if pflags & f:
                            raise EdError('Invalid command suffix')
                        pflags |= f
                    elif ch in 'Ii':
                        if icase:
                            raise EdError('Invalid command suffix')
                        icase = True
                    else:
                        break
                    b.i += 1
                if b.get() != '\n':
                    raise EdError('Invalid command suffix')
            if pat == '':
                if icase:
                    raise EdError('Suffix I invalid with empty regex')
                if self.last_regex is None:
                    raise EdError('No previous pattern')
                rx = self.last_regex
            else:
                rx = self.compile_regex(pat, icase)
            self.subst_regex = rx
            self.s_g = g
            self.s_snum = snum if snum else 1
            self.s_pflags = pflags
            self.s_pmask = pflags if pflags else PF_P
        if not isglobal:
            self.clear_undo_stack()
        self.search_and_replace(self.first_addr, self.second_addr,
                                self.s_g, self.s_snum, isglobal)
        return self.s_pflags

    # -- global --
    def exec_global(self, b):
        self.get_extended_line(b, False)
        cmd = b.s[b.i:]
        if cmd.endswith('\0'):
            cmd = cmd[:-1]
        self.clear_undo_stack()
        try:
            idx = 0
            while True:
                if self.active is None or idx >= len(self.active):
                    break
                node = self.active[idx]
                idx += 1
                if id(node) in self.inactive:
                    continue
                addr = None
                for i, n in enumerate(self.lines):
                    if n is node:
                        addr = i + 1
                        break
                if addr is None:
                    continue
                self.current = addr
                gb = Buf(cmd)
                while gb.cur() != '\0':
                    st = self.exec_command(gb, 0, True)
                    if st != 0:
                        return st
        finally:
            self.active = None
            self.inactive = set()
        return 0

    # -- command dispatcher --
    def exec_command(self, b, prev_status, isglobal):
        pflags = 0
        self.extract_addresses(b)
        b.skip_blanks()
        c = b.get()
        if c == 'a' or c == 'i':
            pflags = self.get_command_suffix(b)
            if not isglobal:
                self.clear_undo_stack()
            self.append_lines(b, self.second_addr, c == 'i', isglobal)
        elif c == 'c':
            self.check_addr_range2()
            pflags = self.get_command_suffix(b)
            if not isglobal:
                self.clear_undo_stack()
            self.delete_lines(self.first_addr, self.second_addr)
            self.inc_current()
            self.append_lines(b, self.current, self.current >= self.first_addr, isglobal)
        elif c == 'd':
            self.check_addr_range2()
            pflags = self.get_command_suffix(b)
            if not isglobal:
                self.clear_undo_stack()
            self.delete_lines(self.first_addr, self.second_addr)
            self.inc_current()
        elif c == 'e' or c == 'E':
            if c == 'e' and self.modified and prev_status != EMOD:
                return EMOD
            self.unexpected_address()
            self.unexpected_suffix(b)
            fn = self.get_filename(b)
            if self.lines:
                self.delete_lines(1, self.last)
            if fn:
                self.def_filename = fn
            self.read_file(fn if fn else self.def_filename, 0)
            self.reset_undo_state()
            self.modified = False
        elif c == 'f':
            self.unexpected_address()
            self.unexpected_suffix(b)
            fn = self.get_filename(b)
            if fn:
                self.def_filename = fn
            self.write(strip_escapes(self.def_filename) + '\n')
        elif c == 'g' or c == 'v':
            if isglobal:
                raise EdError('Cannot nest global commands')
            self.check_addr_range(1, self.last)
            rx = self.get_compiled_regex(b)
            want = (c == 'g')
            act = []
            for node in self.lines[self.first_addr - 1:self.second_addr]:
                if (rx.search(node.text) is not None) == want:
                    act.append(node)
            self.active = act
            self.inactive = set()
            st = self.exec_global(b)
            if st != 0:
                return st
        elif c == 'j':
            self.check_addr_range(self.current, self.current + 1)
            pflags = self.get_command_suffix(b)
            if not isglobal:
                self.clear_undo_stack()
            if self.first_addr < self.second_addr:
                frm, to = self.first_addr, self.second_addr
                text = ''.join(n.text for n in self.lines[frm - 1:to])
                self.delete_lines(frm, to)
                self.insert_texts(frm - 1, [text])
                self.current = frm
        elif c == 'k':
            ch = b.get()
            if self.second_addr == 0:
                raise EdError('Invalid address')
            pflags = self.get_command_suffix(b)
            if not ('a' <= ch <= 'z'):
                raise EdError('Invalid mark character')
            self.marks[ch] = self.lines[self.second_addr - 1]
        elif c == 'm':
            self.check_addr_range2()
            addr = self.get_third_addr(b)
            if self.first_addr <= addr < self.second_addr:
                raise EdError('Invalid destination')
            pflags = self.get_command_suffix(b)
            if not isglobal:
                self.clear_undo_stack()
            frm, to = self.first_addr, self.second_addr
            if addr == frm - 1 or addr == to:
                self.current = to
            else:
                chunk = self.lines[frm - 1:to]
                del self.lines[frm - 1:to]
                cnt = len(chunk)
                if addr < frm:
                    self.lines[addr:addr] = chunk
                    self.current = addr + cnt
                else:
                    pos = addr - cnt
                    self.lines[pos:pos] = chunk
                    self.current = addr
                self.push_undo()
            self.modified = True
        elif c == 'n' or c == 'p' or c == 'l':
            self.check_addr_range2()
            pflags = self.get_command_suffix(b)
            f = {'n': PF_N, 'p': PF_P, 'l': PF_L}[c]
            self.print_lines(self.first_addr, self.second_addr, pflags | f)
            pflags = 0
        elif c == 'q' or c == 'Q':
            self.unexpected_address()
            self.get_command_suffix(b)
            if c == 'Q' or not self.modified or prev_status == EMOD:
                return QUIT
            return EMOD
        elif c == 'r':
            self.unexpected_suffix(b)
            if self.addr_cnt == 0:
                self.second_addr = self.last
            fn = self.get_filename(b)
            if not self.def_filename:
                self.def_filename = fn
            if not isglobal:
                self.clear_undo_stack()
            self.read_file(fn if fn else self.def_filename, self.second_addr)
        elif c == 's':
            pflags = self.command_s(b, isglobal)
        elif c == 't':
            self.check_addr_range2()
            addr = self.get_third_addr(b)
            pflags = self.get_command_suffix(b)
            if not isglobal:
                self.clear_undo_stack()
            texts = [n.text for n in self.lines[self.first_addr - 1:self.second_addr]]
            self.insert_texts(addr, texts)
        elif c == 'u':
            self.unexpected_address()
            pflags = self.get_command_suffix(b)
            self.undo(isglobal)
        elif c == 'w' or c == 'W':
            n = b.cur()
            if n == 'q':
                b.i += 1
            self.unexpected_suffix(b)
            fn = self.get_filename(b)
            if self.addr_cnt == 0 and self.last == 0:
                self.first_addr = self.second_addr = 0
            else:
                self.check_addr_range(1, self.last)
            if not self.def_filename:
                self.def_filename = fn
            cnt = self.write_file(fn if fn else self.def_filename,
                                  'ab' if c == 'W' else 'wb',
                                  self.first_addr, self.second_addr)
            if cnt == self.last:
                self.modified = False
            if n == 'q':
                if self.modified and prev_status != EMOD:
                    return EMOD
                return QUIT
        elif c == '=':
            pflags = self.get_command_suffix(b)
            self.write('%d\n' % (self.second_addr if self.addr_cnt else self.last))
        elif c == '#':
            while b.cur() != '\n' and b.cur() != '\0':
                b.i += 1
            b.i += 1
        elif c == '\n':
            self.check_second_addr(self.current + (0 if isglobal else 1))
            self.print_lines(self.second_addr, self.second_addr, 0)
        else:
            raise EdError('Unknown command')
        if pflags:
            self.print_lines(self.current, self.current, pflags)
        return 0

    # -- main loop --
    def main_loop(self, stdin_regular):
        status = 0
        err_status = 0
        while True:
            line = self.inp.readline()
            if line is None:
                if not self.modified or status == EMOD:
                    status = QUIT
                else:
                    status = EMOD
            else:
                try:
                    status = self.exec_command(Buf(line), status, False)
                except EdError:
                    status = ERR
                except RecursionError:
                    status = ERR
            if status == 0:
                continue
            if status == QUIT:
                return err_status
            self.write('?\n')
            if not self.loose:
                err_status = 1
            if stdin_regular:
                return err_status


def main(argv):
    ere = loose = scripted = False
    filename = None
    for a in argv:
        if len(a) > 1 and a[0] == '-':
            for ch in a[1:]:
                if ch == 'E':
                    ere = True
                elif ch == 'l':
                    loose = True
                elif ch == 's':
                    scripted = True
                else:
                    sys.stderr.write('ed: invalid option -- %s\n' % ch)
                    return 1
        else:
            filename = a
    try:
        st = os.fstat(0)
        stdin_regular = (st.st_mode & 0o170000) == 0o100000
    except OSError:
        stdin_regular = False
    ed = Ed(ere, loose, scripted)
    try:
        if filename is not None:
            ed.def_filename = filename
            try:
                ed.read_file(filename, 0)
            except EdError:
                pass
            ed.modified = False
            ed.reset_undo_state()
        rc = ed.main_loop(stdin_regular)
    finally:
        ed.flush()
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
