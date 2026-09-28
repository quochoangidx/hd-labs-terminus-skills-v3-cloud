"""pysed: a GNU sed 4.9 replacement in pure Python.

Usage: python3 /app/pysed/sed.py [OPTION]... {script-only-if-no-other-script} [input-file]...
"""

import sys

# ---------------------------------------------------------------------------
# Character helpers (C locale, bytes decoded as latin-1)
# ---------------------------------------------------------------------------

_UPPER_TABLE = {i: i - 32 for i in range(ord('a'), ord('z') + 1)}
_LOWER_TABLE = {i: i + 32 for i in range(ord('A'), ord('Z') + 1)}


def c_upper(s):
    return s.translate(_UPPER_TABLE)


def c_lower(s):
    return s.translate(_LOWER_TABLE)


ALLCHARS = frozenset(chr(i) for i in range(256))
_DIGITS = '0123456789'
_LOWERS = 'abcdefghijklmnopqrstuvwxyz'
_UPPERS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
_ALPHA = _LOWERS + _UPPERS
_ALNUM = _ALPHA + _DIGITS
WORDCHARS = frozenset(_ALNUM + '_')
_PUNCT = ''.join(chr(i) for i in range(33, 127) if chr(i) not in _ALNUM)
SPACECHARS = frozenset(' \t\n\r\f\v')

CLASSES = {
    'alpha': frozenset(_ALPHA),
    'digit': frozenset(_DIGITS),
    'alnum': frozenset(_ALNUM),
    'upper': frozenset(_UPPERS),
    'lower': frozenset(_LOWERS),
    'space': SPACECHARS,
    'blank': frozenset(' \t'),
    'punct': frozenset(_PUNCT),
    'print': frozenset(chr(i) for i in range(32, 127)),
    'graph': frozenset(chr(i) for i in range(33, 127)),
    'cntrl': frozenset([chr(i) for i in range(32)] + [chr(127)]),
    'xdigit': frozenset(_DIGITS + 'abcdefABCDEF'),
}


def is_word(c):
    return c in WORDCHARS


# ---------------------------------------------------------------------------
# Escape normalisation (like GNU sed's normalize_text)
# ---------------------------------------------------------------------------

_SIMPLE_ESC = {'a': '\a', 'f': '\f', 'n': '\n', 'r': '\r', 't': '\t',
               'v': '\v'}


def _convert_number(text, i, base):
    """text[i] is the letter (d/o/x).  Returns (char, new_index)."""
    maxd = {16: 2, 8: 3, 10: 3}[base]
    j = i + 1
    n = 0
    cnt = 0
    while j < len(text) and cnt < maxd:
        ch = text[j]
        try:
            d = int(ch, 16)
        except ValueError:
            break
        if d >= base:
            break
        n = n * base + d
        j += 1
        cnt += 1
    if cnt == 0:
        return text[i], i + 1
    return chr(n & 0xff), j


def normalize(text, mode):
    """Process GNU escapes.  mode is 'regex', 'repl' or 'text'.

    For 'regex' and 'repl', unknown escapes are left as backslash pairs.
    For 'text', every escape is resolved (backslash removed).
    """
    out = []
    i = 0
    n = len(text)
    while i < n:
        c = text[i]
        if c != '\\' or i + 1 >= n:
            out.append(c)
            i += 1
            continue
        d = text[i + 1]
        if d in _SIMPLE_ESC:
            out.append(_SIMPLE_ESC[d])
            i += 2
            continue
        if d in 'dox':
            base = {'d': 10, 'o': 8, 'x': 16}[d]
            ch, j = _convert_number(text, i + 1, base)
            if j == i + 2 and ch == d:
                # no digits: keep as-is
                if mode == 'text':
                    out.append(d)
                else:
                    out.append('\\' + d)
                i += 2
                continue
            if mode != 'text' and ch in '\\&':
                out.append('\\' + ch)
            else:
                out.append(ch)
            i = j
            continue
        if d == 'c':
            if i + 2 < n:
                x = text[i + 2]
                if x == '\\' and mode != 'text':
                    # \c\\ -> control-backslash
                    if i + 3 < n and text[i + 3] == '\\':
                        out.append(chr(ord('\\') ^ 0x40))
                        i += 4
                        continue
                out.append(chr(ord(c_upper(x)) ^ 0x40))
                i += 3
                continue
            if mode == 'text':
                out.append('c')
            else:
                out.append('\\c')
            i += 2
            continue
        if mode == 'text':
            out.append(d)
        else:
            out.append('\\' + d)
        i += 2
    return ''.join(out)


# ---------------------------------------------------------------------------
# Regular expressions: parser
# ---------------------------------------------------------------------------

