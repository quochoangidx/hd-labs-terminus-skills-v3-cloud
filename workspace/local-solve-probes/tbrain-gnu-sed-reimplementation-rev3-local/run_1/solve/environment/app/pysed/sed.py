"""pysed: a GNU sed 4.9 replacement in pure Python.

Usage: python3 /app/pysed/sed.py [OPTION]... {script-only-if-no-other-script} [input-file]...
"""

import sys

# ---------------------------------------------------------------------------
# Regular expressions: POSIX leftmost-longest matcher (Pike VM)
# ---------------------------------------------------------------------------

ALL = frozenset(chr(c) for c in range(256))
WORD = frozenset("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_")
SPACE = frozenset(" \t\n\v\f\r")

CLASSES = {
    'alpha': frozenset(c for c in ALL if ('a' <= c <= 'z') or ('A' <= c <= 'Z')),
    'digit': frozenset("0123456789"),
    'alnum': frozenset(c for c in ALL if ('a' <= c <= 'z') or ('A' <= c <= 'Z') or ('0' <= c <= '9')),
    'upper': frozenset(c for c in ALL if 'A' <= c <= 'Z'),
    'lower': frozenset(c for c in ALL if 'a' <= c <= 'z'),
    'space': SPACE,
    'blank': frozenset(" \t"),
    'punct': frozenset(c for c in ALL if 33 <= ord(c) <= 126 and not c.isalnum()),
    'print': frozenset(c for c in ALL if 32 <= ord(c) <= 126),
    'graph': frozenset(c for c in ALL if 33 <= ord(c) <= 126),
    'cntrl': frozenset(c for c in ALL if ord(c) < 32 or ord(c) == 127),
    'xdigit': frozenset("0123456789ABCDEFabcdef"),
}

CTRL_ESC = {'a': '\a', 'f': '\f', 'n': '\n', 'r': '\r', 't': '\t', 'v': '\v'}


class RegexError(Exception):
    pass


