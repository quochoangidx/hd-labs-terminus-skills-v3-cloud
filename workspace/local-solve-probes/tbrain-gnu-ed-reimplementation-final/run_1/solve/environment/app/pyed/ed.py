"""pyed: a GNU ed 1.19 replacement in pure Python.

Usage: python3 /app/pyed/ed.py [OPTIONS] [FILE]
"""

import os
import stat
import sys
import threading


# ---------------------------------------------------------------------------
# POSIX regular expressions (glibc flavoured), leftmost-longest matching
# ---------------------------------------------------------------------------

class RegexError(Exception):
    pass


K_SET, K_EMPTY, K_ASSERT, K_GROUP, K_BREF, K_CAT, K_ALT, K_REP = range(8)

A_BOL, A_EOL, A_BUFF, A_BUFL, A_WFIRST, A_WLAST, A_WDELIM, A_NWDELIM = range(8)

(T_END, T_CHAR, T_ANY, T_BRACKET, T_BREF, T_OPEN, T_CLOSE, T_ALT, T_STAR,
 T_PLUS, T_QUES, T_ODUP, T_CDUP, T_ANCHOR, T_CLASS) = range(15)

RE_DUP_MAX = 0x7fff

WORDCH = frozenset('abcdefghijklmnopqrstuvwxyz'
                   'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_')


def _cls(pred):
    return frozenset(chr(i) for i in range(256) if pred(i))


CLASSES = {
    'alpha': _cls(lambda i: 65 <= i <= 90 or 97 <= i <= 122),
    'upper': _cls(lambda i: 65 <= i <= 90),
    'lower': _cls(lambda i: 97 <= i <= 122),
    'digit': _cls(lambda i: 48 <= i <= 57),
    'alnum': _cls(lambda i: 65 <= i <= 90 or 97 <= i <= 122 or 48 <= i <= 57),
    'xdigit': _cls(lambda i: 48 <= i <= 57 or 65 <= i <= 70 or 97 <= i <= 102),
    'space': _cls(lambda i: i == 32 or 9 <= i <= 13),
    'blank': _cls(lambda i: i == 32 or i == 9),
    'print': _cls(lambda i: 32 <= i <= 126),
    'graph': _cls(lambda i: 33 <= i <= 126),
    'punct': _cls(lambda i: 33 <= i <= 126 and not (
        65 <= i <= 90 or 97 <= i <= 122 or 48 <= i <= 57)),
    'cntrl': _cls(lambda i: i < 32 or i == 127),
}


class RNode(object):
    __slots__ = ('k', 'a', 'b', 'c', 'id')

    def __init__(self, k, a=None, b=None, c=None):
        self.k = k
        self.a = a
        self.b = b
        self.c = c
        self.id = 0


def _table(chars, neg, icase):
    t = [False] * 256
    for ch in chars:
        o = ord(ch)
        if o < 256:
            t[o] = True
    if icase:
        for i in range(65, 91):
            if t[i] or t[i + 32]:
                t[i] = t[i + 32] = True
    if neg:
        t = [not x for x in t]
    return t