class RegexParser(object):
    def __init__(self, pat, ere):
        self.p = pat
        self.n = len(pat)
        self.i = 0
        self.ere = ere
        self.ngroups = 0
        self.max_backref = 0

    def parse(self):
        node = self.parse_alt(0)
        while self.i < self.n:
            # stray close; treat literally
            if self.ere:
                self.i += 1
                rest = self.parse_alt(0)
                node = ('cat', [node, ('lit', ')'), rest])
            else:
                self.i += 2
                rest = self.parse_alt(0)
                node = ('cat', [node, ('lit', ')'), rest])
        return node

    def at_alt(self):
        if self.i >= self.n:
            return False
        if self.ere:
            return self.p[self.i] == '|'
        return self.p.startswith('\\|', self.i)

    def at_close(self, depth):
        if depth <= 0 or self.i >= self.n:
            return False
        if self.ere:
            return self.p[self.i] == ')'
        return self.p.startswith('\\)', self.i)

    def parse_alt(self, depth):
        branches = [self.parse_branch(depth)]
        while self.at_alt():
            self.i += 1 if self.ere else 2
            branches.append(self.parse_branch(depth))
        if len(branches) == 1:
            return branches[0]
        return ('alt', branches)

    def try_interval(self, j):
        """Parse interval body starting at index j (after the opening brace).
        Returns (min, max, newindex) or None."""
        p = self.p
        n = self.n
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
            b = ''
            while k < n and p[k].isdigit():
                b += p[k]
                k += 1
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
        return (mn, mx, k)

    def quant_at(self):
        """If a quantifier starts at current index return (min,max,newidx)."""
        p = self.p
        i = self.i
        c = p[i]
        if c == '*':
            return (0, None, i + 1)
        if self.ere:
            if c == '+':
                return (1, None, i + 1)
            if c == '?':
                return (0, 1, i + 1)
            if c == '{':
                return self.try_interval(i + 1)
            return None
        if c == '\\' and i + 1 < self.n:
            d = p[i + 1]
            if d == '+':
                return (1, None, i + 2)
            if d == '?':
                return (0, 1, i + 2)
            if d == '{':
                return self.try_interval(i + 2)
        return None

    def parse_branch(self, depth):
        items = []
        p = self.p
        while self.i < self.n and not self.at_alt() and not self.at_close(depth):
            q = self.quant_at()
            if q is not None:
                literal_star = False
                if not items:
                    literal_star = True
                elif not self.ere and len(items) == 1 and items[0] == ('assert', 'bol'):
                    literal_star = True
                if not literal_star:
                    mn, mx, ni = q
                    self.i = ni
                    prev = items.pop()
                    items.append(('rep', prev, mn, mx))
                    continue
                # literal
                c = p[self.i]
                if c == '\\':
                    items.append(('lit', p[self.i + 1]))
                    self.i += 2
                else:
                    items.append(('lit', c))
                    self.i += 1
                continue
            items.append(self.parse_atom(depth, not items))
        # merge literals
        merged = []
        for it in items:
            if it[0] == 'lit' and merged and merged[-1][0] == 'lit':
                merged[-1] = ('lit', merged[-1][1] + it[1])
            else:
                merged.append(it)
        if not merged:
            return ('empty',)
        if len(merged) == 1:
            return merged[0]
        return ('cat', merged)

    def parse_atom(self, depth, at_start):
        p = self.p
        c = p[self.i]
        ere = self.ere
        if c == '.':
            self.i += 1
            return ('any',)
        if c == '[':
            return self.parse_bracket()
        if c == '^':
            if ere or at_start:
                self.i += 1
                return ('assert', 'bol')
            self.i += 1
            return ('lit', '^')
        if c == '$':
            if ere:
                self.i += 1
                return ('assert', 'eol')
            j = self.i + 1
            if j >= self.n or p.startswith('\\)', j) or p.startswith('\\|', j):
                self.i += 1
                return ('assert', 'eol')
            self.i += 1
            return ('lit', '$')
        if ere and c == '(':
            self.i += 1
            self.ngroups += 1
            idx = self.ngroups
            body = self.parse_alt(depth + 1)
            if self.i < self.n and p[self.i] == ')':
                self.i += 1
            return ('group', idx, body)
        if ere and c == ')':
            self.i += 1
            return ('lit', ')')
        if c == '\\':
            if self.i + 1 >= self.n:
                self.i += 1
                return ('lit', '\\')
            d = p[self.i + 1]
            self.i += 2
            if not ere and d == '(':
                self.ngroups += 1
                idx = self.ngroups
                body = self.parse_alt(depth + 1)
                if p.startswith('\\)', self.i):
                    self.i += 2
                return ('group', idx, body)
            if not ere and d == ')':
                return ('lit', ')')
            if not ere and d == '{':
                return ('lit', '{')
            if d in '123456789':
                k = int(d)
                if k > self.max_backref:
                    self.max_backref = k
                return ('backref', k)
            if d == 'w':
                return ('set', WORDCHARS)
            if d == 'W':
                return ('set', ALLCHARS - WORDCHARS)
            if d == 's':
                return ('set', SPACECHARS)
            if d == 'S':
                return ('set', ALLCHARS - SPACECHARS)
            if d == 'b':
                return ('assert', 'wordb')
            if d == 'B':
                return ('assert', 'nwordb')
            if d == '<':
                return ('assert', 'wstart')
            if d == '>':
                return ('assert', 'wend')
            if d == '`':
                return ('assert', 'bufstart')
            if d == "'":
                return ('assert', 'bufend')
            if d == 'n':
                return ('lit', '\n')
            return ('lit', d)
        self.i += 1
        return ('lit', c)

    def parse_bracket(self):
        p = self.p
        n = self.n
        start = self.i
        i = self.i + 1
        neg = False
        if i < n and p[i] == '^':
            neg = True
            i += 1
        chars = set()
        first = True
        ok = False
        while i < n:
            c = p[i]
            if c == ']' and not first:
                i += 1
                ok = True
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
                        chars |= CLASSES.get(name, frozenset())
                        continue
                    lo = name[:1] if name else ''
                    if not lo:
                        continue
            else:
                lo = c
                i += 1
            # range?
            if i + 1 < n and p[i] == '-' and p[i + 1] != ']':
                i += 1
                hc = p[i]
                if hc == '[' and i + 1 < n and p[i + 1] in '.=':
                    kind = p[i + 1]
                    end = p.find(kind + ']', i + 2)
                    if end >= 0:
                        hi = p[i + 2:end][:1] or hc
                        i = end + 2
                    else:
                        hi = hc
                        i += 1
                else:
                    hi = hc
                    i += 1
                for o in range(ord(lo), ord(hi) + 1):
                    chars.add(chr(o))
            else:
                chars.add(lo)
        if not ok:
            # unterminated: treat '[' literally
            self.i = start + 1
            return ('lit', '[')
        self.i = i
        return ('bracket', frozenset(chars), neg)


# ---------------------------------------------------------------------------
# Regular expressions: set-based matcher (POSIX leftmost-longest)
# ---------------------------------------------------------------------------

def _icase_set(cs):
    out = set(cs)
    for c in cs:
        out.add(c_lower(c))
        out.add(c_upper(c))
    return frozenset(out)