class RParser:
    def __init__(self, pat, ere):
        self.p = pat
        self.n = len(pat)
        self.i = 0
        self.ere = ere
        self.ng = 0

    def parse(self):
        node = self.alt(0)
        if self.i < self.n:
            raise RegexError("unmatched")
        return node

    def at_alt(self):
        p, i = self.p, self.i
        if self.ere:
            return i < self.n and p[i] == '|'
        return p.startswith('\\|', i)

    def at_close(self, depth):
        if depth == 0:
            return False
        p, i = self.p, self.i
        if self.ere:
            return i < self.n and p[i] == ')'
        return p.startswith('\\)', i)

    def alt(self, depth):
        branches = [self.concat(depth)]
        while self.i < self.n and self.at_alt():
            self.i += 1 if self.ere else 2
            branches.append(self.concat(depth))
        if len(branches) == 1:
            return branches[0]
        return ('alt', branches)

    def bre_dollar_is_anchor(self, j):
        p = self.p
        return j >= self.n or p.startswith('\\)', j) or p.startswith('\\|', j)

    def parse_interval(self, j):
        """Parse interval body starting at j (after '{' or '\\{').
        Returns (min, max, newpos) or None."""
        p, n = self.p, self.n
        k = j
        a = ''
        while k < n and p[k].isdigit():
            a += p[k]
            k += 1
        b = None
        comma = False
        if k < n and p[k] == ',':
            comma = True
            k += 1
            bb = ''
            while k < n and p[k].isdigit():
                bb += p[k]
                k += 1
            b = bb
        if self.ere:
            if k < n and p[k] == '}':
                k += 1
            else:
                return None
        else:
            if p.startswith('\\}', k):
                k += 2
            else:
                return None
        if a == '' and not comma:
            return None
        mn = int(a) if a else 0
        if comma:
            mx = int(b) if b else None
        else:
            mx = mn
        if mx is not None and mx < mn:
            return None
        return mn, mx, k

    def concat(self, depth):
        items = []
        p = self.p
        start = True  # at a position where '*' is literal (BRE) / '^' anchor
        while self.i < self.n and not self.at_alt() and not self.at_close(depth):
            c = p[self.i]
            # quantifiers
            q = None
            if c == '*':
                q = (0, None, self.i + 1)
            elif self.ere and c == '+':
                q = (1, None, self.i + 1)
            elif self.ere and c == '?':
                q = (0, 1, self.i + 1)
            elif self.ere and c == '{':
                r = self.parse_interval(self.i + 1)
                if r is not None:
                    q = r
            elif not self.ere and c == '\\' and self.i + 1 < self.n:
                d = p[self.i + 1]
                if d == '+':
                    q = (1, None, self.i + 2)
                elif d == '?':
                    q = (0, 1, self.i + 2)
                elif d == '{':
                    r = self.parse_interval(self.i + 2)
                    if r is not None:
                        q = r
            if q is not None:
                if start or not items:
                    if c == '\\':
                        # literal of the escaped char
                        items.append(('set', frozenset(p[self.i + 1])))
                        self.i += 2
                    else:
                        items.append(('set', frozenset(c)))
                        self.i += 1
                    start = False
                    continue
                mn, mx, ni = q
                items[-1] = ('rep', items[-1], mn, mx)
                self.i = ni
                continue
            if c == '^' and (self.ere or start):
                items.append(('assert', 'bol'))
                self.i += 1
                start = True
                continue
            if c == '$' and (self.ere or self.bre_dollar_is_anchor(self.i + 1)):
                items.append(('assert', 'eol'))
                self.i += 1
                start = False
                continue
            start = False
            if c == '.':
                items.append(('set', ALL))
                self.i += 1
            elif c == '[':
                items.append(self.bracket())
            elif self.ere and c == '(':
                self.i += 1
                items.append(self.group(depth))
            elif c == '\\':
                if self.i + 1 >= self.n:
                    items.append(('set', frozenset('\\')))
                    self.i += 1
                    continue
                d = p[self.i + 1]
                self.i += 2
                if not self.ere and d == '(':
                    items.append(self.group(depth))
                    start = False
                elif d == 'w':
                    items.append(('set', WORD))
                elif d == 'W':
                    items.append(('set', ALL - WORD))
                elif d == 's':
                    items.append(('set', SPACE))
                elif d == 'S':
                    items.append(('set', ALL - SPACE))
                elif d == 'b':
                    items.append(('assert', 'wordb'))
                elif d == 'B':
                    items.append(('assert', 'nwordb'))
                elif d == '<':
                    items.append(('assert', 'wbeg'))
                elif d == '>':
                    items.append(('assert', 'wend'))
                elif d == '`':
                    items.append(('assert', 'bol'))
                elif d == "'":
                    items.append(('assert', 'eol'))
                elif d in CTRL_ESC:
                    items.append(('set', frozenset(CTRL_ESC[d])))
                elif d.isdigit() and d != '0':
                    items.append(('backref', int(d)))
                else:
                    items.append(('set', frozenset(d)))
            else:
                items.append(('set', frozenset(c)))
                self.i += 1
        if len(items) == 1:
            return items[0]
        return ('cat', items)

    def group(self, depth):
        self.ng += 1
        idx = self.ng
        node = self.alt(depth + 1)
        if not self.at_close(depth + 1):
            raise RegexError("unmatched (")
        self.i += 1 if self.ere else 2
        return ('group', idx, node)

    def bracket(self):
        p, n = self.p, self.n
        i = self.i + 1
        neg = False
        if i < n and p[i] == '^':
            neg = True
            i += 1
        chars = set()
        first = True
        while True:
            if i >= n:
                raise RegexError("unterminated [")
            c = p[i]
            if c == ']' and not first:
                i += 1
                break
            first = False
            lo = None
            if c == '[' and i + 1 < n and p[i + 1] in ':.=':
                kind = p[i + 1]
                end = p.find(kind + ']', i + 2)
                if end < 0:
                    lo = '['
                    i += 1
                else:
                    name = p[i + 2:end]
                    i = end + 2
                    if kind == ':':
                        if name not in CLASSES:
                            raise RegexError("bad class")
                        chars |= CLASSES[name]
                        continue
                    else:
                        lo = name[:1] if name else ''
                        if not lo:
                            continue
            elif c == '\\' and i + 1 < n and p[i + 1] in CTRL_ESC:
                lo = CTRL_ESC[p[i + 1]]
                i += 2
            else:
                lo = c
                i += 1
            # range?
            if i + 1 < n and p[i] == '-' and p[i + 1] != ']':
                j = i + 1
                if p[j] == '[' and j + 1 < n and p[j + 1] in '.=':
                    kind = p[j + 1]
                    end = p.find(kind + ']', j + 2)
                    hi = p[j + 2:end][:1]
                    j = end + 2
                elif p[j] == '\\' and j + 1 < n and p[j + 1] in CTRL_ESC:
                    hi = CTRL_ESC[p[j + 1]]
                    j += 2
                else:
                    hi = p[j]
                    j += 1
                for o in range(ord(lo), ord(hi) + 1):
                    chars.add(chr(o))
                i = j
            else:
                chars.add(lo)
        self.i = i
        s = frozenset(chars)
        if neg:
            s = ALL - s
        return ('set', s)