class Parser(object):
    def __init__(self, pat, ere, icase):
        self.p = pat
        self.n = len(pat)
        self.ere = ere
        self.icase = icase
        self.i = 0
        self.nsub = 0
        self.completed = set()
        self.has_bref = False
        self.tok = None

    # -- tokens --------------------------------------------------------
    def peek(self, i, caret_here=False):
        p = self.p
        n = self.n
        ere = self.ere
        if i >= n:
            return (T_END, None, 0)
        c = p[i]
        if c == '\\':
            if i + 1 >= n:
                raise RegexError('Trailing backslash')
            c2 = p[i + 1]
            if not ere:
                if c2 == '|':
                    return (T_ALT, None, 2)
                if c2 == '(':
                    return (T_OPEN, None, 2)
                if c2 == ')':
                    return (T_CLOSE, None, 2)
                if c2 == '+':
                    return (T_PLUS, '+', 2)
                if c2 == '?':
                    return (T_QUES, '?', 2)
                if c2 == '{':
                    return (T_ODUP, '{', 2)
                if c2 == '}':
                    return (T_CDUP, '}', 2)
            if '1' <= c2 <= '9':
                return (T_BREF, ord(c2) - 48, 2)
            if c2 == '<':
                return (T_ANCHOR, A_WFIRST, 2)
            if c2 == '>':
                return (T_ANCHOR, A_WLAST, 2)
            if c2 == 'b':
                return (T_ANCHOR, A_WDELIM, 2)
            if c2 == 'B':
                return (T_ANCHOR, A_NWDELIM, 2)
            if c2 == '`':
                return (T_ANCHOR, A_BUFF, 2)
            if c2 == "'":
                return (T_ANCHOR, A_BUFL, 2)
            if c2 in 'wWsS':
                return (T_CLASS, c2, 2)
            return (T_CHAR, c2, 2)
        if c == '*':
            return (T_STAR, '*', 1)
        if c == '.':
            return (T_ANY, None, 1)
        if c == '[':
            return (T_BRACKET, None, 1)
        if c == '^':
            if ere or i == 0 or caret_here:
                return (T_ANCHOR, A_BOL, 1)
            return (T_CHAR, '^', 1)
        if c == '$':
            if ere or i + 1 == n:
                return (T_ANCHOR, A_EOL, 1)
            nt = self.peek(i + 1)
            if nt[0] in (T_ALT, T_CLOSE):
                return (T_ANCHOR, A_EOL, 1)
            return (T_CHAR, '$', 1)
        if ere:
            if c == '|':
                return (T_ALT, None, 1)
            if c == '(':
                return (T_OPEN, None, 1)
            if c == ')':
                return (T_CLOSE, None, 1)
            if c == '+':
                return (T_PLUS, '+', 1)
            if c == '?':
                return (T_QUES, '?', 1)
            if c == '{':
                return (T_ODUP, '{', 1)
            if c == '}':
                return (T_CDUP, '}', 1)
        return (T_CHAR, c, 1)

    def fetch(self, caret_here=False):
        t = self.peek(self.i, caret_here)
        self.i += t[2]
        self.tok = t

    # -- node helpers ----------------------------------------------------
    def charnode(self, ch):
        return RNode(K_SET, _table([ch], False, self.icase))

    # -- grammar -----------------------------------------------------------
    def parse(self):
        self.fetch(True)
        tree = self.parse_reg_exp(0)
        if self.tok[0] != T_END:
            raise RegexError('Unmatched ) or \\)')
        return tree

    def parse_reg_exp(self, nest):
        initial = set(self.completed)
        branches = [self.parse_branch(nest)]
        while self.tok[0] == T_ALT:
            self.fetch(True)
            t = self.tok[0]
            if t != T_ALT and t != T_END and (nest == 0 or t != T_CLOSE):
                acc = self.completed
                self.completed = set(initial)
                b = self.parse_branch(nest)
                self.completed |= acc
            else:
                b = RNode(K_EMPTY)
            branches.append(b)
        if len(branches) == 1:
            return branches[0]
        return RNode(K_ALT, branches)

    def parse_branch(self, nest):
        items = []
        e = self.parse_expression(nest)
        if e is not None:
            items.append(e)
        while self.tok[0] != T_ALT and self.tok[0] != T_END and \
                (nest == 0 or self.tok[0] != T_CLOSE):
            e = self.parse_expression(nest)
            if e is not None:
                items.append(e)
        if not items:
            return RNode(K_EMPTY)
        if len(items) == 1:
            return items[0]
        return RNode(K_CAT, items)

    def parse_expression(self, nest):
        t, v = self.tok[0], self.tok[1]
        ere = self.ere
        if t == T_CHAR:
            node = self.charnode(v)
        elif t == T_ANY:
            node = RNode(K_SET, [i != 0 for i in range(256)])
        elif t == T_BRACKET:
            node = self.parse_bracket()
        elif t == T_BREF:
            if v not in self.completed:
                raise RegexError('Invalid back reference')
            self.has_bref = True
            node = RNode(K_BREF, v)
        elif t == T_OPEN:
            node = self.parse_sub_exp(nest + 1)
        elif t == T_ODUP:
            raise RegexError('Invalid preceding regular expression')
        elif t in (T_STAR, T_PLUS, T_QUES):
            if ere:
                raise RegexError('Invalid preceding regular expression')
            node = self.charnode(v)
        elif t == T_CLOSE:
            if not ere:
                raise RegexError('Unmatched ) or \\)')
            node = self.charnode(')')
        elif t == T_CDUP:
            node = self.charnode('}')
        elif t == T_ANCHOR:
            node = RNode(K_ASSERT, v)
            self.fetch()
            return node
        elif t == T_CLASS:
            if v in 'wW':
                node = RNode(K_SET, _table(WORDCH, v == 'W', False))
            else:
                node = RNode(K_SET, _table(CLASSES['space'], v == 'S', False))
        else:  # T_ALT, T_END
            return None
        self.fetch()
        while self.tok[0] in (T_STAR, T_PLUS, T_QUES, T_ODUP):
            node = self.parse_dup(node)
            if not ere and self.tok[0] in (T_STAR, T_ODUP):
                raise RegexError('Invalid preceding regular expression')
        return node

    def parse_sub_exp(self, nest):
        self.nsub += 1
        idx = self.nsub
        self.fetch(True)
        if self.tok[0] == T_CLOSE:
            child = RNode(K_EMPTY)
        else:
            child = self.parse_reg_exp(nest)
            if self.tok[0] != T_CLOSE:
                raise RegexError('Unmatched ( or \\(')
        if idx <= 9:
            self.completed.add(idx)
        return RNode(K_GROUP, idx, child)

    def fetch_number(self):
        num = -1
        while True:
            self.fetch()
            t, c = self.tok[0], self.tok[1]
            if t == T_END:
                return -2
            if t == T_CDUP or (t == T_CHAR and c == ','):
                break
            if t != T_CHAR or not ('0' <= c <= '9') or num == -2:
                num = -2
            elif num == -1:
                num = ord(c) - 48
            else:
                num = min(RE_DUP_MAX + 1, num * 10 + ord(c) - 48)
        return num

    def parse_dup(self, node):
        t = self.tok[0]
        if t == T_STAR:
            lo, hi = 0, -1
        elif t == T_PLUS:
            lo, hi = 1, -1
        elif t == T_QUES:
            lo, hi = 0, 1
        else:
            end = 0
            start = self.fetch_number()
            if start == -1:
                if self.tok[0] == T_CHAR and self.tok[1] == ',':
                    start = 0
                else:
                    raise RegexError('Invalid content of \\{\\}')
            if start != -2:
                if self.tok[0] == T_CDUP:
                    end = start
                elif self.tok[0] == T_CHAR and self.tok[1] == ',':
                    end = self.fetch_number()
                else:
                    end = -2
            if start == -2 or end == -2:
                raise RegexError('Invalid content of \\{\\}')
            if (end != -1 and start > end) or self.tok[0] != T_CDUP:
                raise RegexError('Invalid content of \\{\\}')
            if (start if end == -1 else end) > RE_DUP_MAX:
                raise RegexError('Regular expression too big')
            lo, hi = start, end
        self.fetch()
        if node is None:
            return None
        return RNode(K_REP, node, lo, hi)

    # -- bracket expressions -------------------------------------------------
    def peek_bracket(self, i):
        p = self.p
        n = self.n
        if i >= n:
            return ('end', None, 0)
        c = p[i]
        if c == '[' and i + 1 < n and p[i + 1] in '.:=':
            return ('open' + p[i + 1], p[i + 1], 2)
        if c == ']':
            return ('close', c, 1)
        if c == '^':
            return ('nonmatch', c, 1)
        if c == '-':
            return ('range', c, 1)
        return ('char', c, 1)

    def bracket_symbol(self, i, tok):
        # i points after the "[x" opener
        p = self.p
        n = self.n
        delim = tok[1]
        if i >= n:
            raise RegexError('Unmatched [')
        name = []
        while True:
            if len(name) >= 32:
                raise RegexError('Unmatched [')
            if i >= n:
                raise RegexError('Unmatched [')
            ch = p[i]
            i += 1
            if i >= n:
                raise RegexError('Unmatched [')
            if ch == delim and p[i] == ']':
                break
            name.append(ch)
        i += 1
        name = ''.join(name)
        if delim == ':':
            return ('class', name), i
        if delim == '=':
            return ('equiv', name), i
        return ('coll', name), i

    def bracket_element(self, i, tok, accept_hyphen):
        i += tok[2]
        if tok[0] in ('open.', 'open:', 'open='):
            return self.bracket_symbol(i, tok)
        if tok[0] == 'range' and not accept_hyphen:
            t2 = self.peek_bracket(i)
            if t2[0] != 'close':
                raise RegexError('Invalid range end')
        return ('char', tok[1]), i

    @staticmethod
    def elem_char(elem):
        if elem[0] == 'char':
            return elem[1]
        if elem[0] == 'coll':
            if len(elem[1]) != 1:
                raise RegexError('Invalid collation character')
            return elem[1]
        raise RegexError('Invalid range end')

    def parse_bracket(self):
        i = self.i
        chars = set()
        neg = False
        tok = self.peek_bracket(i)
        if tok[0] == 'nonmatch':
            neg = True
            i += tok[2]
            tok = self.peek_bracket(i)
        if tok[0] == 'close':
            tok = ('char', ']', 1)
        first = True
        while True:
            if tok[0] == 'end':
                raise RegexError('Unmatched [')
            start, i = self.bracket_element(i, tok, first)
            first = False
            tok = self.peek_bracket(i)
            is_range = False
            tok2 = None
            if start[0] not in ('class', 'equiv'):
                if tok[0] == 'end':
                    raise RegexError('Unmatched [')
                if tok[0] == 'range':
                    j = i + tok[2]
                    tok2 = self.peek_bracket(j)
                    if tok2[0] == 'end':
                        raise RegexError('Unmatched [')
                    if tok2[0] == 'close':
                        tok = ('char', '-', 1)
                    else:
                        is_range = True
                        i = j
            if is_range:
                end, i = self.bracket_element(i, tok2, True)
                tok = self.peek_bracket(i)
                a = self.elem_char(start)
                b = self.elem_char(end)
                if ord(a) > ord(b):
                    raise RegexError('Invalid range end')
                for o in range(ord(a), ord(b) + 1):
                    chars.add(chr(o))
            else:
                kind, val = start
                if kind == 'char':
                    chars.add(val)
                elif kind in ('coll', 'equiv'):
                    if len(val) != 1:
                        raise RegexError('Invalid collation character')
                    chars.add(val)
                else:
                    name = val
                    if self.icase and name in ('upper', 'lower'):
                        name = 'alpha'
                    if name not in CLASSES:
                        raise RegexError('Invalid character class name')
                    chars |= CLASSES[name]
            if tok[0] == 'end':
                raise RegexError('Unmatched [')
            if tok[0] == 'close':
                i += tok[2]
                break
        self.i = i
        return RNode(K_SET, _table(chars, neg, self.icase))