class Regex(object):
    def __init__(self, pattern, ere, icase=False, mline=False):
        self.pattern = pattern
        self.icase = icase
        self.mline = mline
        parser = RegexParser(pattern, ere)
        ast = parser.parse()
        self.ngroups = parser.ngroups
        self.max_backref = parser.max_backref
        self.ast = self._resolve(ast)
        self.cache = {}
        nullable, fs = self._first(self.ast)
        self.first = None if nullable else fs

    # convert 'any'/'bracket' into plain sets with flags applied
    def _resolve(self, node):
        k = node[0]
        if k == 'any':
            cs = ALLCHARS
            if self.mline:
                cs = cs - {'\n'}
            return ('set', cs)
        if k == 'bracket':
            cs = node[1]
            if self.icase:
                cs = _icase_set(cs)
            if node[2]:
                cs = ALLCHARS - cs
                if self.mline:
                    cs = cs - {'\n'}
            return ('set', frozenset(cs))
        if k == 'set':
            cs = node[1]
            if self.icase:
                cs = _icase_set(cs)
            return ('set', frozenset(cs))
        if k == 'lit':
            return node
        if k == 'group':
            return ('group', node[1], self._resolve(node[2]))
        if k == 'cat':
            return ('cat', [self._resolve(x) for x in node[1]])
        if k == 'alt':
            return ('alt', [self._resolve(x) for x in node[1]])
        if k == 'rep':
            return ('rep', self._resolve(node[1]), node[2], node[3])
        return node

    def _first(self, node):
        k = node[0]
        if k == 'lit':
            c = node[1][0]
            if self.icase:
                return (False, {c, c_lower(c), c_upper(c)})
            return (False, {c})
        if k == 'set':
            return (False, set(node[1]))
        if k in ('assert', 'empty'):
            return (True, set())
        if k == 'backref':
            return (True, None)
        if k == 'group':
            return self._first(node[2])
        if k == 'cat':
            acc = set()
            for x in node[1]:
                nl, cs = self._first(x)
                if cs is None or acc is None:
                    acc = None
                else:
                    acc |= cs
                if not nl:
                    return (False, acc)
            return (True, acc)
        if k == 'alt':
            acc = set()
            nlany = False
            for x in node[1]:
                nl, cs = self._first(x)
                nlany = nlany or nl
                if cs is None or acc is None:
                    acc = None
                else:
                    acc |= cs
            return (nlany, acc)
        if k == 'rep':
            nl, cs = self._first(node[1])
            return (nl or node[2] == 0, cs)
        return (True, None)

    def _build(self, node, slots, mok=False):
        k = node[0]
        icase = self.icase
        mline = self.mline
        if k == 'lit':
            lit = node[1]
            ln = len(lit)
            if icase:
                litl = c_lower(lit)

                def f(S, sts):
                    out = set()
                    for st in sts:
                        p = st[0]
                        if c_lower(S[p:p + ln]) == litl:
                            out.add((p + ln,) + st[1:])
                    return out
            elif ln == 1:
                def f(S, sts):
                    out = set()
                    n = len(S)
                    for st in sts:
                        p = st[0]
                        if p < n and S[p] == lit:
                            out.add((p + 1,) + st[1:])
                    return out
            else:
                def f(S, sts):
                    out = set()
                    for st in sts:
                        p = st[0]
                        if S.startswith(lit, p):
                            out.add((p + ln,) + st[1:])
                    return out
            return f
        if k == 'set':
            cs = node[1]

            def f(S, sts):
                out = set()
                n = len(S)
                for st in sts:
                    p = st[0]
                    if p < n and S[p] in cs:
                        out.add((p + 1,) + st[1:])
                return out
            return f
        if k == 'empty':
            return lambda S, sts: sts
        if k == 'assert':
            kind = node[1]
            if kind == 'bol':
                if mline:
                    def t(S, p):
                        return p == 0 or S[p - 1] == '\n'
                else:
                    def t(S, p):
                        return p == 0
            elif kind == 'eol':
                if mline:
                    def t(S, p):
                        return p == len(S) or S[p] == '\n'
                else:
                    def t(S, p):
                        return p == len(S)
            elif kind == 'bufstart':
                def t(S, p):
                    return p == 0
            elif kind == 'bufend':
                def t(S, p):
                    return p == len(S)
            else:
                def wb(S, p):
                    a = p > 0 and S[p - 1] in WORDCHARS
                    b = p < len(S) and S[p] in WORDCHARS
                    return a, b
                if kind == 'wordb':
                    def t(S, p):
                        a, b = wb(S, p)
                        return a != b
                elif kind == 'nwordb':
                    def t(S, p):
                        a, b = wb(S, p)
                        return a == b
                elif kind == 'wstart':
                    def t(S, p):
                        a, b = wb(S, p)
                        return (not a) and b
                else:
                    def t(S, p):
                        a, b = wb(S, p)
                        return a and not b

            def f(S, sts):
                return {st for st in sts if t(S, st[0])}
            return f
        if k == 'group':
            idx = node[1]
            body = self._build(node[2], slots, mok)
            if idx not in slots:
                return body
            o = slots[idx]

            def f(S, sts):
                opened = set()
                for st in sts:
                    opened.add(st[:o] + (st[0],) + st[o + 1:])
                res = body(S, opened)
                out = set()
                for st in res:
                    out.add(st[:o] + (-1, st[o], st[0]) + st[o + 3:])
                return out
            return f
        if k == 'backref':
            idx = node[1]
            if idx not in slots:
                return lambda S, sts: set()
            o = slots[idx]

            def f(S, sts):
                out = set()
                for st in sts:
                    s0 = st[o + 1]
                    if s0 < 0:
                        continue
                    sub = S[s0:st[o + 2]]
                    p = st[0]
                    ln = len(sub)
                    if icase:
                        if c_lower(S[p:p + ln]) == c_lower(sub):
                            out.add((p + ln,) + st[1:])
                    elif S.startswith(sub, p):
                        out.add((p + ln,) + st[1:])
                return out
            return f
        if k == 'cat':
            fs = [self._build(x, slots, mok) for x in node[1]]

            def f(S, sts):
                for g in fs:
                    if not sts:
                        return sts
                    sts = g(S, sts)
                return sts
            return f
        if k == 'alt':
            fs = [self._build(x, slots, mok) for x in node[1]]

            def f(S, sts):
                out = set()
                for g in fs:
                    out |= g(S, sts)
                return out
            return f
        if k == 'rep':
            mn = node[2]
            mx = node[3]
            counted = not ((mx is None and mn <= 1) or (mn == 0 and mx == 1))
            body = self._build(node[1], slots, mok and not counted)
            if mok:
                seen = {}
                self.memos.append(seen)
                ctx = self.ctx

                def filt(sts):
                    att = ctx[0]
                    out = set()
                    for st in sts:
                        a = seen.get(st[0])
                        if a is None:
                            seen[st[0]] = att
                            out.add(st)
                        elif a == att:
                            out.add(st)
                    return out

                if mx is not None:
                    def f(S, sts):
                        cur = sts
                        for _ in range(mn):
                            if not cur:
                                return cur
                            cur = body(S, cur)
                        if mx == mn:
                            return filt(cur)
                        result = set(cur)
                        frontier = cur
                        count = mn
                        while frontier and count < mx:
                            nxt = body(S, frontier)
                            nxt -= result
                            result |= nxt
                            frontier = nxt
                            count += 1
                        return filt(result)
                    return f

                def f(S, sts):
                    cur = sts
                    for _ in range(mn):
                        if not cur:
                            return cur
                        cur = body(S, cur)
                    cur = filt(cur)
                    result = set(cur)
                    frontier = cur
                    count = mn
                    while frontier and (mx is None or count < mx):
                        nxt = body(S, frontier)
                        nxt -= result
                        nxt = filt(nxt)
                        result |= nxt
                        frontier = nxt
                        count += 1
                    return result
                return f

            def f(S, sts):
                cur = sts
                for _ in range(mn):
                    if not cur:
                        return cur
                    cur = body(S, cur)
                if mx is not None and mx == mn:
                    return cur
                result = set(cur)
                frontier = cur
                count = mn
                while frontier and (mx is None or count < mx):
                    nxt = body(S, frontier)
                    nxt -= result
                    result |= nxt
                    frontier = nxt
                    count += 1
                return result
            return f
        raise ValueError(k)

    def _matcher(self, ntrack):
        m = self.cache.get(ntrack)
        if m is None:
            slots = {}
            for g in range(1, ntrack + 1):
                slots[g] = 1 + 3 * (g - 1)
            m = self._build(self.ast, slots)
            self.cache[ntrack] = m
        return m

    def _posmatcher(self):
        m = self.cache.get('pos')
        if m is None:
            self.memos = []
            self.ctx = [0]
            m = self._build(self.ast, {}, True)
            self.cache['pos'] = m
        return m

    def _pos_search(self, S, start):
        """Position-only leftmost-longest search with memoisation across
        start positions (valid only without back-references)."""
        f = self._posmatcher()
        for d in self.memos:
            d.clear()
        ctx = self.ctx
        n = len(S)
        first = self.first
        p = start
        att = 0
        while p <= n:
            if first is not None:
                while p < n and S[p] not in first:
                    p += 1
                if p >= n:
                    return None
            att += 1
            ctx[0] = att
            res = f(S, {(p,)})
            if res:
                return (p, max(st[0] for st in res))
            p += 1
        return None

    def search(self, S, start, ntrack=0):
        """Return (start, end, groups) for the leftmost-longest match at or
        after `start`, or None.  groups[k] = (s, e) for k in 1..ntrack."""
        ntrack = min(max(ntrack, self.max_backref), self.ngroups)
        n = len(S)
        if self.max_backref == 0:
            r = self._pos_search(S, start)
            if r is None:
                return None
            if ntrack == 0:
                return (r[0], r[1], [r])
            start = r[0]
            n = start
            first = None
        else:
            first = self.first
        f = self._matcher(ntrack)
        init = (-1,) * (3 * ntrack)
        p = start
        while p <= n:
            if first is not None:
                while p < n and S[p] not in first:
                    p += 1
                if p >= n:
                    return None
            res = f(S, {(p,) + init})
            if res:
                if ntrack == 0:
                    e = max(st[0] for st in res)
                    return (p, e, [(p, e)])
                best = None
                bestkey = None
                for st in res:
                    key = [st[0]]
                    for g in range(ntrack):
                        s0 = st[2 + 3 * g]
                        e0 = st[3 + 3 * g]
                        if s0 < 0:
                            key.append((0, 0, 0))
                        else:
                            key.append((1, -s0, e0 - s0))
                    key = tuple(key)
                    if bestkey is None or key > bestkey:
                        bestkey = key
                        best = st
                groups = [(p, best[0])]
                for g in range(ntrack):
                    groups.append((best[2 + 3 * g], best[3 + 3 * g]))
                return (p, best[0], groups)
            p += 1
        return None