class Regex:
    def __init__(self, pattern, ere):
        self.pattern = pattern
        parser = RParser(pattern, ere)
        ast = parser.parse()
        self.ngroups = parser.ng
        self.prog = []
        self._emit(ast)
        self.prog.append(('M',))
        self._compute_first()

    def _emit(self, node):
        prog = self.prog
        t = node[0]
        if t == 'set':
            prog.append(['C', node[1]])
        elif t == 'cat':
            for x in node[1]:
                self._emit(x)
        elif t == 'alt':
            jmps = []
            alts = node[1]
            for k, a in enumerate(alts):
                if k < len(alts) - 1:
                    sp = len(prog)
                    prog.append(['S', sp + 1, None])
                    self._emit(a)
                    jmps.append(len(prog))
                    prog.append(['J', None])
                    prog[sp][2] = len(prog)
                else:
                    self._emit(a)
            for j in jmps:
                prog[j][1] = len(prog)
        elif t == 'group':
            prog.append(['V', 2 * node[1]])
            self._emit(node[2])
            prog.append(['V', 2 * node[1] + 1])
        elif t == 'rep':
            sub, mn, mx = node[1], node[2], node[3]
            for _ in range(mn):
                self._emit(sub)
            if mx is None:
                L = len(prog)
                prog.append(['S', L + 1, None])
                self._emit(sub)
                prog.append(['J', L])
                prog[L][2] = len(prog)
            else:
                ends = []
                for _ in range(mx - mn):
                    sp = len(prog)
                    prog.append(['S', sp + 1, None])
                    ends.append(sp)
                    self._emit(sub)
                for sp in ends:
                    prog[sp][2] = len(prog)
        elif t == 'assert':
            prog.append(['A', node[1]])
        elif t == 'backref':
            prog.append(['B', node[1]])
        else:
            raise RegexError("bad node")

    def _compute_first(self):
        # set of chars which can start a non-empty match; None if the
        # regex can match empty (or starts with a backreference)
        prog = self.prog
        seen = set()
        stack = [0]
        first = set()
        while stack:
            pc = stack.pop()
            if pc in seen:
                continue
            seen.add(pc)
            op = prog[pc]
            k = op[0]
            if k == 'C':
                first |= op[1]
            elif k == 'S':
                stack.append(op[1])
                stack.append(op[2])
            elif k == 'J':
                stack.append(op[1])
            elif k in ('V', 'A'):
                stack.append(pc + 1)
            else:
                self.first = None
                return
        self.first = frozenset(first)

    def search(self, s, pos):
        """Leftmost-longest search starting at pos. Returns caps list
        [s0, e0, s1, e1, ...] (None for unset) or None."""
        prog = self.prog
        n = len(s)
        ncap = 2 * (self.ngroups + 1)
        init_caps = (None,) * ncap
        first = self.first
        best = None  # (start, end, caps)
        clist = []   # list of (pc, start, caps)
        i = pos
        while True:
            if not clist:
                if best is not None:
                    break
                if i > n:
                    break
                if first is not None:
                    while i < n and s[i] not in first:
                        i += 1
                    if i >= n:
                        break
            # compute closure at position i
            prev = s[i - 1] if i > 0 else None
            nxt = s[i] if i < n else None
            pw = prev is not None and prev in WORD
            nw = nxt is not None and nxt in WORD
            visited = set()
            runq = []
            threads = clist
            if best is None:
                threads = clist + [(0, i, init_caps)]
            for (pc0, st, caps0) in threads:
                if best is not None and st > best[0]:
                    continue
                stack = [(pc0, caps0)]
                while stack:
                    pc, caps = stack.pop()
                    if pc in visited:
                        continue
                    visited.add(pc)
                    op = prog[pc]
                    k = op[0]
                    if k == 'C':
                        runq.append((op[1], pc + 1, st, caps))
                    elif k == 'S':
                        stack.append((op[2], caps))
                        stack.append((op[1], caps))
                    elif k == 'J':
                        stack.append((op[1], caps))
                    elif k == 'V':
                        idx = op[1]
                        caps = caps[:idx] + (i,) + caps[idx + 1:]
                        stack.append((pc + 1, caps))
                    elif k == 'A':
                        a = op[1]
                        if a == 'bol':
                            ok = i == 0
                        elif a == 'eol':
                            ok = i == n
                        elif a == 'wordb':
                            ok = pw != nw
                        elif a == 'nwordb':
                            ok = pw == nw
                        elif a == 'wbeg':
                            ok = (not pw) and nw
                        else:
                            ok = pw and not nw
                        if ok:
                            stack.append((pc + 1, caps))
                    elif k == 'B':
                        # back-reference: not supported by the NFA; ignore
                        idx = op[1]
                        bs, be = caps[2 * idx], caps[2 * idx + 1]
                        if bs is not None and be == i and False:
                            pass
                    else:  # match
                        if best is None or st < best[0] or (st == best[0] and i > best[1]):
                            best = (st, i, caps)
            if i >= n:
                break
            ch = s[i]
            nlist = []
            for (cset, npc, st, caps) in runq:
                if best is not None and st > best[0]:
                    continue
                if ch in cset:
                    nlist.append((npc, st, caps))
            clist = nlist
            i += 1
        if best is None:
            return None
        st, en, caps = best
        res = list(caps)
        res[0] = st
        res[1] = en
        for g in range(1, self.ngroups + 1):
            if res[2 * g] is None or res[2 * g + 1] is None:
                res[2 * g] = res[2 * g + 1] = None
        return res