class Regex(object):
    def __init__(self, pat, ere=False, icase=False):
        parser = Parser(pat, ere, icase)
        self.root = parser.parse()
        self.nsub = parser.nsub
        self.has_bref = parser.has_bref
        self.icase = icase
        self._count = 0
        self._number(self.root)

    def _number(self, node):
        self._count += 1
        node.id = self._count
        k = node.k
        if k == K_GROUP:
            self._number(node.b)
        elif k in (K_CAT, K_ALT):
            for x in node.a:
                self._number(x)
        elif k == K_REP:
            self._number(node.a)

    def search(self, s, notbol=False):
        """Return (start, end, groups) of the leftmost-longest match."""
        if self.has_bref:
            return _BTMatcher(self, s, notbol).search()
        m = _Matcher(self, s, notbol)
        root = self.root
        for st in range(len(s) + 1):
            e_set = m.ends(root, st)
            if e_set:
                e = max(e_set)
                caps = [None] * (self.nsub + 1)
                m.assign(root, st, e, caps)
                return st, e, caps
        return None

    def matches(self, s):
        return self.search(s) is not None


def _check_assert(a, s, n, p, notbol):
    if a == A_BOL:
        return p == 0 and not notbol
    if a == A_EOL:
        return p == n
    if a == A_BUFF:
        return p == 0
    if a == A_BUFL:
        return p == n
    pw = p > 0 and s[p - 1] in WORDCH
    nw = p < n and s[p] in WORDCH
    if a == A_WFIRST:
        return nw and not pw
    if a == A_WLAST:
        return pw and not nw
    if a == A_WDELIM:
        return pw != nw
    return pw == nw


class _Matcher(object):
    """Set-based matcher (no back-references), memoised on positions."""

    def __init__(self, rx, s, notbol):
        self.rx = rx
        self.s = s
        self.n = len(s)
        self.notbol = notbol
        self.memo = {}
        self.cmemo = {}
        self.rmemo = {}

    def ends(self, node, p):
        key = (node.id, p)
        r = self.memo.get(key)
        if r is not None:
            return r
        k = node.k
        if k == K_SET:
            if p < self.n and ord(self.s[p]) < 256 and node.a[ord(self.s[p])]:
                r = frozenset((p + 1,))
            else:
                r = frozenset()
        elif k == K_EMPTY:
            r = frozenset((p,))
        elif k == K_ASSERT:
            if _check_assert(node.a, self.s, self.n, p, self.notbol):
                r = frozenset((p,))
            else:
                r = frozenset()
        elif k == K_GROUP:
            r = self.ends(node.b, p)
        elif k == K_CAT:
            r = self.cat_ends(node, 0, p)
        elif k == K_ALT:
            acc = set()
            for x in node.a:
                acc |= self.ends(x, p)
            r = frozenset(acc)
        elif k == K_REP:
            r = self.rep_ends(node, 0, p)
        else:
            r = frozenset()
        self.memo[key] = r
        return r

    def cat_ends(self, node, i, p):
        items = node.a
        if i == len(items):
            return frozenset((p,))
        key = (node.id, i, p)
        r = self.cmemo.get(key)
        if r is not None:
            return r
        acc = set()
        for q in self.ends(items[i], p):
            acc |= self.cat_ends(node, i + 1, q)
        r = frozenset(acc)
        self.cmemo[key] = r
        return r

    def rep_ends(self, node, done, p):
        lo, hi = node.b, node.c
        state = done if hi >= 0 else min(done, lo)
        key = (node.id, state, p)
        r = self.rmemo.get(key)
        if r is not None:
            return r
        acc = set()
        if done >= lo:
            acc.add(p)
        if hi < 0 or done < hi:
            for q in self.ends(node.a, p):
                if done >= lo and q == p:
                    continue
                acc |= self.rep_ends(node, done + 1, q)
        r = frozenset(acc)
        self.rmemo[key] = r
        return r

    def assign(self, node, p, e, caps):
        k = node.k
        if k == K_GROUP:
            caps[node.a] = (p, e)
            self.assign(node.b, p, e, caps)
        elif k == K_CAT:
            items = node.a
            last = len(items) - 1
            for i, item in enumerate(items):
                if i == last:
                    self.assign(item, p, e, caps)
                    break
                best = -1
                for q in self.ends(item, p):
                    if best < q <= e and e in self.cat_ends(node, i + 1, q):
                        best = q
                self.assign(item, p, best, caps)
                p = best
        elif k == K_ALT:
            for x in node.a:
                if e in self.ends(x, p):
                    self.assign(x, p, e, caps)
                    return
        elif k == K_REP:
            lo, hi = node.b, node.c
            done = 0
            while True:
                if done >= lo and p == e:
                    return
                best = -1
                if hi < 0 or done < hi:
                    for q in self.ends(node.a, p):
                        if done >= lo and q == p:
                            continue
                        if best < q <= e and e in self.rep_ends(node, done + 1, q):
                            best = q
                if best < 0:
                    return
                self.assign(node.a, p, best, caps)
                p = best
                done += 1


class _BTMatcher(object):
    """Backtracking matcher used when back-references are present."""

    def __init__(self, rx, s, notbol):
        self.rx = rx
        self.s = s
        self.n = len(s)
        self.notbol = notbol
        self.icase = rx.icase

    def search(self):
        root = self.rx.root
        init = (None,) * (self.rx.nsub + 1)
        n = self.n
        for st in range(n + 1):
            best = None
            for e, caps in self.bt(root, st, init):
                if best is None or e > best[0]:
                    best = (e, caps)
                    if e == n:
                        break
            if best is not None:
                return st, best[0], list(best[1])
        return None

    def bt(self, node, p, caps):
        k = node.k
        s = self.s
        if k == K_SET:
            if p < self.n and ord(s[p]) < 256 and node.a[ord(s[p])]:
                yield p + 1, caps
        elif k == K_EMPTY:
            yield p, caps
        elif k == K_ASSERT:
            if _check_assert(node.a, s, self.n, p, self.notbol):
                yield p, caps
        elif k == K_GROUP:
            idx = node.a
            for q, c in self.bt(node.b, p, caps):
                c2 = list(c)
                c2[idx] = (p, q)
                yield q, tuple(c2)
        elif k == K_BREF:
            g = caps[node.a] if node.a < len(caps) else None
            if g is None:
                return
            sub = s[g[0]:g[1]]
            L = len(sub)
            seg = s[p:p + L]
            if len(seg) != L:
                return
            if seg == sub or (self.icase and seg.lower() == sub.lower()):
                yield p + L, caps
        elif k == K_CAT:
            for r in self.cat(node.a, 0, p, caps):
                yield r
        elif k == K_ALT:
            for x in node.a:
                for r in self.bt(x, p, caps):
                    yield r
        elif k == K_REP:
            for r in self.rep(node, 0, p, caps):
                yield r

    def cat(self, items, i, p, caps):
        if i == len(items):
            yield p, caps
            return
        for q, c in self.bt(items[i], p, caps):
            for r in self.cat(items, i + 1, q, c):
                yield r

    def rep(self, node, done, p, caps):
        lo, hi = node.b, node.c
        if hi < 0 or done < hi:
            for q, c in self.bt(node.a, p, caps):
                if done >= lo and q == p:
                    continue
                for r in self.rep(node, done + 1, q, c):
                    yield r
        if done >= lo:
            yield p, caps