# ---------------------------------------------------------------------------
# Script parsing
# ---------------------------------------------------------------------------

class SedError(Exception):
    pass


class Addr(object):
    __slots__ = ('kind', 'n1', 'n2', 'regex')

    def __init__(self, kind, n1=0, n2=0, regex=None):
        self.kind = kind   # num, step, last, re, zero, plus, mod
        self.n1 = n1
        self.n2 = n2
        self.regex = regex


class Cmd(object):
    def __init__(self):
        self.a1 = None
        self.a2 = None
        self.negate = False
        self.name = None
        self.text = None
        self.label = None
        self.target = None
        self.int_arg = None
        self.block_end = None
        self.range_state = 0   # 0 inactive, 1 active, 2 closed
        self.range_end = 0
        # s command
        self.regex = None
        self.repl = None
        self.gflag = False
        self.pflag = 0
        self.nth = 1
        self.max_ref = 0
        self.ymap = None
        self.fname = None


INACTIVE, ACTIVE, CLOSED = 0, 1, 2
BLANKS = ' \t'
WS = ' \t\n\r\f\v'


class ScriptParser(object):
    def __init__(self, script, ere):
        self.s = script
        self.n = len(script)
        self.i = 0
        self.ere = ere

    def peek(self):
        if self.i < self.n:
            return self.s[self.i]
        return ''

    def skip_blanks(self):
        while self.i < self.n and self.s[self.i] in BLANKS:
            self.i += 1

    def skip_ws(self):
        while self.i < self.n and self.s[self.i] in WS:
            self.i += 1

    def match_slash(self, delim, regex):
        s = self.s
        buf = []
        while self.i < self.n:
            c = s[self.i]
            if c == delim:
                self.i += 1
                return ''.join(buf)
            if c == '\\':
                self.i += 1
                if self.i >= self.n:
                    buf.append('\\')
                    break
                c = s[self.i]
                if c == delim:
                    if not regex and c == '&':
                        buf.append('\\&')
                    else:
                        buf.append(c)
                elif c == 'n' and regex:
                    buf.append('\n')
                elif c == '\n':
                    buf.append('\n')
                else:
                    buf.append('\\')
                    buf.append(c)
                self.i += 1
                continue
            buf.append(c)
            self.i += 1
        raise SedError('unterminated')

    def make_regex(self, pat, icase, mline):
        if pat == '':
            return None
        pat = normalize(pat, 'regex')
        return Regex(pat, self.ere, icase, mline)

    def read_number(self):
        st = self.i
        while self.i < self.n and self.s[self.i].isdigit():
            self.i += 1
        return int(self.s[st:self.i])

    def parse_addr(self):
        c = self.peek()
        if c.isdigit():
            n1 = self.read_number()
            if self.peek() == '~':
                self.i += 1
                n2 = self.read_number() if self.peek().isdigit() else 0
                return Addr('step', n1, n2)
            if n1 == 0:
                return Addr('zero')
            return Addr('num', n1)
        if c == '$':
            self.i += 1
            return Addr('last')
        if c == '/' or c == '\\':
            if c == '\\':
                self.i += 1
                delim = self.peek()
            else:
                delim = '/'
            self.i += 1
            pat = self.match_slash(delim, True)
            icase = mline = False
            while True:
                c = self.peek()
                if c == 'I':
                    icase = True
                    self.i += 1
                elif c == 'M':
                    mline = True
                    self.i += 1
                else:
                    break
            return Addr('re', regex=self.make_regex(pat, icase, mline))
        return None

    def parse_addr2(self):
        c = self.peek()
        if c == '+' or c == '~':
            self.i += 1
            n = self.read_number() if self.peek().isdigit() else 0
            return Addr('plus' if c == '+' else 'mod', n)
        a = self.parse_addr()
        if a is not None and a.kind == 'zero':
            a = Addr('num', 0)
        return a

    def end_of_cmd(self):
        self.skip_blanks()
        c = self.peek()
        if c == ';':
            self.i += 1

    def read_label(self):
        self.skip_blanks()
        st = self.i
        while self.i < self.n and self.s[self.i] not in WS and self.s[self.i] not in ';}':
            self.i += 1
        return self.s[st:self.i]

    def read_to_eol(self):
        st = self.i
        while self.i < self.n and self.s[self.i] != '\n':
            self.i += 1
        return self.s[st:self.i]

    def read_text(self):
        s = self.s
        self.skip_blanks()
        if self.peek() == '\\':
            self.i += 1
            if self.peek() == '\n':
                self.i += 1
                raw_first = ''
            else:
                raw_first = self.peek()
                if self.i < self.n:
                    self.i += 1
        else:
            raw_first = ''
        buf = []
        while self.i < self.n:
            c = s[self.i]
            if c == '\n':
                self.i += 1
                break
            if c == '\\':
                self.i += 1
                if self.i >= self.n:
                    break
                d = s[self.i]
                self.i += 1
                if d == '\n':
                    buf.append('\n')
                else:
                    buf.append('\\' + d)
                continue
            buf.append(c)
            self.i += 1
        text = raw_first.replace('\\', '\\\\') + ''.join(buf)
        return normalize(text, 'text') + '\n'

    def parse_repl(self, text):
        """Returns list of pieces (prefix, subst_id, repl_type)."""
        text = normalize(text, 'repl')
        pieces = []
        repl_type = 0
        base = []
        i = 0
        n = len(text)
        maxref = 0

        # repl_type bits: 1 = upper, 2 = lower, 4 = upper first, 8 = lower first
        def newpiece():
            pieces.append([''.join(base), -1, repl_type])
            del base[:]
            return pieces[-1]

        while i < n:
            c = text[i]
            if c == '\\':
                tail = newpiece()
                repl_type &= ~12
                i += 1
                if i >= n:
                    tail[0] += '\\'
                    break
                d = text[i]
                if d.isdigit():
                    tail[1] = int(d)
                    if tail[1] > maxref:
                        maxref = tail[1]
                elif d in 'LUE':
                    pending = tail[2] & 12 if tail[0] == '' else 0
                    repl_type = {'L': 2, 'U': 1, 'E': 0}[d] | pending
                elif d == 'l':
                    repl_type |= 8
                elif d == 'u':
                    repl_type |= 4
                elif d == 'n':
                    tail[0] += '\n'
                else:
                    tail[0] += d
                i += 1
            elif c == '&':
                tail = newpiece()
                repl_type &= ~12
                tail[1] = 0
                i += 1
            else:
                base.append(c)
                i += 1
        if base:
            newpiece()
        return pieces, maxref

    def parse(self):
        cmds = []
        stack = []
        s = self.s
        while True:
            self.skip_ws()
            while self.peek() == ';':
                self.i += 1
                self.skip_ws()
            if self.i >= self.n:
                break
            if self.peek() == '#':
                self.read_to_eol()
                continue
            cmd = Cmd()
            a1 = self.parse_addr()
            if a1 is not None:
                cmd.a1 = a1
                self.skip_blanks()
                if self.peek() == ',':
                    self.i += 1
                    self.skip_blanks()
                    cmd.a2 = self.parse_addr2()
                if a1.kind == 'zero':
                    if cmd.a2 is None:
                        raise SedError('invalid usage of line address 0')
            self.skip_blanks()
            while self.peek() == '!':
                cmd.negate = True
                self.i += 1
                self.skip_blanks()
            if self.i >= self.n:
                raise SedError('missing command')
            c = s[self.i]
            self.i += 1
            cmd.name = c
            if c == '{':
                stack.append(len(cmds))
                cmds.append(cmd)
                continue
            if c == '}':
                if stack:
                    op = stack.pop()
                    cmds[op].block_end = len(cmds) + 1
                cmds.append(cmd)
                self.end_of_cmd()
                continue
            if c in '=dDgGhHnNpPxzF':
                cmds.append(cmd)
                self.end_of_cmd()
                continue
            if c in 'lqQL':
                self.skip_blanks()
                if self.peek().isdigit():
                    cmd.int_arg = self.read_number()
                cmds.append(cmd)
                self.end_of_cmd()
                continue
            if c == ':':
                cmd.label = self.read_label()
                cmds.append(cmd)
                self.end_of_cmd()
                continue
            if c in 'btT':
                cmd.label = self.read_label()
                cmds.append(cmd)
                self.end_of_cmd()
                continue
            if c in 'aic':
                cmd.text = self.read_text()
                cmds.append(cmd)
                continue
            if c in 'rRwWe':
                self.skip_blanks()
                cmd.fname = self.read_to_eol()
                cmds.append(cmd)
                continue
            if c == 'v':
                self.read_label()
                cmds.append(cmd)
                self.end_of_cmd()
                continue
            if c == 's':
                delim = s[self.i]
                self.i += 1
                pat = self.match_slash(delim, True)
                rep = self.match_slash(delim, False)
                icase = mline = False
                while self.i < self.n:
                    f = s[self.i]
                    if f == 'g':
                        cmd.gflag = True
                    elif f == 'p':
                        cmd.pflag += 1
                    elif f in 'iI':
                        icase = True
                    elif f in 'mM':
                        mline = True
                    elif f == 'e':
                        pass
                    elif f.isdigit():
                        cmd.nth = self.read_number()
                        continue
                    elif f == 'w':
                        self.i += 1
                        self.skip_blanks()
                        cmd.fname = self.read_to_eol()
                        break
                    else:
                        break
                    self.i += 1
                cmd.regex = self.make_regex(pat, icase, mline)
                cmd.repl, cmd.max_ref = self.parse_repl(rep)
                cmds.append(cmd)
                self.end_of_cmd()
                continue
            if c == 'y':
                delim = s[self.i]
                self.i += 1
                src = self.y_unescape(self.match_slash(delim, False))
                dst = self.y_unescape(self.match_slash(delim, False))
                m = {}
                for a, b in zip(src, dst):
                    if a not in m:
                        m[a] = b
                cmd.ymap = {ord(a): b for a, b in m.items()}
                cmds.append(cmd)
                self.end_of_cmd()
                continue
            raise SedError('unknown command: %r' % c)
        # resolve labels
        labels = {}
        for idx, cmd in enumerate(cmds):
            if cmd.name == ':':
                if cmd.label not in labels:
                    labels[cmd.label] = idx
        for cmd in cmds:
            if cmd.name in 'btT':
                if cmd.label:
                    cmd.target = labels.get(cmd.label, len(cmds))
                else:
                    cmd.target = len(cmds)
        for idx, cmd in enumerate(cmds):
            if cmd.name == '{' and cmd.block_end is None:
                cmd.block_end = len(cmds)
        return cmds

    def y_unescape(self, t):
        t = normalize(t, 'repl')
        out = []
        i = 0
        while i < len(t):
            c = t[i]
            if c == '\\' and i + 1 < len(t):
                d = t[i + 1]
                if d == 'n':
                    out.append('\n')
                else:
                    out.append(d)
                i += 2
            else:
                out.append(c)
                i += 1
        return ''.join(out)