# ---------------------------------------------------------------------------
# Script parsing
# ---------------------------------------------------------------------------

class SedError(Exception):
    pass


class Addr:
    __slots__ = ('kind', 'n1', 'n2', 'rx')

    def __init__(self, kind, n1=0, n2=0, rx=None):
        self.kind = kind
        self.n1 = n1
        self.n2 = n2
        self.rx = rx


class Cmd:
    def __init__(self):
        self.a1 = None
        self.a2 = None
        self.neg = False
        self.name = None
        self.state = 0  # 0 inactive, 1 active
        self.range_end = 0
        self.text = ''
        self.label = ''
        self.target = None
        self.end = None
        self.rx = None
        self.repl = None
        self.glob = False
        self.pflag = 0
        self.numb = 1
        self.code = 0
        self.ymap = None
        self.initial_state = 0


class ScriptParser:
    def __init__(self, text, ere):
        self.s = text
        self.n = len(text)
        self.i = 0
        self.ere = ere
        self.cmds = []
        self.regex_cache = {}

    def peek(self):
        return self.s[self.i] if self.i < self.n else None

    def getc(self):
        if self.i < self.n:
            c = self.s[self.i]
            self.i += 1
            return c
        self.i += 1
        return None

    def skip_blank(self):
        while self.i < self.n and self.s[self.i] in ' \t':
            self.i += 1

    def skip_ws(self):
        while self.i < self.n and self.s[self.i] in ' \t\n\r\v\f':
            self.i += 1

    def compile_regex(self, pat):
        if pat == '':
            return None
        key = pat
        if key not in self.regex_cache:
            self.regex_cache[key] = Regex(pat, self.ere)
        return self.regex_cache[key]

    def match_slash(self, delim, regex):
        out = []
        while True:
            c = self.getc()
            if c is None:
                raise SedError("unterminated")
            if c == delim:
                return ''.join(out)
            if c == '\\':
                d = self.getc()
                if d is None:
                    raise SedError("unterminated")
                if d == delim:
                    out.append(d)
                elif d == 'n' and regex:
                    out.append('\n')
                elif d == '\n':
                    out.append('\n')
                else:
                    out.append('\\')
                    out.append(d)
            elif c == '\n' and regex:
                raise SedError("unterminated address regex")
            else:
                out.append(c)

    def read_number(self):
        st = self.i
        while self.i < self.n and self.s[self.i].isdigit():
            self.i += 1
        return int(self.s[st:self.i])

    def parse_addr(self):
        c = self.peek()
        if c is None:
            return None
        if c.isdigit():
            num = self.read_number()
            if self.peek() == '~':
                self.i += 1
                step = self.read_number() if (self.peek() or '').isdigit() else 0
                return Addr('step', num, step)
            return Addr('line', num)
        if c == '$':
            self.i += 1
            return Addr('last')
        if c == '/' or c == '\\':
            self.i += 1
            delim = '/'
            if c == '\\':
                delim = self.getc()
            pat = self.match_slash(delim, True)
            rx = self.compile_regex(pat)
            # modifiers I / M (unused) tolerated
            while self.peek() in ('I', 'M'):
                self.i += 1
            return Addr('re', rx=rx)
        return None

    def read_label(self):
        self.skip_blank()
        st = self.i
        while self.i < self.n and self.s[self.i] not in ';\n}' and self.s[self.i] not in ' \t\r\v\f':
            self.i += 1
        lab = self.s[st:self.i]
        return lab

    def end_of_cmd(self):
        self.skip_blank()
        c = self.peek()
        if c in (';', '\n'):
            self.i += 1

    def read_text(self):
        # after a/i/c
        self.skip_blank()
        raw = []
        c = self.peek()
        if c is None:
            return ''
        if c == '\\':
            self.i += 1
            ch = self.getc()
            if ch is None:
                return ''
            if ch != '\n':
                raw.append(ch)
        while True:
            ch = self.getc()
            if ch is None or ch == '\n':
                break
            if ch == '\\':
                d = self.getc()
                if d is None:
                    break
                raw.append('\\' + d)
            else:
                raw.append(ch)
        out = []
        for piece in raw:
            if len(piece) == 2:
                d = piece[1]
                if d in CTRL_ESC:
                    out.append(CTRL_ESC[d])
                else:
                    out.append(d)
            else:
                out.append(piece)
        return ''.join(out) + '\n'

    def parse_repl(self, text):
        parts = []
        buf = []
        i = 0
        n = len(text)
        while i < n:
            c = text[i]
            if c == '\\' and i + 1 < n:
                d = text[i + 1]
                i += 2
                if d.isdigit():
                    if buf:
                        parts.append(''.join(buf))
                        buf = []
                    parts.append(int(d))
                elif d in CTRL_ESC:
                    buf.append(CTRL_ESC[d])
                elif d == '\n':
                    buf.append('\n')
                else:
                    buf.append(d)
            elif c == '&':
                if buf:
                    parts.append(''.join(buf))
                    buf = []
                parts.append(0)
                i += 1
            else:
                buf.append(c)
                i += 1
        if buf:
            parts.append(''.join(buf))
        return parts

    def parse_y(self, delim):
        def unesc(t):
            out = []
            i = 0
            while i < len(t):
                if t[i] == '\\' and i + 1 < len(t):
                    d = t[i + 1]
                    if d == '\\':
                        out.append('\\')
                    elif d in CTRL_ESC:
                        out.append(CTRL_ESC[d])
                    else:
                        out.append('\\')
                        out.append(d)
                    i += 2
                else:
                    out.append(t[i])
                    i += 1
            return out
        a = unesc(self.match_slash(delim, False))
        b = unesc(self.match_slash(delim, False))
        if len(a) != len(b):
            raise SedError("strings for y command are different lengths")
        m = {}
        for x, y in zip(a, b):
            m[x] = y
        return m

    def parse(self):
        cmds = self.cmds
        stack = []
        while True:
            while self.i < self.n and self.s[self.i] in ' \t\n\r\v\f;':
                self.i += 1
            if self.i >= self.n:
                break
            c = self.peek()
            if c == '#':
                while self.i < self.n and self.s[self.i] != '\n':
                    self.i += 1
                continue
            cmd = Cmd()
            a1 = self.parse_addr()
            if a1 is not None:
                cmd.a1 = a1
                self.skip_blank()
                if self.peek() == ',':
                    self.i += 1
                    self.skip_blank()
                    c2 = self.peek()
                    if c2 == '+':
                        self.i += 1
                        cmd.a2 = Addr('plus', self.read_number())
                    elif c2 == '~':
                        self.i += 1
                        cmd.a2 = Addr('mult', self.read_number())
                    else:
                        a2 = self.parse_addr()
                        if a2 is None:
                            raise SedError("unexpected ,")
                        if a2.kind == 'step':
                            a2 = Addr('line', a2.n1)
                        cmd.a2 = a2
                    if a1.kind == 'line' and a1.n1 == 0:
                        cmd.initial_state = 1
                        cmd.state = 1
            self.skip_blank()
            while self.peek() == '!':
                cmd.neg = True
                self.i += 1
                self.skip_blank()
            name = self.getc()
            if name is None:
                raise SedError("missing command")
            cmd.name = name
            if name == '{':
                stack.append(len(cmds))
                cmds.append(cmd)
                continue
            if name == '}':
                if not stack:
                    raise SedError("unexpected }")
                op = stack.pop()
                cmds[op].end = len(cmds)
                cmds.append(cmd)
                self.end_of_cmd()
                continue
            if name in '=dDgGhHnNpPxzlF':
                if name == 'l':
                    self.skip_blank()
                    if (self.peek() or '').isdigit():
                        cmd.code = self.read_number()
                    else:
                        cmd.code = None
                self.end_of_cmd()
            elif name in 'qQ':
                self.skip_blank()
                if (self.peek() or '').isdigit():
                    cmd.code = self.read_number()
                self.end_of_cmd()
            elif name in 'aic':
                cmd.text = self.read_text()
            elif name == ':':
                lab = self.read_label()
                if not lab:
                    raise SedError("\":\" lacks a label")
                cmd.label = lab
                self.end_of_cmd()
            elif name in 'btT':
                cmd.label = self.read_label()
                self.end_of_cmd()
            elif name == 's':
                delim = self.getc()
                pat = self.match_slash(delim, True)
                rep = self.match_slash(delim, False)
                cmd.rx = self.compile_regex(pat)
                cmd.repl = self.parse_repl(rep)
                while True:
                    f = self.peek()
                    if f == 'g':
                        cmd.glob = True
                        self.i += 1
                    elif f == 'p':
                        cmd.pflag += 1
                        self.i += 1
                    elif f is not None and f.isdigit():
                        cmd.numb = self.read_number()
                    elif f in ('i', 'I', 'm', 'M', 'e'):
                        self.i += 1
                    elif f == 'w':
                        self.i += 1
                        while self.i < self.n and self.s[self.i] != '\n':
                            self.i += 1
                    else:
                        break
                self.end_of_cmd()
            elif name == 'y':
                delim = self.getc()
                cmd.ymap = self.parse_y(delim)
                self.end_of_cmd()
            elif name in 'rRwWe':
                # unsupported file commands: read filename to end of line
                self.skip_blank()
                st = self.i
                while self.i < self.n and self.s[self.i] != '\n':
                    self.i += 1
                cmd.label = self.s[st:self.i]
            elif name == 'v':
                self.read_label()
                self.end_of_cmd()
                cmd.name = '#'
            else:
                raise SedError("unknown command: `%s'" % name)
            cmds.append(cmd)
        if stack:
            raise SedError("unmatched `{'")
        labels = {}
        for idx, cmd in enumerate(cmds):
            if cmd.name == ':':
                if cmd.label in labels:
                    raise SedError("duplicate label")
                labels[cmd.label] = idx
        for cmd in cmds:
            if cmd.name in 'btT':
                if cmd.label == '':
                    cmd.target = len(cmds)
                elif cmd.label in labels:
                    cmd.target = labels[cmd.label]
                else:
                    raise SedError("can't find label for jump to `%s'" % cmd.label)
        return cmds


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------