# ---------------------------------------------------------------------------
# The editor
# ---------------------------------------------------------------------------

class EdError(Exception):
    pass


QUIT, ERR, EMOD = -1, -2, -3
PF_L, PF_N, PF_P = 1, 2, 4
SF_G, SF_P, SF_R, SF_NONE = 1, 2, 4, 8
INT_MAX = 2147483647


class Line(object):
    __slots__ = ('t',)

    def __init__(self, t):
        self.t = t


class Cursor(object):
    __slots__ = ('s', 'i')

    def __init__(self, s, i=0):
        self.s = s
        self.i = i

    def peek(self, k=0):
        j = self.i + k
        if 0 <= j < len(self.s):
            return self.s[j]
        return ''

    def getc(self):
        c = self.peek()
        self.i += 1
        return c

    def skip_blanks(self):
        while self.peek() in (' ', '\t') and self.peek() != '':
            self.i += 1


def is_digit(c):
    return c != '' and '0' <= c <= '9'


class Input(object):
    def __init__(self, data):
        self.data = data
        self.pos = 0

    def get_line(self):
        d = self.data
        if self.pos >= len(d):
            return None
        j = d.find('\n', self.pos)
        if j < 0:
            line = d[self.pos:] + '\n'
            self.pos = len(d)
        else:
            line = d[self.pos:j + 1]
            self.pos = j + 1
        return line