# ---------------------------------------------------------------------------
# Input handling
# ---------------------------------------------------------------------------

class Input(object):
    def __init__(self, files, separate, on_new_file):
        self.files = files
        self.fidx = 0
        self.lines = []
        self.li = 0
        self.separate = separate
        self.bad = 0
        self.line_number = 0
        self.on_new_file = on_new_file
        self.cur_name = '-'

    def _load(self, name):
        if name == '-':
            try:
                data = sys.stdin.buffer.read()
            except Exception:
                data = b''
        else:
            try:
                with open(name, 'rb') as fh:
                    data = fh.read()
            except (IOError, OSError) as e:
                sys.stderr.write('sed: can\'t read %s: %s\n' % (name, e.strerror or 'error'))
                self.bad += 1
                return None
        text = data.decode('latin-1')
        lines = []
        if text:
            parts = text.split('\n')
            last = parts.pop()
            for p in parts:
                lines.append((p, True))
            if last != '':
                lines.append((last, False))
        return lines

    def _open_next(self):
        name = self.files[self.fidx]
        self.fidx += 1
        lines = self._load(name)
        self.lines = lines or []
        self.li = 0
        self.cur_name = name
        return lines is not None

    def read_line(self):
        while self.li >= len(self.lines):
            if self.fidx >= len(self.files):
                return None
            self._open_next()
            if self.separate:
                self.line_number = 0
                self.on_new_file()
        r = self.lines[self.li]
        self.li += 1
        self.line_number += 1
        return r

    def is_last(self):
        if self.li < len(self.lines):
            return False
        if self.separate:
            return True
        while self.fidx < len(self.files):
            self._open_next()
            if self.lines:
                return False
        return True