class Input:
    def __init__(self, files, separate):
        self.files = files if files else ['-']
        self.separate = separate
        self.fidx = -1
        self.lines = []
        self.pos = 0
        self.cache = {}
        self.bad = 0
        self.lineno = 0
        self.stdin_data = None
        self.on_new_file = None
        self.started = False
        self.curname = '-'

    def load(self, idx):
        if idx in self.cache:
            return self.cache[idx]
        name = self.files[idx]
        data = None
        if name == '-':
            if self.stdin_data is None:
                self.stdin_data = sys.stdin.buffer.read().decode('latin-1')
                data = self.stdin_data
            else:
                data = ''
        else:
            try:
                with open(name, 'rb') as f:
                    data = f.read().decode('latin-1')
            except (IsADirectoryError,) as e:
                sys.stderr.write("sed: couldn't edit %s: not a regular file\n" % name)
                self.bad += 1
                data = None
            except OSError as e:
                sys.stderr.write("sed: can't read %s: %s\n" % (name, e.strerror))
                self.bad += 1
                data = None
        if data is None:
            lines = []
        else:
            lines = data.split('\n')
            if lines and lines[-1] == '':
                lines.pop()
        self.cache[idx] = lines
        return lines

    def next_line(self):
        while self.pos >= len(self.lines):
            if self.fidx + 1 >= len(self.files):
                return None
            self.fidx += 1
            self.lines = self.load(self.fidx)
            self.pos = 0
            self.curname = self.files[self.fidx]
            if self.separate and self.started:
                self.lineno = 0
                if self.on_new_file:
                    self.on_new_file()
        self.started = True
        line = self.lines[self.pos]
        self.pos += 1
        self.lineno += 1
        return line

    def has_next(self):
        if self.pos < len(self.lines):
            return True
        # need to look into following files (also in -s mode, for n/N)
        j = self.fidx + 1
        while j < len(self.files):
            if self.load(j):
                return True
            j += 1
        return False

    def is_last(self):
        if self.pos < len(self.lines):
            return False
        if self.separate:
            return True
        return not self.has_next()