class Ed(object):
    def __init__(self, inp, opts):
        self.inp = inp
        self.out = []
        self.ere = opts['E']
        self.loose = opts['l']
        self.quiet = opts['q']
        self.restricted = opts['r']
        self.scripted = opts['s']
        self.prompt = opts['p'] if opts['p'] is not None else '*'
        self.prompt_on = opts['p'] is not None
        self.stdin_regular = opts['regular']
        self.lines = []
        self.cur = 0
        self.first_addr = 0
        self.second_addr = 0
        self.modified = False
        self.marks = {}
        self.cut = []
        self.def_filename = ''
        self.last_regex = None
        self.subst_regex = None
        self.template = None
        self.s_pflags = 0
        self.s_pmask = PF_P
        self.s_snum = 1
        self.u_snap = None
        self.u_ok = False
        self.active_list = []
        self.active_pos = 0
        self.active_set = set()
        self.window_lines = 22
        self.window_columns = 72

    # -- output ------------------------------------------------------------
    def put(self, s):
        self.out.append(s)

    def flush(self):
        if self.out:
            data = ''.join(self.out).encode('latin-1', 'replace')
            self.out = []
            try:
                sys.stdout.buffer.write(data)
                sys.stdout.buffer.flush()
            except (OSError, ValueError):
                pass

    def diag(self, msg):
        if not self.quiet and msg:
            try:
                sys.stderr.write(msg + '\n')
            except Exception:
                pass

    # -- basic helpers -----------------------------------------------------
    def last(self):
        return len(self.lines)

    def invalid_address(self):
        raise EdError('Invalid address')

    def parse_int(self, cur):
        j = cur.i
        s = cur.s
        while j < len(s) and '0' <= s[j] <= '9':
            j += 1
        n = int(s[cur.i:j])
        cur.i = j
        if n > INT_MAX:
            raise EdError('Number out of range')
        return n

    def clear_undo(self):
        self.u_snap = (list(self.lines), self.cur, self.modified)
        self.u_ok = False

    def reset_undo(self):
        self.u_snap = None
        self.u_ok = False

    def undo(self, isglobal):
        if not self.u_ok or self.u_snap is None:
            raise EdError('Nothing to undo')
        snap = (list(self.lines), self.cur, self.modified)
        lines, cur, mod = self.u_snap
        self.lines = list(lines)
        self.cur = cur
        self.modified = mod
        self.u_snap = snap
        if isglobal:
            self.clear_active()

    def clear_active(self):
        self.active_list = []
        self.active_pos = 0
        self.active_set = set()

    def unset_active(self, lines):
        if self.active_set:
            for l in lines:
                self.active_set.discard(id(l))

    def line_addr(self, lp):
        for i, l in enumerate(self.lines):
            if l is lp:
                return i + 1
        return -1

    # -- addresses -----------------------------------------------------------
    def extract_addresses(self, cur):
        first = True
        fa = sa = -1
        cur.skip_blanks()
        while True:
            ch = cur.peek()
            if is_digit(ch):
                n = self.parse_int(cur)
                if first:
                    first = False
                    sa = n
                else:
                    sa += n
            elif ch in (' ', '\t') and ch != '':
                cur.skip_blanks()
            elif ch in ('+', '-') and ch != '':
                if first:
                    first = False
                    sa = self.cur
                if is_digit(cur.peek(1)):
                    cur.i += 1
                    n = self.parse_int(cur)
                    sa += -n if ch == '-' else n
                else:
                    cur.i += 1
                    sa += -1 if ch == '-' else 1
            elif ch in ('.', '$') and ch != '':
                if not first:
                    self.invalid_address()
                first = False
                cur.i += 1
                sa = self.cur if ch == '.' else self.last()
            elif ch in ('/', '?') and ch != '':
                if not first:
                    self.invalid_address()
                sa = self.next_matching_addr(cur)
                first = False
            elif ch == "'":
                if not first:
                    self.invalid_address()
                first = False
                cur.i += 1
                sa = self.get_marked_addr(cur.getc())
            elif ch in ('%', ',', ';') and ch != '':
                if first:
                    if fa < 0:
                        fa = self.cur if ch == ';' else 1
                        sa = self.last()
                else:
                    if sa < 0 or sa > self.last():
                        self.invalid_address()
                    if ch == ';':
                        self.cur = sa
                    fa = sa
                    first = True
                cur.i += 1
            else:
                if not first and (sa < 0 or sa > self.last()):
                    self.invalid_address()
                cnt = 0
                if sa >= 0:
                    cnt = 2 if fa >= 0 else 1
                if cnt <= 0:
                    sa = self.cur
                if cnt <= 1:
                    fa = sa
                self.first_addr = fa
                self.second_addr = sa
                return cnt

    def get_marked_addr(self, c):
        if not ('a' <= c <= 'z') or len(c) != 1:
            raise EdError('Invalid mark character')
        lp = self.marks.get(c)
        if lp is None:
            self.invalid_address()
        n = self.line_addr(lp)
        if n < 0:
            self.invalid_address()
        return n

    def next_matching_addr(self, cur):
        forward = cur.peek() == '/'
        rx = self.get_compiled_regex(cur)
        last = self.last()
        start = self.cur
        addr = start
        while True:
            if forward:
                addr = addr + 1 if addr < last else 0
            else:
                addr = addr - 1 if addr > 0 else last
            if addr:
                if rx.search(self.lines[addr - 1].t) is not None:
                    return addr
            if addr == start:
                break
        raise EdError('No match')

    def check_addr_range(self, n, m, addr_cnt):
        if addr_cnt == 0:
            self.first_addr = n
            self.second_addr = m
        if self.first_addr < 1 or self.first_addr > self.second_addr or \
                self.second_addr > self.last():
            self.invalid_address()

    def check_addr_range2(self, addr_cnt):
        self.check_addr_range(self.cur, self.cur, addr_cnt)

    def check_second_addr(self, addr, addr_cnt):
        if addr_cnt == 0:
            self.second_addr = addr
        if self.second_addr < 1 or self.second_addr > self.last():
            self.invalid_address()

    def get_third_addr(self, cur):
        o1, o2 = self.first_addr, self.second_addr
        self.extract_addresses(cur)
        addr = self.second_addr
        if addr < 0 or addr > self.last():
            self.invalid_address()
        self.first_addr, self.second_addr = o1, o2
        return addr

    # -- regular expressions ---------------------------------------------------
    def extract_pattern(self, cur, delim):
        s = cur.s
        j = cur.i
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
        pat = s[cur.i:j]
        cur.i = j
        return pat

    @staticmethod
    def parse_char_class(s, j):
        n = len(s)
        if j < n and s[j] == '^':
            j += 1
        if j < n and s[j] == ']':
            j += 1
        while j < n and s[j] != ']' and s[j] != '\n':
            if s[j] == '[' and j + 1 < n and s[j + 1] in '.:=':
                d = s[j + 1]
                j += 2
                c = s[j] if j < n else ''
                while True:
                    if j >= n:
                        return -1
                    if s[j] == ']' and c == d:
                        break
                    c = s[j]
                    if c == '\n':
                        return -1
                    j += 1
            j += 1
        if j < n and s[j] == ']':
            return j
        return -1

    def compile_regex(self, pat, icase):
        if pat == '':
            if icase:
                raise EdError('Invalid pattern')
            if self.last_regex is None:
                raise EdError('No previous pattern')
            return self.last_regex
        try:
            rx = Regex(pat, self.ere, icase)
        except RegexError as e:
            raise EdError(str(e))
        except RecursionError:
            raise EdError('Regular expression too big')
        self.last_regex = rx
        return rx

    def get_compiled_regex(self, cur):
        delim = cur.getc()
        if delim in (' ', '\n', ''):
            raise EdError('Invalid pattern delimiter')
        pat = self.extract_pattern(cur, delim)
        if cur.peek() == delim:
            cur.i += 1
        icase = False
        if cur.peek() == 'I':
            icase = True
            cur.i += 1
        return self.compile_regex(pat, icase)

    # -- printing ------------------------------------------------------------
    def print_lines(self, frm, to, pflags):
        if frm == 0:
            self.invalid_address()
        for addr in range(frm, to + 1):
            self.cur = addr
            self.print_line(self.lines[addr - 1].t, pflags)

    def print_line(self, text, pflags):
        out = []
        col = 0
        if pflags & PF_N:
            out.append('%d\t' % self.cur)
            col = 8
        if not (pflags & PF_L):
            out.append(text)
        else:
            esc = {'\a': 'a', '\b': 'b', '\f': 'f', '\n': 'n', '\r': 'r',
                   '\t': 't', '\v': 'v'}
            cols = self.window_columns
            for ch in text:
                col += 1
                if col > cols:
                    col = 1
                    out.append('\\\n')
                o = ord(ch)
                if 32 <= o <= 126:
                    if ch == '$' or ch == '\\':
                        col += 1
                        out.append('\\')
                    out.append(ch)
                else:
                    col += 1
                    out.append('\\')
                    if o and ch in esc:
                        out.append(esc[ch])
                    else:
                        col += 2
                        o &= 0xff
                        out.append(chr(((o >> 6) & 7) + 48))
                        out.append(chr(((o >> 3) & 7) + 48))
                        out.append(chr((o & 7) + 48))
            out.append('$')
        out.append('\n')
        self.put(''.join(out))

    # -- command helpers -------------------------------------------------------
    def get_command_suffix(self, cur, pflags=0):
        while True:
            ch = cur.peek()
            if ch == 'l':
                if pflags & PF_L:
                    break
                pflags |= PF_L
            elif ch == 'n':
                if pflags & PF_N:
                    break
                pflags |= PF_N
            elif ch == 'p':
                if pflags & PF_P:
                    break
                pflags |= PF_P
            else:
                break
            cur.i += 1
        if cur.getc() != '\n':
            raise EdError('Invalid command suffix')
        return pflags

    def unexpected_address(self, addr_cnt):
        if addr_cnt > 0:
            raise EdError('Unexpected address')

    def unexpected_command_suffix(self, cur):
        ch = cur.peek()
        if ch not in (' ', '\t', '\n', '\v', '\f', '\r') or ch == '':
            raise EdError('Unexpected command suffix')

    def may_access_filename(self, name):
        if self.restricted:
            if name.startswith('!'):
                raise EdError('Shell access restricted')
            if name == '..' or '/' in name:
                raise EdError('Access restricted to working directory')

    def get_filename(self, cur, allow_empty=False):
        cur.skip_blanks()
        if cur.peek() != '\n':
            s = cur.s
            j = s.find('\n', cur.i)
            if j < 0:
                j = len(s)
            name = s[cur.i:j]
            cur.i = j + 1
        else:
            cur.i += 1
            name = ''
            if not allow_empty and not self.def_filename:
                raise EdError('No current filename')
        self.may_access_filename(name)
        return name

    def get_extended_line(self, cur):
        s = cur.s
        j = s.find('\n', cur.i)
        if j < 0:
            j = len(s) - 1
        line = s[cur.i:j + 1]
        cur.i = j + 1
        if not self.trailing_escape(line):
            return line
        parts = [line[:-2] + '\n']
        while True:
            nl = self.inp.get_line()
            if nl is None:
                raise EdError('Unexpected end-of-file')
            if self.trailing_escape(nl):
                parts.append(nl[:-2] + '\n')
                continue
            parts.append(nl)
            break
        return ''.join(parts)

    @staticmethod
    def trailing_escape(line):
        if len(line) < 2 or line[-1] != '\n':
            return False
        k = 0
        j = len(line) - 2
        while j >= 0 and line[j] == '\\':
            k += 1
            j -= 1
        return k % 2 == 1

    # -- buffer operations -----------------------------------------------------
    def append_lines(self, cur, addr, insert, isglobal):
        self.cur = addr
        while True:
            if not isglobal:
                line = self.inp.get_line()
                if line is None:
                    return
            else:
                if cur.i >= len(cur.s):
                    return
                j = cur.s.find('\n', cur.i)
                if j < 0:
                    j = len(cur.s) - 1
                line = cur.s[cur.i:j + 1]
                cur.i = j + 1
            if line == '.\n':
                return
            if insert:
                insert = False
                if addr > 0:
                    self.cur = addr - 1
            text = line[:-1] if line.endswith('\n') else line
            self.lines.insert(self.cur, Line(text))
            self.cur += 1
            self.u_ok = True
            self.modified = True

    def delete_lines(self, fa, sa, isglobal):
        dl = self.lines[fa - 1:sa]
        self.cut = [l.t for l in dl]
        del self.lines[fa - 1:sa]
        if isglobal:
            self.unset_active(dl)
        self.cur = min(fa, len(self.lines))
        if dl:
            self.u_ok = True
            self.modified = True

    def join_lines(self, fa, sa, isglobal):
        text = ''.join(l.t for l in self.lines[fa - 1:sa])
        self.delete_lines(fa, sa, isglobal)
        self.lines.insert(fa - 1, Line(text))
        self.cur = fa
        self.u_ok = True
        self.modified = True

    def move_lines(self, fa, sa, addr, isglobal):
        block = self.lines[fa - 1:sa]
        if addr == fa - 1 or addr == sa:
            self.cur = sa
        else:
            del self.lines[fa - 1:sa]
            ins = addr - len(block) if addr > sa else addr
            self.lines[ins:ins] = block
            self.cur = ins + len(block)
            self.u_ok = True
        if isglobal:
            self.unset_active(block)
        self.modified = True

    def copy_lines(self, fa, sa, addr):
        block = [Line(l.t) for l in self.lines[fa - 1:sa]]
        self.lines[addr:addr] = block
        self.cur = addr + len(block)
        if block:
            self.u_ok = True
            self.modified = True

    def put_lines(self, addr):
        if not self.cut:
            raise EdError('Nothing to put')
        block = [Line(t) for t in self.cut]
        self.lines[addr:addr] = block
        self.cur = addr + len(block)
        self.u_ok = True
        self.modified = True

    # -- files -----------------------------------------------------------------
    def read_file(self, fname, addr):
        try:
            with open(fname, 'rb') as f:
                data = f.read()
        except OSError as e:
            self.diag('%s: %s' % (fname, e.strerror))
            raise EdError('Cannot open input file')
        text = data.decode('latin-1')
        size = len(data)
        if text == '':
            new = []
        else:
            new = text.split('\n')
            if text.endswith('\n'):
                new.pop()
            else:
                size += 1
                self.diag('Newline appended')
        block = [Line(t) for t in new]
        self.lines[addr:addr] = block
        self.cur = addr + len(block)
        if block:
            self.u_ok = True
        if not self.scripted:
            self.put('%d\n' % size)
        return len(block)

    def write_file(self, fname, mode, fa, sa):
        if fa > 0:
            data = ''.join(l.t + '\n' for l in self.lines[fa - 1:sa])
        else:
            data = ''
        raw = data.encode('latin-1', 'replace')
        try:
            with open(fname, mode) as f:
                f.write(raw)
        except OSError as e:
            self.diag('%s: %s' % (fname, e.strerror))
            raise EdError('Cannot open output file')
        if not self.scripted:
            self.put('%d\n' % len(raw))
        return len(raw)

    # -- substitution ------------------------------------------------------------
    def extract_replacement(self, cur, delim, isglobal):
        if cur.peek() == '%' and (cur.peek(1) == delim or (
                cur.peek(1) == '\n' and cur.i + 2 >= len(cur.s))):
            cur.i += 1
            if self.template is None:
                raise EdError('No previous substitution')
            return self.template
        buf = []
        while cur.peek() != delim:
            if cur.i >= len(cur.s):
                raise EdError('Missing pattern delimiter')
            c = cur.getc()
            if c == '\n' and cur.i >= len(cur.s):
                cur.i -= 1
                break
            buf.append(c)
            if c == '\\':
                c2 = cur.getc()
                buf.append(c2)
                if c2 == '\n' and not isglobal:
                    nl = self.inp.get_line()
                    if nl is None:
                        raise EdError('Unexpected end-of-file')
                    cur.s = nl
                    cur.i = 0
        return ''.join(buf)

    def apply_template(self, tmpl, txt, so, eo, caps, nsub):
        out = []
        i = 0
        n = len(tmpl)
        while i < n:
            c = tmpl[i]
            if c == '&':
                out.append(txt[so:eo])
            elif c == '\\' and i + 1 < n:
                i += 1
                c2 = tmpl[i]
                if '1' <= c2 <= '9' and ord(c2) - 48 <= nsub:
                    g = caps[ord(c2) - 48] if ord(c2) - 48 < len(caps) else None
                    if g is not None:
                        out.append(txt[g[0]:g[1]])
                else:
                    out.append(c2)
            else:
                out.append(c)
            i += 1
        return ''.join(out)

    def replace_in_line(self, text, snum):
        rx = self.subst_regex
        m = rx.search(text, False)
        if m is None:
            return None
        glob = snum <= 0
        out = []
        txt = text
        matchno = 0
        changed = False
        while True:
            so, eo, caps = m
            matchno += 1
            if glob or snum == matchno:
                changed = True
                out.append(txt[:so])
                out.append(self.apply_template(self.template, txt, so, eo,
                                               caps, rx.nsub))
            else:
                out.append(txt[:eo])
            txt = txt[eo:]
            if not (txt and (not changed or (glob and eo))):
                break
            m = rx.search(txt, True)
            if m is None:
                break
        out.append(txt)
        if not changed:
            return None
        return ''.join(out)

    def search_and_replace(self, fa, sa, snum, isglobal):
        found = False
        lastline = -1
        a = fa
        for _ in range(sa - fa + 1):
            lp = self.lines[a - 1]
            new = self.replace_in_line(lp.t, snum)
            if new is None:
                a += 1
                continue
            parts = new.split('\n')
            self.delete_lines(a, a, isglobal)
            block = [Line(t) for t in parts]
            self.lines[a - 1:a - 1] = block
            self.u_ok = True
            self.modified = True
            a += len(block)
            lastline = a - 1
            found = True
        if not found:
            if not isglobal:
                raise EdError('No match')
        else:
            self.cur = lastline

    def command_s(self, cur, addr_cnt, isglobal):
        self.check_addr_range2(addr_cnt)
        sflags = 0
        snum = self.s_snum
        while True:
            ch = cur.peek()
            if is_digit(ch):
                n = self.parse_int(cur)
                if n <= 0:
                    raise EdError('Invalid count')
                snum = n
                sflags |= SF_NONE
            elif ch == '\n':
                sflags |= SF_NONE
            elif ch == 'g':
                sflags |= SF_G
                cur.i += 1
            elif ch == 'p':
                sflags |= SF_P
                cur.i += 1
            elif ch == 'r':
                sflags |= SF_R
                cur.i += 1
            else:
                if sflags:
                    raise EdError('Invalid command suffix')
            if not (sflags and cur.peek() != '\n'):
                break
        if sflags:
            if self.subst_regex is None or self.template is None:
                raise EdError('No previous substitution')
            if sflags & SF_G:
                snum = 1 if snum <= 0 else 0
            if sflags & SF_P:
                self.s_pflags ^= self.s_pmask
            if sflags & SF_R:
                if self.last_regex is None:
                    raise EdError('No previous pattern')
                self.subst_regex = self.last_regex
            self.s_snum = snum
            cur.getc()  # the newline
        else:
            delim = cur.getc()
            if delim in (' ', '\n', ''):
                raise EdError('Invalid pattern delimiter')
            pat = self.extract_pattern(cur, delim)
            if cur.peek() != delim:
                raise EdError('Missing pattern delimiter')
            cur.i += 1
            tmpl = self.extract_replacement(cur, delim, isglobal)
            pflags = 0
            snum = 1
            icase = False
            if cur.peek() == '\n':
                pflags = PF_P
                cur.i += 1
            else:
                cur.i += 1
                gotg = gotn = False
                while True:
                    ch = cur.peek()
                    if ch == 'g':
                        if gotg or gotn:
                            raise EdError('Invalid command suffix')
                        gotg = True
                        snum = 0
                        cur.i += 1
                    elif is_digit(ch):
                        if gotg or gotn:
                            raise EdError('Invalid command suffix')
                        n = self.parse_int(cur)
                        if n <= 0:
                            raise EdError('Invalid count')
                        gotn = True
                        snum = n
                    elif ch in ('l', 'n', 'p') and ch != '':
                        bit = {'l': PF_L, 'n': PF_N, 'p': PF_P}[ch]
                        if pflags & bit:
                            break
                        pflags |= bit
                        cur.i += 1
                    elif ch in ('I', 'i') and ch != '':
                        icase = True
                        cur.i += 1
                    else:
                        break
                if cur.getc() != '\n':
                    raise EdError('Invalid command suffix')
            rx = self.compile_regex(pat, icase)
            self.subst_regex = rx
            self.template = tmpl
            self.s_pflags = pflags
            self.s_pmask = pflags if pflags else PF_P
            self.s_snum = snum
        if not isglobal:
            self.clear_undo()
        self.search_and_replace(self.first_addr, self.second_addr,
                                self.s_snum, isglobal)
        return self.s_pflags

    # -- global commands -----------------------------------------------------------
    def build_active_list(self, cur, match):
        rx = self.get_compiled_regex(cur)
        self.clear_active()
        lst = []
        for addr in range(self.first_addr, self.second_addr + 1):
            lp = self.lines[addr - 1]
            if (rx.search(lp.t) is not None) == match:
                lst.append(lp)
        self.active_list = lst
        self.active_pos = 0
        self.active_set = set(id(l) for l in lst)

    def next_active(self):
        while self.active_pos < len(self.active_list):
            lp = self.active_list[self.active_pos]
            self.active_pos += 1
            if id(lp) in self.active_set:
                self.active_set.discard(id(lp))
                return lp
        return None

    def exec_global(self, cur, gflags, interactive):
        cmd = None
        if not interactive:
            cmd = self.get_extended_line(cur)
        self.clear_undo()
        while True:
            lp = self.next_active()
            if lp is None:
                break
            addr = self.line_addr(lp)
            if addr < 0:
                continue
            self.cur = addr
            if interactive:
                self.print_lines(self.cur, self.cur, gflags)
                line = self.inp.get_line()
                if line is None:
                    raise EdError('Unexpected end-of-file')
                if line == '\n':
                    continue
                if line == '&\n':
                    if cmd is None:
                        raise EdError('No previous command')
                else:
                    cmd = self.get_extended_line(Cursor(line))
            c2 = Cursor(cmd)
            while c2.i < len(c2.s):
                r = self.exec_command(c2, 0, True)
                if r < 0:
                    raise EdError('')
        self.clear_active()

    # -- command dispatcher ------------------------------------------------------
    def exec_command(self, cur, prev_status, isglobal):
        addr_cnt = self.extract_addresses(cur)
        c = cur.getc()
        pflags = 0
        if c == 'a':
            pflags = self.get_command_suffix(cur)
            if not isglobal:
                self.clear_undo()
            self.append_lines(cur, self.second_addr, False, isglobal)
        elif c == 'c':
            if self.first_addr == 0:
                self.first_addr = 1
            if self.second_addr == 0:
                self.second_addr = 1
            self.check_addr_range2(addr_cnt)
            pflags = self.get_command_suffix(cur)
            if not isglobal:
                self.clear_undo()
            fa = self.first_addr
            self.delete_lines(fa, self.second_addr, isglobal)
            self.append_lines(cur, self.cur, self.cur >= fa, isglobal)
        elif c == 'd':
            self.check_addr_range2(addr_cnt)
            pflags = self.get_command_suffix(cur)
            if not isglobal:
                self.clear_undo()
            self.delete_lines(self.first_addr, self.second_addr, isglobal)
        elif c == 'e' or c == 'E':
            if c == 'e' and self.modified and prev_status != EMOD:
                return EMOD
            self.unexpected_address(addr_cnt)
            self.unexpected_command_suffix(cur)
            fn = self.get_filename(cur)
            if self.lines:
                self.cut = [l.t for l in self.lines]
                self.lines = []
                self.cur = 0
                self.modified = True
            self.reset_undo()
            if fn:
                self.def_filename = fn
            self.read_file(fn if fn else self.def_filename, 0)
            self.reset_undo()
            self.modified = False
        elif c == 'f':
            self.unexpected_address(addr_cnt)
            self.unexpected_command_suffix(cur)
            fn = self.get_filename(cur)
            if fn:
                self.def_filename = fn
            self.put(self.def_filename + '\n')
        elif c in ('g', 'v', 'G', 'V') and c != '':
            if isglobal:
                raise EdError('Cannot nest global commands')
            self.check_addr_range(1, self.last(), addr_cnt)
            self.build_active_list(cur, c in ('g', 'G'))
            interactive = c in ('G', 'V')
            gflags = 0
            if interactive:
                gflags = self.get_command_suffix(cur)
            self.exec_global(cur, gflags, interactive)
        elif c == 'i':
            pflags = self.get_command_suffix(cur)
            if not isglobal:
                self.clear_undo()
            self.append_lines(cur, self.second_addr, True, isglobal)
        elif c == 'j':
            self.check_addr_range(self.cur, self.cur + 1, addr_cnt)
            pflags = self.get_command_suffix(cur)
            if not isglobal:
                self.clear_undo()
            if self.first_addr != self.second_addr:
                self.join_lines(self.first_addr, self.second_addr, isglobal)
        elif c == 'k':
            mc = cur.getc()
            if self.second_addr == 0:
                self.invalid_address()
            pflags = self.get_command_suffix(cur)
            if not ('a' <= mc <= 'z') or len(mc) != 1:
                raise EdError('Invalid mark character')
            self.marks[mc] = self.lines[self.second_addr - 1]
        elif c in ('l', 'n', 'p') and c != '':
            own = {'l': PF_L, 'n': PF_N, 'p': PF_P}[c]
            self.check_addr_range2(addr_cnt)
            pflags = self.get_command_suffix(cur)
            self.print_lines(self.first_addr, self.second_addr, pflags | own)
            pflags = 0
        elif c == 'm':
            self.check_addr_range2(addr_cnt)
            addr = self.get_third_addr(cur)
            fa, sa = self.first_addr, self.second_addr
            if fa <= addr < sa:
                raise EdError('Invalid destination')
            pflags = self.get_command_suffix(cur)
            if not isglobal:
                self.clear_undo()
            self.move_lines(fa, sa, addr, isglobal)
        elif c == 'P':
            self.unexpected_address(addr_cnt)
            pflags = self.get_command_suffix(cur)
            self.prompt_on = not self.prompt_on
        elif c == 'q' or c == 'Q':
            self.unexpected_address(addr_cnt)
            self.get_command_suffix(cur)
            if c == 'q' and self.modified and prev_status != EMOD:
                return EMOD
            return QUIT
        elif c == 'r':
            self.unexpected_command_suffix(cur)
            if addr_cnt == 0:
                self.second_addr = self.last()
            fn = self.get_filename(cur)
            if not isglobal:
                self.clear_undo()
            if not self.def_filename and fn:
                self.def_filename = fn
            n = self.read_file(fn if fn else self.def_filename,
                               self.second_addr)
            if n > 0:
                self.modified = True
        elif c == 's':
            pflags = self.command_s(cur, addr_cnt, isglobal)
        elif c == 't':
            self.check_addr_range2(addr_cnt)
            addr = self.get_third_addr(cur)
            pflags = self.get_command_suffix(cur)
            if not isglobal:
                self.clear_undo()
            self.copy_lines(self.first_addr, self.second_addr, addr)
        elif c == 'u':
            self.unexpected_address(addr_cnt)
            pflags = self.get_command_suffix(cur)
            self.undo(isglobal)
        elif c == 'w' or c == 'W':
            n = cur.peek()
            if n in ('q', 'Q') and n != '':
                cur.i += 1
            else:
                n = ''
            self.unexpected_command_suffix(cur)
            fn = self.get_filename(cur)
            if addr_cnt == 0 and self.last() == 0:
                self.first_addr = self.second_addr = 0
            else:
                self.check_addr_range(1, self.last(), addr_cnt)
            if not self.def_filename and fn:
                self.def_filename = fn
            fa, sa = self.first_addr, self.second_addr
            self.write_file(fn if fn else self.def_filename,
                            'ab' if c == 'W' else 'wb', fa, sa)
            if (fa <= 1 and sa == self.last()):
                self.modified = False
            elif n == 'q' and self.modified and prev_status != EMOD:
                return EMOD
            if n in ('q', 'Q') and n != '':
                return QUIT
        elif c == 'x':
            if self.second_addr < 0 or self.second_addr > self.last():
                self.invalid_address()
            pflags = self.get_command_suffix(cur)
            if not isglobal:
                self.clear_undo()
            self.put_lines(self.second_addr)
        elif c == 'y':
            self.check_addr_range2(addr_cnt)
            pflags = self.get_command_suffix(cur)
            self.cut = [l.t for l in
                        self.lines[self.first_addr - 1:self.second_addr]]
        elif c == 'z':
            self.check_second_addr(self.cur + (0 if isglobal else 1), addr_cnt)
            if is_digit(cur.peek()):
                n = self.parse_int(cur)
                if n <= 0:
                    raise EdError('Invalid window size')
                self.window_lines = n
            pflags = self.get_command_suffix(cur)
            sa = self.second_addr
            self.print_lines(sa, min(self.last(), sa + self.window_lines - 1),
                             pflags)
            pflags = 0
        elif c == '=':
            pflags = self.get_command_suffix(cur)
            self.put('%d\n' % (self.second_addr if addr_cnt else self.last()))
        elif c == '#':
            j = cur.s.find('\n', cur.i)
            cur.i = len(cur.s) if j < 0 else j + 1
            return 0
        elif c == '\n':
            self.check_second_addr(self.cur + (0 if isglobal else 1), addr_cnt)
            self.print_lines(self.second_addr, self.second_addr, 0)
        else:
            raise EdError('Unknown command')
        if pflags:
            self.print_lines(self.cur, self.cur, pflags)
        return 0

    # -- main loop -----------------------------------------------------------------
    def main_loop(self):
        status = 0
        err_status = 0
        while True:
            if self.prompt_on:
                self.put(self.prompt)
            line = self.inp.get_line()
            if line is None:
                if not self.modified or status == EMOD:
                    status = QUIT
                else:
                    status = EMOD
            else:
                try:
                    status = self.exec_command(Cursor(line), status, False)
                except EdError as e:
                    self.diag(str(e))
                    status = ERR
                except (RecursionError, MemoryError, IndexError, ValueError):
                    status = ERR
            if status == 0:
                continue
            if status == QUIT:
                return err_status
            self.put('?\n')
            if status == EMOD:
                self.diag('Warning: buffer modified')
            if not self.loose and err_status == 0:
                err_status = 1
            if self.stdin_regular:
                return err_status