# ---------------------------------------------------------------------------
# Executor
# ---------------------------------------------------------------------------

class Quit(Exception):
    pass


class Sed(object):
    def __init__(self, cmds, files, nflag, separate, line_len):
        self.cmds = cmds
        self.nflag = nflag
        self.line_len = line_len
        self.out = []
        self.missing_newline = False
        self.append_queue = []
        self.hold = ''
        self.ps = ''
        self.chomped = True
        self.replaced = False
        self.last_regex = None
        self.inp = Input(files, separate, self.reset_addresses)
        self.reset_addresses()

    def reset_addresses(self):
        for c in self.cmds:
            if c.a1 is not None and c.a1.kind == 'zero':
                c.range_state = ACTIVE
            else:
                c.range_state = INACTIVE

    # output --------------------------------------------------------------
    def write(self, t):
        if self.missing_newline:
            self.out.append('\n')
            self.missing_newline = False
        self.out.append(t)

    def output_ps(self, text=None):
        if text is None:
            text = self.ps
        self.write(text)
        if self.chomped:
            self.out.append('\n')
        else:
            self.missing_newline = True

    def dump_append(self):
        for t in self.append_queue:
            if isinstance(t, tuple):
                # file contents (r command)
                self.write(t[1])
            else:
                self.write(t)
        self.append_queue = []

    def read_next(self):
        self.dump_append()
        r = self.inp.read_line()
        if r is None:
            return None
        self.replaced = False
        return r

    # addresses -----------------------------------------------------------
    def match_regex(self, rx, S):
        if rx is None:
            rx = self.last_regex
            if rx is None:
                raise SedError('no previous regular expression')
        else:
            self.last_regex = rx
        return rx.search(S, 0) is not None

    def match1(self, a):
        k = a.kind
        l = self.inp.line_number
        if k == 'num':
            return l == a.n1
        if k == 're':
            return self.match_regex(a.regex, self.ps)
        if k == 'last':
            return self.inp.is_last()
        if k == 'step':
            if a.n2 <= 0:
                return l == a.n1
            return l >= a.n1 and (l - a.n1) % a.n2 == 0
        if k == 'zero':
            return False
        return False

    def match_addr(self, cmd):
        if cmd.a1 is None:
            return True
        if cmd.a2 is None:
            return self.match1(cmd.a1)
        l = self.inp.line_number
        a2 = cmd.a2
        if cmd.range_state == ACTIVE:
            if a2.kind in ('num', 'plus', 'mod'):
                if l < cmd.range_end:
                    return True
                cmd.range_state = CLOSED
                if l == cmd.range_end:
                    return True
                # got past the end: fire only if the first address matches
                return self.match1(cmd.a1)
            else:
                if self.match1(a2):
                    cmd.range_state = CLOSED
                return True
        if cmd.a1.kind == 'zero':
            return False
        if not self.match1(cmd.a1):
            return False
        k = a2.kind
        if k == 'num':
            if a2.n1 <= l:
                cmd.range_state = CLOSED
                return True
            cmd.range_end = a2.n1
        elif k == 'plus':
            if a2.n1 == 0:
                cmd.range_state = CLOSED
                return True
            cmd.range_end = l + a2.n1
        elif k == 'mod':
            if a2.n1 <= 0 or l % a2.n1 == 0:
                cmd.range_state = CLOSED
                return True
            cmd.range_end = (l // a2.n1 + 1) * a2.n1
        cmd.range_state = ACTIVE
        return True

    # s command -----------------------------------------------------------
    def do_subst(self, cmd):
        rx = cmd.regex
        if rx is None:
            rx = self.last_regex
            if rx is None:
                raise SedError('no previous regular expression')
        else:
            self.last_regex = rx
        S = self.ps
        n = len(S)
        ntrack = cmd.max_ref
        pos = 0
        out = []
        count = 0
        did = False
        prev_end = -1
        while pos <= n:
            m = rx.search(S, pos, ntrack)
            if m is None:
                break
            s0, e0, groups = m
            out.append(S[pos:s0])
            if s0 == e0 and s0 == prev_end:
                if s0 < n:
                    out.append(S[s0])
                pos = s0 + 1
                continue
            count += 1
            if count < cmd.nth:
                out.append(S[s0:e0])
            else:
                self.append_replacement(out, cmd.repl, groups, S)
                did = True
            prev_end = e0
            if s0 == e0:
                if s0 < n:
                    out.append(S[s0])
                pos = e0 + 1
            else:
                pos = e0
            if did and not cmd.gflag:
                break
        if not did:
            return False
        if pos <= n:
            out.append(S[pos:])
        self.ps = ''.join(out)
        return True

    @staticmethod
    def _modify(t, typ):
        if typ == 0 or not t:
            return t
        first = t[0]
        rest = t[1:]
        if typ & 4:
            first = c_upper(first)
        elif typ & 8:
            first = c_lower(first)
        elif typ & 1:
            first = c_upper(first)
        elif typ & 2:
            first = c_lower(first)
        if typ & 1:
            rest = c_upper(rest)
        elif typ & 2:
            rest = c_lower(rest)
        return first + rest

    def append_replacement(self, out, pieces, groups, S):
        repl_mode = 0
        for prefix, sid, rtype in pieces:
            if rtype & 12:
                curr = rtype
            else:
                curr = rtype | repl_mode
            repl_mode = 0
            if prefix:
                out.append(self._modify(prefix, curr))
                curr &= ~12
            if sid >= 0:
                if sid < len(groups):
                    gs, ge = groups[sid]
                else:
                    gs, ge = -1, -1
                if gs < 0 or ge == gs:
                    if rtype & 12:
                        repl_mode = curr & 12
                else:
                    out.append(self._modify(S[gs:ge], curr))

    # misc ----------------------------------------------------------------
    def do_list(self, width):
        out = []
        cur = 0
        esc = {'\\': '\\\\', '\a': '\\a', '\b': '\\b', '\f': '\\f',
               '\n': '\\n', '\r': '\\r', '\t': '\\t', '\v': '\\v'}
        for ch in self.ps:
            if ch in esc:
                r = esc[ch]
            else:
                o = ord(ch)
                if 32 <= o < 127:
                    r = ch
                else:
                    r = '\\%03o' % o
            if width > 1 and cur + len(r) > width - 1:
                out.append('\\\n')
                cur = 0
            out.append(r)
            cur += len(r)
        out.append('$\n')
        self.write(''.join(out))

    # main loop -----------------------------------------------------------
    def run(self):
        status = 0
        restart = False
        try:
            while True:
                if not restart:
                    r = self.read_next()
                    if r is None:
                        break
                    self.ps, self.chomped = r
                restart = False
                res = self.execute()
                if res == 'restart':
                    restart = True
                elif res is not None and res[0] == 'quit':
                    status = res[1]
                    break
        except SedError as e:
            sys.stderr.write('sed: -e expression #1, char 0: %s\n' % e)
            self.flush()
            return 4
        self.flush()
        if self.inp.bad:
            return 2
        return status

    def flush(self):
        data = ''.join(self.out).encode('latin-1', 'replace')
        self.out = []
        try:
            sys.stdout.buffer.write(data)
            sys.stdout.buffer.flush()
        except Exception:
            pass

    def end_cycle(self, autoprint):
        if autoprint and not self.nflag:
            self.output_ps()
        self.dump_append()

    def execute(self):
        cmds = self.cmds
        ncmd = len(cmds)
        pc = 0
        while pc < ncmd:
            cmd = cmds[pc]
            name = cmd.name
            if cmd.a1 is not None:
                m = self.match_addr(cmd) != cmd.negate
            else:
                m = not cmd.negate
            if not m:
                if name == '{':
                    pc = cmd.block_end
                else:
                    pc += 1
                continue
            pc += 1
            if name == '{' or name == '}' or name == ':':
                continue
            if name == 's':
                if self.do_subst(cmd):
                    self.replaced = True
                    if cmd.pflag:
                        for _ in range(cmd.pflag):
                            self.output_ps()
                    if cmd.fname is not None:
                        self.write_file(cmd.fname, self.ps + '\n')
                continue
            if name == 'p':
                self.output_ps()
            elif name == 'd':
                self.end_cycle(False)
                return None
            elif name == 'D':
                k = self.ps.find('\n')
                if k < 0:
                    self.end_cycle(False)
                    return None
                self.ps = self.ps[k + 1:]
                self.dump_append()
                return 'restart'
            elif name == 'n':
                if self.inp.is_last():
                    self.end_cycle(True)
                    return None
                if not self.nflag:
                    self.output_ps()
                r = self.read_next()
                if r is None:
                    self.end_cycle(False)
                    return None
                self.ps, self.chomped = r
            elif name == 'N':
                if self.inp.is_last():
                    self.end_cycle(True)
                    return None
                r = self.read_next()
                if r is None:
                    self.end_cycle(True)
                    return None
                self.ps = self.ps + '\n' + r[0]
                self.chomped = r[1]
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
            elif name == 'z':
                self.ps = ''
            elif name == 'P':
                k = self.ps.find('\n')
                if k < 0:
                    self.output_ps()
                else:
                    self.write(self.ps[:k] + '\n')
            elif name == '=':
                self.write('%d\n' % self.inp.line_number)
            elif name == 'l':
                w = cmd.int_arg if cmd.int_arg is not None else self.line_len
                self.do_list(w)
            elif name == 'i':
                self.write(cmd.text)
            elif name == 'a':
                self.append_queue.append(cmd.text)
            elif name == 'c':
                if cmd.a2 is None or cmd.range_state != ACTIVE:
                    self.write(cmd.text)
                self.end_cycle(False)
                return None
            elif name == 'b':
                pc = cmd.target
            elif name == 't':
                if self.replaced:
                    self.replaced = False
                    pc = cmd.target
            elif name == 'T':
                if not self.replaced:
                    pc = cmd.target
                else:
                    self.replaced = False
            elif name == 'y':
                self.ps = self.ps.translate(cmd.ymap)
            elif name == 'q':
                self.end_cycle(True)
                return ('quit', cmd.int_arg or 0)
            elif name == 'Q':
                return ('quit', cmd.int_arg or 0)
            elif name == 'F':
                self.write(self.inp.cur_name + '\n')
            elif name == 'r':
                try:
                    with open(cmd.fname, 'rb') as fh:
                        data = fh.read().decode('latin-1')
                    if data:
                        if not data.endswith('\n'):
                            data += '\n'
                        self.append_queue.append(data)
                except (IOError, OSError):
                    pass
            elif name == 'w':
                self.write_file(cmd.fname, self.ps + '\n')
            elif name == 'W':
                k = self.ps.find('\n')
                self.write_file(cmd.fname, (self.ps if k < 0 else self.ps[:k]) + '\n')
        self.end_cycle(True)
        return None

    def write_file(self, fname, text):
        if fname == '/dev/stdout':
            self.write(text)
            return
        if fname == '/dev/stderr':
            sys.stderr.write(text)
            return
        if not hasattr(self, '_wfiles'):
            self._wfiles = {}
        try:
            fh = self._wfiles.get(fname)
            if fh is None:
                fh = open(fname, 'wb')
                self._wfiles[fname] = fh
            fh.write(text.encode('latin-1', 'replace'))
            fh.flush()
        except (IOError, OSError):
            pass


# ---------------------------------------------------------------------------
# Command line
# ---------------------------------------------------------------------------

def main(argv):
    nflag = False
    ere = False
    separate = False
    line_len = 70
    scripts = []
    positional = []
    i = 0
    only_files = False
    while i < len(argv):
        a = argv[i]
        i += 1
        if only_files or a == '-' or not a.startswith('-'):
            positional.append(a)
            continue
        if a == '--':
            only_files = True
            continue
        if a.startswith('--'):
            name, eq, val = a[2:].partition('=')
            if name in ('quiet', 'silent'):
                nflag = True
            elif name == 'regexp-extended':
                ere = True
            elif name == 'separate':
                separate = True
            elif name == 'expression':
                if not eq:
                    val = argv[i] if i < len(argv) else ''
                    i += 1
                scripts.append(val)
            elif name == 'file':
                if not eq:
                    val = argv[i] if i < len(argv) else ''
                    i += 1
                try:
                    with open(val, 'rb') as fh:
                        t = fh.read().decode('latin-1')
                    if t.endswith('\n'):
                        t = t[:-1]
                    scripts.append(t)
                except (IOError, OSError):
                    sys.stderr.write('sed: couldn\'t open file %s\n' % val)
                    return 1
            elif name == 'line-length':
                if not eq:
                    val = argv[i] if i < len(argv) else '70'
                    i += 1
                line_len = int(val)
            elif name in ('posix', 'debug', 'sandbox', 'unbuffered',
                          'binary', 'follow-symlinks', 'null-data',
                          'zero-terminated'):
                pass
            continue
        j = 1
        while j < len(a):
            c = a[j]
            j += 1
            if c == 'n':
                nflag = True
            elif c in 'Er':
                ere = True
            elif c == 's':
                separate = True
            elif c in 'ef':
                if j < len(a):
                    val = a[j:]
                else:
                    val = argv[i] if i < len(argv) else ''
                    i += 1
                if c == 'e':
                    scripts.append(val)
                else:
                    try:
                        with open(val, 'rb') as fh:
                            t = fh.read().decode('latin-1')
                        if t.endswith('\n'):
                            t = t[:-1]
                        scripts.append(t)
                    except (IOError, OSError):
                        sys.stderr.write('sed: couldn\'t open file %s\n' % val)
                        return 1
                break
            elif c == 'l':
                if j < len(a):
                    val = a[j:]
                else:
                    val = argv[i] if i < len(argv) else '70'
                    i += 1
                try:
                    line_len = int(val)
                except ValueError:
                    pass
                break
            elif c == 'i':
                break
            else:
                pass
    if not scripts:
        if not positional:
            sys.stderr.write('Usage: sed [OPTION]... {script-only-if-no-other-script} [input-file]...\n')
            return 1
        scripts.append(positional.pop(0))
    script = '\n'.join(scripts)
    if script.startswith('#n') and (len(script) == 2 or script[2] == '\n'):
        nflag = True
    try:
        cmds = ScriptParser(script, ere).parse()
    except (SedError, IndexError, ValueError) as e:
        sys.stderr.write('sed: -e expression #1, char 0: %s\n' % e)
        return 1
    files = positional if positional else ['-']
    sed = Sed(cmds, files, nflag, separate, line_len)
    return sed.run()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