class Quit(Exception):
    def __init__(self, code):
        self.code = code


class Sed:
    def __init__(self, cmds, nflag, inp):
        self.cmds = cmds
        self.nflag = nflag
        self.inp = inp
        self.out = []
        self.append_q = []
        self.hold = ''
        self.ps = ''
        self.tflag = False
        self.last_rx = None
        inp.on_new_file = self.reset_ranges

    def reset_ranges(self):
        for c in self.cmds:
            c.state = c.initial_state

    def dump_append(self):
        if self.append_q:
            self.out.extend(self.append_q)
            self.append_q = []

    def get_rx(self, rx):
        if rx is None:
            if self.last_rx is None:
                raise SedError("no previous regular expression")
            return self.last_rx
        self.last_rx = rx
        return rx

    def match_one(self, a):
        k = a.kind
        l = self.inp.lineno
        if k == 'line':
            return l == a.n1
        if k == 'last':
            return self.inp.is_last()
        if k == 're':
            rx = self.get_rx(a.rx)
            return rx.search(self.ps, 0) is not None
        if k == 'step':
            if a.n2 <= 0:
                return l == a.n1
            return l >= a.n1 and (l - a.n1) % a.n2 == 0
        return False

    def match_addr(self, cmd):
        if cmd.a1 is None:
            return True
        if cmd.a2 is None:
            return self.match_one(cmd.a1)
        l = self.inp.lineno
        a2 = cmd.a2
        if cmd.state == 1:
            if a2.kind in ('line', 'plus', 'mult'):
                if l >= cmd.range_end:
                    cmd.state = 0
                return l <= cmd.range_end or True
            if self.match_one(a2):
                cmd.state = 0
            return True
        if not self.match_one(cmd.a1):
            return False
        if a2.kind == 'line':
            if a2.n1 <= l:
                return True
            cmd.range_end = a2.n1
        elif a2.kind == 'plus':
            if a2.n1 == 0:
                return True
            cmd.range_end = l + a2.n1
        elif a2.kind == 'mult':
            if a2.n1 <= 0 or l % a2.n1 == 0:
                return True
            cmd.range_end = (l // a2.n1 + 1) * a2.n1
        cmd.state = 1
        return True

    def subst(self, cmd):
        rx = self.get_rx(cmd.rx)
        s = self.ps
        n = len(s)
        pos = 0
        count = 0
        out = []
        did = False
        prev_end = -1
        while pos <= n:
            m = rx.search(s, pos)
            if m is None:
                break
            st, en = m[0], m[1]
            if st == en and st == prev_end:
                # empty match right after the previous match: skip
                if st < n:
                    out.append(s[pos:st + 1])
                pos = st + 1
                continue
            count += 1
            out.append(s[pos:st])
            if count >= cmd.numb:
                did = True
                for part in cmd.repl:
                    if type(part) is int:
                        a, b = m[2 * part] if 2 * part < len(m) else None, m[2 * part + 1] if 2 * part + 1 < len(m) else None
                        if a is not None and b is not None:
                            out.append(s[a:b])
                    else:
                        out.append(part)
            else:
                out.append(s[st:en])
            prev_end = en
            if st == en:
                if st < n:
                    out.append(s[st])
                pos = en + 1
            else:
                pos = en
            if did and not cmd.glob:
                break
        if not did:
            return False
        if pos <= n:
            out.append(s[pos:])
        self.ps = ''.join(out)
        return True

    def lcmd(self, width):
        if width is None:
            width = 70
        s = self.ps
        res = []
        cur = ''
        esc = {'\\': '\\\\', '\a': '\\a', '\b': '\\b', '\f': '\\f', '\n': '\\n',
               '\r': '\\r', '\t': '\\t', '\v': '\\v'}
        for ch in s:
            if ch in esc:
                o = esc[ch]
            elif 32 <= ord(ch) < 127:
                o = ch
            else:
                o = '\\%03o' % ord(ch)
            if width > 1 and len(cur) + len(o) > width - 1:
                res.append(cur + '\\\n')
                cur = ''
            cur += o
        res.append(cur + '$\n')
        self.out.append(''.join(res))

    def read_into(self, append):
        """Read next line for n/N. Returns False if no more input."""
        if not self.inp.has_next():
            return False
        self.dump_append()
        line = self.inp.next_line()
        if line is None:
            return False
        if append:
            self.ps = self.ps + '\n' + line
        else:
            self.ps = line
        self.tflag = False
        return True

    def execute(self):
        """Returns one of 'end', 'delete', 'restart'."""
        cmds = self.cmds
        ncmds = len(cmds)
        pc = 0
        out = self.out
        while pc < ncmds:
            cmd = cmds[pc]
            name = cmd.name
            if name == '}' or name == ':' or name == '#':
                pc += 1
                continue
            m = self.match_addr(cmd)
            if cmd.neg:
                m = not m
            if not m:
                if name == '{':
                    pc = cmd.end + 1
                else:
                    pc += 1
                continue
            pc += 1
            if name == '{':
                continue
            if name == 's':
                if self.subst(cmd):
                    self.tflag = True
                    if cmd.pflag:
                        out.append(self.ps + '\n')
            elif name == 'p':
                out.append(self.ps + '\n')
            elif name == 'd':
                return 'delete'
            elif name == 'D':
                idx = self.ps.find('\n')
                if idx < 0:
                    return 'delete'
                self.ps = self.ps[idx + 1:]
                return 'restart'
            elif name == 'n':
                if not self.inp.has_next():
                    return 'end'
                if not self.nflag:
                    out.append(self.ps + '\n')
                if not self.read_into(False):
                    return 'end_noprint'
            elif name == 'N':
                if not self.inp.has_next():
                    return 'end'
                self.read_into(True)
            elif name == 'g':
                self.ps = self.hold
            elif name == 'G':
                self.ps = self.ps + '\n' + self.hold
            elif name == 'h':
                self.hold = self.ps
            elif name == 'H':
                self.hold = self.hold + '\n' + self.ps
            elif name == 'x':
                self.ps, self.hold = self.hold, self.ps
            elif name == 'b':
                pc = cmd.target
            elif name == 't':
                if self.tflag:
                    self.tflag = False
                    pc = cmd.target
            elif name == 'T':
                if self.tflag:
                    self.tflag = False
                else:
                    pc = cmd.target
            elif name == 'P':
                idx = self.ps.find('\n')
                out.append((self.ps if idx < 0 else self.ps[:idx]) + '\n')
            elif name == '=':
                out.append('%d\n' % self.inp.lineno)
            elif name == 'z':
                self.ps = ''
            elif name == 'a':
                self.append_q.append(cmd.text)
            elif name == 'i':
                out.append(cmd.text)
            elif name == 'c':
                if cmd.a2 is None or cmd.state != 1:
                    out.append(cmd.text)
                return 'delete'
            elif name == 'q':
                if not self.nflag:
                    out.append(self.ps + '\n')
                self.dump_append()
                raise Quit(cmd.code)
            elif name == 'Q':
                raise Quit(cmd.code)
            elif name == 'y':
                mp = cmd.ymap
                self.ps = ''.join(mp.get(ch, ch) for ch in self.ps)
            elif name == 'l':
                self.lcmd(cmd.code)
            elif name == 'F':
                out.append(('-' if self.inp.curname == '-' else self.inp.curname) + '\n')
            else:
                pass
        return 'end'

    def run(self):
        restart = False
        try:
            while True:
                if not restart:
                    line = self.inp.next_line()
                    if line is None:
                        break
                    self.ps = line
                    self.tflag = False
                restart = False
                r = self.execute()
                if r == 'end':
                    if not self.nflag:
                        self.out.append(self.ps + '\n')
                elif r == 'restart':
                    restart = True
                self.dump_append()
        except Quit as q:
            return q.code
        return 2 if self.inp.bad else 0


def main(argv):
    nflag = False
    ere = False
    separate = False
    scripts = []
    files = []
    i = 0
    have_e = False
    while i < len(argv):
        a = argv[i]
        if a == '--':
            files.extend(argv[i + 1:])
            break
        if a.startswith('--') and len(a) > 2:
            if a in ('--quiet', '--silent'):
                nflag = True
            elif a == '--regexp-extended':
                ere = True
            elif a == '--separate':
                separate = True
            elif a.startswith('--expression='):
                scripts.append(a[len('--expression='):])
                have_e = True
            elif a == '--expression':
                i += 1
                scripts.append(argv[i])
                have_e = True
            elif a == '--posix' or a == '--debug' or a == '--sandbox':
                pass
            else:
                sys.stderr.write("sed: unknown option -- '%s'\n" % a)
                return 1
            i += 1
            continue
        if a.startswith('-') and len(a) > 1:
            j = 1
            while j < len(a):
                o = a[j]
                if o == 'n':
                    nflag = True
                elif o in 'Er':
                    ere = True
                elif o == 's':
                    separate = True
                elif o == 'u' or o == 'z' and False:
                    pass
                elif o == 'e':
                    rest = a[j + 1:]
                    if rest:
                        scripts.append(rest)
                    else:
                        i += 1
                        if i >= len(argv):
                            sys.stderr.write("sed: option requires an argument -- 'e'\n")
                            return 1
                        scripts.append(argv[i])
                    have_e = True
                    break
                elif o == 'f':
                    rest = a[j + 1:]
                    if not rest:
                        i += 1
                        rest = argv[i]
                    try:
                        with open(rest, 'rb') as f:
                            t = f.read().decode('latin-1')
                        if t.endswith('\n'):
                            t = t[:-1]
                        scripts.append(t)
                    except OSError:
                        sys.stderr.write("sed: couldn't open file %s\n" % rest)
                        return 1
                    have_e = True
                    break
                else:
                    sys.stderr.write("sed: invalid option -- '%s'\n" % o)
                    return 1
                j += 1
            i += 1
            continue
        if not have_e and not scripts:
            scripts.append(a)
            have_e = True
        else:
            files.append(a)
        i += 1
    if not scripts:
        sys.stderr.write("Usage: sed [OPTION]... {script-only-if-no-other-script} [input-file]...\n")
        return 1
    script = '\n'.join(scripts)
    if script.startswith('#n') and (len(script) == 2 or script[2] == '\n'):
        nflag = True
    try:
        cmds = ScriptParser(script, ere).parse()
    except (SedError, RegexError) as e:
        sys.stderr.write("sed: -e expression #1, char 0: %s\n" % e)
        return 1
    inp = Input(files, separate)
    sed = Sed(cmds, nflag, inp)
    try:
        code = sed.run()
    except SedError as e:
        sys.stdout.buffer.write(''.join(sed.out).encode('latin-1'))
        sys.stderr.write("sed: %s\n" % e)
        return 4
    try:
        sys.stdout.buffer.write(''.join(sed.out).encode('latin-1'))
        sys.stdout.flush()
    except BrokenPipeError:
        pass
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