def run(argv):
    opts = {'E': False, 'l': False, 'q': False, 'r': False, 's': False,
            'p': None, 'regular': False}
    i = 0
    fname = None
    while i < len(argv):
        a = argv[i]
        if a == '-p':
            if i + 1 >= len(argv):
                sys.stderr.write('ed: option requires an argument -- p\n')
                return 1
            opts['p'] = argv[i + 1]
            i += 2
            continue
        if a.startswith('--prompt='):
            opts['p'] = a[len('--prompt='):]
        elif a in ('-E', '--extended-regexp'):
            opts['E'] = True
        elif a in ('-l', '--loose-exit-status'):
            opts['l'] = True
        elif a in ('-q', '--quiet', '--silent'):
            opts['q'] = True
        elif a in ('-r', '--restricted'):
            opts['r'] = True
        elif a in ('-s', '--script'):
            opts['s'] = True
        elif a == '--':
            if i + 1 < len(argv):
                fname = argv[i + 1]
            break
        elif a.startswith('-') and len(a) > 1:
            # combined short options such as -sE
            ok = True
            for ch in a[1:]:
                if ch in 'Elqrs':
                    opts[ch] = True
                else:
                    ok = False
            if not ok:
                sys.stderr.write('ed: invalid option -- %s\n' % a)
                return 1
        else:
            fname = a
            break
        i += 1
    try:
        opts['regular'] = stat.S_ISREG(os.fstat(0).st_mode)
    except OSError:
        opts['regular'] = False
    try:
        data = sys.stdin.buffer.read()
    except (OSError, ValueError):
        data = b''
    ed = Ed(Input(data.decode('latin-1')), opts)
    if fname is not None:
        try:
            ed.may_access_filename(fname)
        except EdError as e:
            ed.diag(str(e))
            ed.flush()
            return 1
        try:
            ed.read_file(fname, 0)
        except EdError:
            if opts['regular']:
                ed.flush()
                return 2
        ed.def_filename = fname
        ed.reset_undo()
        ed.modified = False
    try:
        rc = ed.main_loop()
    finally:
        ed.flush()
    return rc


def main(argv):
    result = [1]

    def target():
        result[0] = run(argv)

    try:
        threading.stack_size(256 * 1024 * 1024)
        sys.setrecursionlimit(100000)
        t = threading.Thread(target=target)
        t.start()
        t.join()
    except (RuntimeError, ValueError, MemoryError):
        sys.setrecursionlimit(10000)
        target()
    return result[0]


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
