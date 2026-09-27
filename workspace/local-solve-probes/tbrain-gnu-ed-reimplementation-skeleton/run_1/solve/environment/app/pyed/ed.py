"""pyed: a GNU ed 1.19 replacement in pure Python.

Usage: python3 /app/pyed/ed.py [OPTIONS] [FILE]
"""

import string

INF = None


class RegexError(Exception):
    pass


E_BADRPT = "Invalid preceding regular expression"
E_EPAREN = "Unmatched ( or \\("
E_ERPAREN = "Unmatched ) or \\)"
E_EBRACE = "Unmatched \\{"
E_BADBR = "Invalid content of \\{\\}"
E_EBRACK = "Unmatched [, [^, [:, [., or [="
E_ERANGE = "Invalid range end"
E_ECTYPE = "Invalid character class name"
E_ECOLLATE = "Invalid collation character"
E_EESCAPE = "Trailing backslash"
E_ESUBREG = "Invalid back reference"
E_ESIZE = "Regular expression too big"

WORDCH = frozenset(string.ascii_letters + string.digits + "_")
_ALL = [chr(i) for i in range(256)]
CLASSES = {
    "alpha": frozenset(string.ascii_letters),
    "upper": frozenset(string.ascii_uppercase),
    "lower": frozenset(string.ascii_lowercase),
    "digit": frozenset(string.digits),
    "xdigit": frozenset(string.hexdigits),
    "alnum": frozenset(string.ascii_letters + string.digits),
    "space": frozenset(" \t\n\r\f\v"),
    "blank": frozenset(" \t"),
    "punct": frozenset(string.punctuation),
    "print": frozenset(chr(i) for i in range(32, 127)),
    "graph": frozenset(chr(i) for i in range(33, 127)),
    "cntrl": frozenset([chr(i) for i in range(32)] + [chr(127)]),
}


def isword(c):
    return c in WORDCH


class Node(object):
    __slots__ = ("t", "pred", "kind", "idx", "body", "items", "lo", "hi", "n")

    def __init__(self, t, **kw):
        self.t = t
        self.pred = kw.get("pred")
        self.kind = kw.get("kind")
        self.idx = kw.get("idx")
        self.body = kw.get("body")
        self.items = kw.get("items")
        self.lo = kw.get("lo")
        self.hi = kw.get("hi")
        self.n = kw.get("n")


def EMPTY():
    return Node("empty")


class Parser(object):
    def __init__(self, pat, ere, icase):
        self.p = pat
        self.i = 0
        self.ere = ere
        self.icase = icase
        self.ngroups = 0
        self.completed = set()
        self.has_bref = False
        self.tok = None

    # ---- character predicates
    def lit(self, c):
        if self.icase and c.lower() != c.upper():
            s = frozenset((c.lower(), c.upper()))
            return Node("char", pred=s.__contains__)
        return Node("char", pred=(lambda x, c=c: x == c))

    def setnode(self, chars, neg):
        if self.icase:
            ext = set(chars)
            for ch in chars:
                ext.add(ch.lower())
                ext.add(ch.upper())
            chars = ext
        chars = frozenset(chars)
        if neg:
            return Node("char", pred=(lambda x, s=chars: x not in s))
        return Node("char", pred=chars.__contains__)

    # ---- tokenizer
    def fetch(self, caret_here=False):
        p = self.p
        if self.i >= len(p):
            self.tok = ("end",)
            return
        c = p[self.i]
        if c == "\\":
            if self.i + 1 >= len(p):
                raise RegexError(E_EESCAPE)
            d = p[self.i + 1]
            self.i += 2
            if not self.ere:
                m = {"(": "open", ")": "close", "|": "alt", "{": "odup",
                     "}": "cdup", "+": "plus", "?": "qm"}
                if d in m:
                    self.tok = (m[d],)
                    return
            if d in "123456789":
                self.tok = ("bref", int(d))
            elif d == "<":
                self.tok = ("anchor", "wbeg")
            elif d == ">":
                self.tok = ("anchor", "wend")
            elif d == "b":
                self.tok = ("anchor", "wordb")
            elif d == "B":
                self.tok = ("anchor", "nwordb")
            elif d == "`":
                self.tok = ("anchor", "bufbeg")
            elif d == "'":
                self.tok = ("anchor", "bufend")
            elif d == "w":
                self.tok = ("node", self.setnode(WORDCH, False))
            elif d == "W":
                self.tok = ("node", self.setnode(WORDCH, True))
            elif d == "s":
                self.tok = ("node", self.setnode(CLASSES["space"], False))
            elif d == "S":
                self.tok = ("node", self.setnode(CLASSES["space"], True))
            else:
                self.tok = ("node", self.lit(d))
            return
        start = self.i
        self.i += 1
        if self.ere:
            m = {"(": "open", ")": "close", "|": "alt", "{": "odup",
                 "}": "cdup", "*": "star", "+": "plus", "?": "qm"}
            if c in m:
                self.tok = (m[c],)
                return
            if c == "^":
                self.tok = ("anchor", "bol")
                return
            if c == "$":
                self.tok = ("anchor", "eol")
                return
        else:
            if c == "*":
                self.tok = ("star",)
                return
            if c == "^":
                if start == 0 or caret_here:
                    self.tok = ("anchor", "bol")
                else:
                    self.tok = ("node", self.lit(c))
                return
            if c == "$":
                if (self.i == len(p) or p.startswith("\\)", self.i)
                        or p.startswith("\\|", self.i)):
                    self.tok = ("anchor", "eol")
                else:
                    self.tok = ("node", self.lit(c))
                return
        if c == ".":
            self.tok = ("node", Node("char", pred=(lambda x: True)))
            return
        if c == "[":
            self.tok = ("node", self.parse_bracket())
            return
        self.tok = ("node", self.lit(c))

    def bracket_elem(self, i):
        p = self.p
        if i >= len(p):
            raise RegexError(E_EBRACK)
        if p[i] == "[" and i + 1 < len(p) and p[i + 1] in ":.=":
            d = p[i + 1]
            j = p.find(d + "]", i + 2)
            if j < 0:
                raise RegexError(E_EBRACK)
            name = p[i + 2:j]
            ni = j + 2
            if d == ":":
                if self.icase and name in ("upper", "lower"):
                    name = "alpha"
                if name not in CLASSES:
                    raise RegexError(E_ECTYPE)
                return ("class", CLASSES[name], ni)
            if len(name) != 1:
                raise RegexError(E_ECOLLATE)
            return ("char", name, ni)
        return ("char", p[i], i + 1)

    def parse_bracket(self):
        p = self.p
        i = self.i
        neg = False
        chars = set()
        if i < len(p) and p[i] == "^":
            neg = True
            i += 1
        first = True
        while True:
            if i >= len(p):
                raise RegexError(E_EBRACK)
            if p[i] == "]" and not first:
                i += 1
                break
            first = False
            kind, val, i = self.bracket_elem(i)
            if kind == "class":
                chars |= val
                continue
            if i + 1 < len(p) and p[i] == "-" and p[i + 1] != "]":
                kind2, val2, i = self.bracket_elem(i + 1)
                if kind2 == "class":
                    raise RegexError(E_ERANGE)
                lo, hi = ord(val), ord(val2)
                if self.icase:
                    lo, hi = ord(val.lower()), ord(val2.lower())
                if lo > hi:
                    raise RegexError(E_ERANGE)
                for o in range(lo, hi + 1):
                    chars.add(chr(o))
            else:
                chars.add(val)
        self.i = i
        return self.setnode(chars, neg)

    # ---- grammar
    def parse(self):
        self.fetch(True)
        tree = self.parse_reg_exp(0)
        if self.tok[0] != "end":
            raise RegexError(E_ERPAREN)
        return tree if tree is not None else EMPTY()

    def stop_branch(self, nest):
        t = self.tok[0]
        return t == "alt" or t == "end" or (nest and t == "close")

    def parse_reg_exp(self, nest):
        initial = set(self.completed)
        tree = None
        if not self.stop_branch(nest):
            tree = self.parse_branch(nest)
        alts = [tree]
        while self.tok[0] == "alt":
            self.fetch(True)
            if not self.stop_branch(nest):
                acc = set(self.completed)
                self.completed = set(initial)
                b = self.parse_branch(nest)
                self.completed |= acc
            else:
                b = None
            alts.append(b)
        if len(alts) == 1:
            return tree
        return Node("alt", items=[a if a is not None else EMPTY() for a in alts])

    def parse_branch(self, nest):
        items = []
        while not self.stop_branch(nest):
            e = self.parse_expression(nest)
            if e is not None:
                items.append(e)
        if not items:
            return None
        if len(items) == 1:
            return items[0]
        return Node("cat", items=items)

    def parse_expression(self, nest):
        t = self.tok
        k = t[0]
        if k == "node":
            node = t[1]
        elif k == "open":
            node = self.parse_sub_exp(nest + 1)
        elif k == "bref":
            if t[1] not in self.completed:
                raise RegexError(E_ESUBREG)
            self.has_bref = True
            node = Node("bref", n=t[1])
        elif k == "odup":
            raise RegexError(E_BADRPT)
        elif k in ("star", "plus", "qm"):
            if self.ere:
                raise RegexError(E_BADRPT)
            node = self.lit({"star": "*", "plus": "+", "qm": "?"}[k])
        elif k == "close":
            if self.ere:
                node = self.lit(")")
            else:
                raise RegexError(E_ERPAREN)
        elif k == "cdup":
            node = self.lit("}")
        elif k == "anchor":
            node = Node("assert", kind=t[1])
            self.fetch()
            return node
        else:
            return None
        self.fetch()
        while self.tok[0] in ("star", "plus", "qm", "odup"):
            node = self.parse_dup(node)
            if not self.ere and self.tok[0] in ("star", "odup"):
                raise RegexError(E_BADRPT)
        return node

    def parse_sub_exp(self, nest):
        self.ngroups += 1
        idx = self.ngroups
        self.fetch(True)
        if self.tok[0] == "close":
            body = EMPTY()
        else:
            body = self.parse_reg_exp(nest)
            if self.tok[0] != "close":
                raise RegexError(E_EPAREN)
            if body is None:
                body = EMPTY()
        self.completed.add(idx)
        return Node("group", idx=idx, body=body)

    def parse_interval(self):
        p = self.p
        i = self.i

        def num(i):
            st = i
            while i < len(p) and "0" <= p[i] <= "9":
                i += 1
            return (int(p[st:i]) if i > st else None), i

        m, i = num(i)
        if i >= len(p):
            raise RegexError(E_EBRACE)
        if p[i] == ",":
            n, i = num(i + 1)
            if m is None:
                m = 0
        else:
            if m is None:
                raise RegexError(E_BADBR)
            n = m
        close = "}" if self.ere else "\\}"
        if p.startswith(close, i):
            i += len(close)
        else:
            if i >= len(p) or (not self.ere and p[i] == "\\" and i + 1 >= len(p)):
                raise RegexError(E_EBRACE)
            raise RegexError(E_BADBR)
        if n is not None and m > n:
            raise RegexError(E_BADBR)
        if (n if n is not None else m) > 32767:
            raise RegexError(E_ESIZE)
        self.i = i
        return m, n

    def parse_dup(self, node):
        k = self.tok[0]
        if k == "star":
            lo, hi = 0, INF
        elif k == "plus":
            lo, hi = 1, INF
        elif k == "qm":
            lo, hi = 0, 1
        else:
            lo, hi = self.parse_interval()
        self.fetch()
        if node is None:
            return None
        if lo == 0 and hi == 0:
            return EMPTY()
        return Node("rep", body=node, lo=lo, hi=hi)


class Regex(object):
    def __init__(self, pattern, extended=False, icase=False):
        pr = Parser(pattern, extended, icase)
        self.root = pr.parse()
        self.ngroups = pr.ngroups
        self.has_bref = pr.has_bref
        self.icase = icase

    # ------------------------------------------------------------------
    def search(self, text, notbol=False):
        """Return (start, end, caps) of the leftmost-longest match or None.
        caps is a list indexed by group number of (s, e) or None."""
        m = _Matcher(self, text, notbol)
        return m.search()


class _Matcher(object):
    def __init__(self, rx, text, notbol):
        self.rx = rx
        self.text = text
        self.L = len(text)
        self.notbol = notbol
        self.memo = {}

    def check(self, kind, pos):
        text = self.text
        L = self.L
        if kind == "bol":
            return pos == 0 and not self.notbol
        if kind == "eol":
            return pos == L
        if kind == "bufbeg":
            return pos == 0
        if kind == "bufend":
            return pos == L
        pw = pos > 0 and isword(text[pos - 1])
        nw = pos < L and isword(text[pos])
        if kind == "wbeg":
            return nw and not pw
        if kind == "wend":
            return pw and not nw
        if kind == "wordb":
            return pw != nw
        if kind == "nwordb":
            return pw == nw
        return False

    # ---------------- ends (no backrefs)
    def ends(self, n, pos):
        key = (id(n), pos)
        r = self.memo.get(key)
        if r is not None:
            return r
        t = n.t
        if t == "char":
            r = frozenset((pos + 1,)) if pos < self.L and n.pred(self.text[pos]) else frozenset()
        elif t == "assert":
            r = frozenset((pos,)) if self.check(n.kind, pos) else frozenset()
        elif t == "empty":
            r = frozenset((pos,))
        elif t == "group":
            r = self.ends(n.body, pos)
        elif t == "cat":
            r = self.seq_ends(n, 0, pos)
        elif t == "alt":
            s = set()
            for a in n.items:
                s |= self.ends(a, pos)
            r = frozenset(s)
        elif t == "rep":
            r = self.rep_ends(n.body, pos, n.lo, n.hi)
        else:
            r = frozenset()
        self.memo[key] = r
        return r

    def seq_ends(self, n, k, pos):
        key = ("s", id(n), k, pos)
        r = self.memo.get(key)
        if r is not None:
            return r
        items = n.items
        if k == len(items):
            r = frozenset((pos,))
        else:
            s = set()
            for e in self.ends(items[k], pos):
                s |= self.seq_ends(n, k + 1, e)
            r = frozenset(s)
        self.memo[key] = r
        return r

    def step(self, body, S):
        out = set()
        for p in S:
            out |= self.ends(body, p)
        return out

    def rep_ends(self, body, pos, lo, hi):
        key = ("r", id(body), pos, lo, hi)
        r = self.memo.get(key)
        if r is not None:
            return r
        cur = {pos}
        ok = True
        for _ in range(lo):
            cur = self.step(body, cur)
            if not cur:
                ok = False
                break
        if not ok:
            r = frozenset()
        else:
            result = set(cur)
            frontier = set(cur)
            k = lo
            while frontier and (hi is None or k < hi):
                nxt = self.step(body, frontier)
                frontier = nxt - result
                result |= nxt
                k += 1
            r = frozenset(result)
        self.memo[key] = r
        return r

    def exact(self, n, pos, end, caps):
        t = n.t
        if t == "group":
            self.exact(n.body, pos, end, caps)
            caps[n.idx] = (pos, end)
        elif t == "alt":
            for a in n.items:
                if end in self.ends(a, pos):
                    self.exact(a, pos, end, caps)
                    return
        elif t == "cat":
            items = n.items
            k = 0
            while k < len(items):
                it = items[k]
                if k == len(items) - 1:
                    self.exact(it, pos, end, caps)
                    break
                for e in sorted(self.ends(it, pos), reverse=True):
                    if e <= end and end in self.seq_ends(n, k + 1, e):
                        self.exact(it, pos, e, caps)
                        pos = e
                        break
                k += 1
        elif t == "rep":
            self.exact_rep(n.body, n.lo, n.hi, pos, end, caps)

    def exact_rep(self, body, lo, hi, pos, end, caps):
        while True:
            if pos == end:
                if lo > 0:
                    self.exact(body, pos, pos, caps)
                return
            nlo = lo - 1 if lo > 0 else 0
            nhi = None if hi is None else hi - 1
            found = False
            for e in sorted(self.ends(body, pos), reverse=True):
                if e == pos or e > end:
                    continue
                if nhi is not None and nhi < 0:
                    continue
                if end in self.rep_ends(body, e, nlo, nhi):
                    self.exact(body, pos, e, caps)
                    pos, lo, hi = e, nlo, nhi
                    found = True
                    break
            if not found:
                return

    # ---------------- backtracking (with backrefs)
    def bt(self, n, pos, caps, k):
        t = n.t
        if t == "char":
            return pos < self.L and n.pred(self.text[pos]) and k(pos + 1, caps)
        if t == "assert":
            return self.check(n.kind, pos) and k(pos, caps)
        if t == "empty":
            return k(pos, caps)
        if t == "group":
            idx = n.idx

            def kg(p, c, pos=pos):
                c2 = list(c)
                c2[idx] = (pos, p)
                return k(p, tuple(c2))
            return self.bt(n.body, pos, caps, kg)
        if t == "cat":
            return self.bt_seq(n.items, 0, pos, caps, k)
        if t == "alt":
            for a in n.items:
                if self.bt(a, pos, caps, k):
                    return True
            return False
        if t == "rep":
            return self.bt_rep(n, 0, pos, caps, k)
        if t == "bref":
            cap = caps[n.n]
            if cap is None:
                return False
            sub = self.text[cap[0]:cap[1]]
            seg = self.text[pos:pos + len(sub)]
            if len(seg) != len(sub):
                return False
            if self.rx.icase:
                if seg.lower() != sub.lower():
                    return False
            elif seg != sub:
                return False
            return k(pos + len(sub), caps)
        return False

    def bt_seq(self, items, i, pos, caps, k):
        if i == len(items):
            return k(pos, caps)
        return self.bt(items[i], pos, caps,
                       lambda p, c: self.bt_seq(items, i + 1, p, c, k))

    def bt_rep(self, n, count, pos, caps, k):
        if n.hi is None or count < n.hi:
            def k2(p, c):
                if p == pos and count >= n.lo:
                    return False
                return self.bt_rep(n, count + 1, p, c, k)
            if self.bt(n.body, pos, caps, k2):
                return True
        if count >= n.lo:
            return k(pos, caps)
        return False

    # ---------------- driver
    def search(self):
        rx = self.rx
        root = rx.root
        ng = rx.ngroups
        for st in range(self.L + 1):
            if rx.has_bref:
                best = [None]
                L = self.L

                def fin(p, c):
                    if best[0] is None or p > best[0][0]:
                        best[0] = (p, c)
                    return p == L
                self.bt(root, st, tuple([None] * (ng + 1)), fin)
                if best[0] is not None:
                    e, c = best[0]
                    caps = list(c)
                    caps[0] = (st, e)
                    return st, e, caps
            else:
                E = self.ends(root, st)
                if E:
                    e = max(E)
                    caps = [None] * (ng + 1)
                    self.exact(root, st, e, caps)
                    caps[0] = (st, e)
                    return st, e, caps
        return None

# ======================================================================
# The editor
# ======================================================================

import os
import stat
import sys

QUIT = -1
ERR = -2
EMOD = -3

PF_L = 1
PF_N = 2
PF_P = 4

ESCAPES = {"\a": "a", "\b": "b", "\f": "f", "\n": "n", "\r": "r",
           "\t": "t", "\v": "v"}


class EdError(Exception):
    pass


class Line(object):
    __slots__ = ("text",)

    def __init__(self, text):
        self.text = text


class Cursor(object):
    __slots__ = ("s", "i")

    def __init__(self, s):
        self.s = s
        self.i = 0

    def peek(self, k=0):
        j = self.i + k
        return self.s[j] if j < len(self.s) else ""

    def getc(self):
        c = self.peek()
        self.i += 1
        return c

    def skip_blanks(self):
        while self.peek() in (" ", "\t") and self.peek() != "":
            self.i += 1


def isdig(c):
    return c != "" and "0" <= c <= "9"


def isspace(c):
    return c != "" and c in " \t\n\r\f\v"


def trailing_escape(s):
    # s ends with '\n'; odd number of backslashes before it?
    j = len(s) - 2
    n = 0
    while j >= 0 and s[j] == "\\":
        n += 1
        j -= 1
    return n % 2 == 1


def strip_escapes(s):
    out = []
    i = 0
    while i < len(s):
        if s[i] == "\\" and i + 1 < len(s):
            i += 1
        out.append(s[i])
        i += 1
    return "".join(out)


def stdin_is_regular():
    try:
        st = os.fstat(0)
    except OSError:
        return True
    return stat.S_ISREG(st.st_mode)


class Ed(object):
    def __init__(self):
        self.lines = []
        self.cur = 0
        self.modified = False
        self.def_filename = ""
        self.marks = {}
        self.cut = []
        self.undo_snap = None
        self.undo_changed = False
        self.last_regex = None
        self.subst_regex = None
        self.subst_repl = None
        self.s_global = False
        self.s_count = 1
        self.s_pflags = 0
        self.extended = False
        self.traditional = False
        self.loose = False
        self.prompt = "*"
        self.prompt_on = False
        self.quiet = False
        self.restricted = False
        self.scripted = False
        self.verbose = False
        self.errmsg = ""
        self.active_cleared = False
        self.window_lines = 22
        self.window_columns = 72
        self.out = sys.stdout.buffer
        self.inp = sys.stdin.buffer
        self.linenum = 0

    # ---------------------------------------------------------------- io
    def write(self, s):
        self.out.write(s.encode("latin-1"))

    def diag(self, s):
        if not self.quiet:
            try:
                sys.stdout.flush()
                self.out.flush()
                sys.stderr.write(s + "\n")
                sys.stderr.flush()
            except Exception:
                pass

    def read_line(self):
        try:
            self.out.flush()
        except Exception:
            pass
        b = self.inp.readline()
        if not b:
            return None
        self.linenum += 1
        s = b.decode("latin-1")
        if not s.endswith("\n"):
            s += "\n"
        return s

    # ------------------------------------------------------------ buffer
    @property
    def last(self):
        return len(self.lines)

    def touch(self):
        self.modified = True
        self.undo_changed = True

    def clear_undo(self):
        self.undo_snap = (list(self.lines), self.cur, self.modified)
        self.undo_changed = False

    def addr_of(self, ln):
        for i, l in enumerate(self.lines):
            if l is ln:
                return i + 1
        return -1

    def unmark(self, removed):
        ids = set(id(l) for l in removed)
        if self.marks:
            self.marks = dict((k, v) for k, v in self.marks.items()
                              if id(v) not in ids)

    def delete_lines(self, f, s):
        removed = self.lines[f - 1:s]
        self.cut = [l.text for l in removed]
        del self.lines[f - 1:s]
        self.unmark(removed)
        self.cur = f if f <= self.last else self.last
        if removed:
            self.touch()

    def insert_texts(self, addr, texts):
        self.lines[addr:addr] = [Line(t) for t in texts]
        self.cur = addr + len(texts)
        if texts:
            self.touch()

    # ------------------------------------------------------------- print
    def print_line(self, text, pflags, addr):
        out = []
        col = 0
        if pflags & PF_N:
            out.append("%d\t" % addr)
            col = 8
        if not (pflags & PF_L):
            out.append(text)
        else:
            for ch in text:
                if not self.traditional:
                    col += 1
                    if col > self.window_columns:
                        out.append("\\\n")
                        col = 1
                o = ord(ch)
                if ch == "\\":
                    out.append("\\\\")
                    col += 1
                elif ch in ESCAPES:
                    out.append("\\" + ESCAPES[ch])
                    col += 1
                elif o < 32 or o >= 127:
                    out.append("\\%03o" % o)
                    col += 3
                elif ch == "$":
                    out.append("\\$")
                    col += 1
                else:
                    out.append(ch)
            out.append("$")
        out.append("\n")
        self.write("".join(out))

    def print_lines(self, f, t, pflags):
        if f < 1 or t > self.last:
            raise EdError("Invalid address")
        for a in range(f, t + 1):
            self.cur = a
            self.print_line(self.lines[a - 1].text, pflags, a)

    # --------------------------------------------------------- addresses
    def parse_int(self, C):
        st = C.i
        while isdig(C.peek()):
            C.i += 1
        return int(C.s[st:C.i])

    def extract_addresses(self, C):
        first = True
        faddr = saddr = -1
        while True:
            ch = C.peek()
            if isdig(ch):
                n = self.parse_int(C)
                if first:
                    first = False
                    saddr = n
                else:
                    saddr += n
            elif ch == " " or ch == "\t":
                C.skip_blanks()
            elif ch == "+" or ch == "-":
                if first:
                    first = False
                    saddr = self.cur
                C.i += 1
                if isdig(C.peek()):
                    n = self.parse_int(C)
                    saddr += -n if ch == "-" else n
                else:
                    saddr += 1 if ch == "+" else -1
            elif ch == "." or ch == "$":
                if not first:
                    raise EdError("Invalid address")
                first = False
                C.i += 1
                saddr = self.cur if ch == "." else self.last
            elif ch == "/" or ch == "?":
                if not first:
                    raise EdError("Invalid address")
                saddr = self.next_matching(C)
                first = False
            elif ch == "'":
                if not first:
                    raise EdError("Invalid address")
                first = False
                C.i += 1
                saddr = self.marked_addr(C.getc())
            elif ch in ("%", ",", ";"):
                if first:
                    if faddr < 0:
                        faddr = self.cur if ch == ";" else 1
                        saddr = self.last
                    else:
                        faddr = saddr
                else:
                    if saddr < 0 or saddr > self.last:
                        raise EdError("Invalid address")
                    if ch == ";":
                        self.cur = saddr
                    faddr = saddr
                    first = True
                C.i += 1
            else:
                if not first and (saddr < 0 or saddr > self.last):
                    raise EdError("Invalid address")
                cnt = 0
                if saddr >= 0:
                    cnt = 2 if faddr >= 0 else 1
                if cnt <= 0:
                    saddr = self.cur
                if cnt <= 1:
                    faddr = saddr
                return cnt, faddr, saddr

    def marked_addr(self, c):
        if c == "" or not ("a" <= c <= "z"):
            raise EdError("Invalid mark character")
        ln = self.marks.get(c)
        if ln is None:
            raise EdError("Invalid address")
        a = self.addr_of(ln)
        if a < 0:
            raise EdError("Invalid address")
        return a

    def check_range(self, n, m, cnt, f, s):
        if cnt == 0:
            f, s = n, m
        if f < 1 or f > s or s > self.last:
            raise EdError("Invalid address")
        return f, s

    # ----------------------------------------------------------- regexes
    def parse_pattern(self, C, delim):
        ch = C.peek()
        if ch == "\n" or ch == delim or ch == "":
            return None
        st = C.i
        while True:
            ch = C.peek()
            if ch == delim or ch == "\n" or ch == "":
                break
            if ch == "[":
                j = self.parse_char_class(C.s, C.i + 1)
                if j < 0:
                    raise EdError("Unbalanced brackets ([])")
                C.i = j + 1
            elif ch == "\\":
                C.i += 1
                if C.peek() in ("\n", ""):
                    raise EdError("Trailing backslash (\\)")
                C.i += 1
            else:
                C.i += 1
        return C.s[st:C.i]

    @staticmethod
    def parse_char_class(s, p):
        n = len(s)

        def at(k):
            return s[k] if k < n else ""
        if at(p) == "^":
            p += 1
        if at(p) == "]":
            p += 1
        while at(p) != "]" and at(p) != "\n" and at(p) != "":
            if at(p) == "[" and at(p + 1) in (".", ":", "="):
                d = at(p + 1)
                p += 2
                c = at(p)
                while not (at(p) == "]" and c == d):
                    c = at(p)
                    if c == "\n" or c == "":
                        return -1
                    p += 1
            p += 1
        return p if at(p) == "]" else -1

    def compile(self, pat, icase):
        if pat is None:
            if self.last_regex is None:
                raise EdError("No previous regular expression")
            if icase:
                raise EdError("Invalid pattern delimiter")
            return self.last_regex
        try:
            r = Regex(pat, self.extended, icase)
        except RegexError as e:
            raise EdError(str(e))
        self.last_regex = r
        return r

    def get_regex(self, C, delim):
        pat = self.parse_pattern(C, delim)
        if C.peek() == delim:
            C.i += 1
        icase = False
        if C.peek() == "I":
            icase = True
            C.i += 1
        return self.compile(pat, icase)

    def next_matching(self, C):
        delim = C.getc()
        forward = delim == "/"
        rx = self.get_regex(C, delim)
        addr = self.cur
        while True:
            if forward:
                addr += 1
                if addr > self.last:
                    addr = 0
            else:
                addr -= 1
                if addr < 0:
                    addr = self.last
            if addr and rx.search(self.lines[addr - 1].text) is not None:
                return addr
            if addr == self.cur:
                raise EdError("No match")

    # -------------------------------------------------------- misc parse
    def get_command_suffix(self, C):
        pflags = 0
        while True:
            ch = C.peek()
            if ch == "l":
                if pflags & PF_L:
                    break
                pflags |= PF_L
            elif ch == "n":
                if pflags & PF_N:
                    break
                pflags |= PF_N
            elif ch == "p":
                if pflags & PF_P:
                    break
                pflags |= PF_P
            else:
                break
            C.i += 1
        if C.getc() != "\n":
            raise EdError("Invalid command suffix")
        return pflags

    def get_extended_line(self, C, strip):
        nl = C.s.find("\n", C.i)
        if nl < 0:
            text = C.s[C.i:] + "\n"
            C.i = len(C.s)
        else:
            text = C.s[C.i:nl + 1]
            C.i = nl + 1
        if len(text) < 2 or not trailing_escape(text):
            return text
        buf = text[:-2] + ("" if strip else "\n")
        while True:
            line = self.read_line()
            if line is None:
                raise EdError("Unexpected end-of-file")
            buf += line
            if len(line) < 2 or not trailing_escape(line):
                break
            buf = buf[:-2] + ("" if strip else "\n")
        return buf

    def may_access(self, name):
        if self.restricted:
            if name.startswith("!"):
                raise EdError("Shell access restricted")
            if name == ".." or "/" in name:
                raise EdError("Directory access restricted")
        return True

    def get_filename(self, C, trad_f=False):
        C.skip_blanks()
        if C.peek() != "\n":
            text = self.get_extended_line(C, True)
            name = text[:-1] if text.endswith("\n") else text
            if name.startswith("!"):
                raise EdError("Shell access restricted" if self.restricted
                              else "Invalid redirection")
        else:
            C.i += 1
            if not trad_f and not self.def_filename:
                raise EdError("No current filename")
            name = ""
        self.may_access(name)
        return name

    def get_third_addr(self, C):
        cnt, f, s = self.extract_addresses(C)
        if self.traditional and cnt == 0:
            raise EdError("Destination expected")
        if s < 0 or s > self.last:
            raise EdError("Invalid address")
        return s

    # -------------------------------------------------------------- files
    def read_file(self, name, addr):
        fname = strip_escapes(name)
        try:
            with open(fname, "rb") as fh:
                data = fh.read()
        except OSError as e:
            self.diag("%s: %s" % (name, e.strerror or "error"))
            raise EdError("Cannot open input file")
        text = data.decode("latin-1")
        if text == "":
            texts = []
        else:
            texts = text.split("\n")
            if text.endswith("\n"):
                texts.pop()
            else:
                self.diag("Newline appended")
        self.lines[addr:addr] = [Line(t) for t in texts]
        self.cur = addr + len(texts)
        if texts:
            self.undo_changed = True
        if not self.scripted:
            self.write("%d\n" % len(data))
        return len(texts)

    def write_file(self, name, mode, f, s):
        fname = strip_escapes(name)
        if f > 0:
            data = "".join(l.text + "\n" for l in self.lines[f - 1:s])
        else:
            data = ""
        raw = data.encode("latin-1")
        try:
            with open(fname, mode) as fh:
                fh.write(raw)
        except OSError as e:
            self.diag("%s: %s" % (name, e.strerror or "error"))
            raise EdError("Cannot open output file")
        if not self.scripted:
            self.write("%d\n" % len(raw))
        return (s - f + 1) if f > 0 else 0

    # --------------------------------------------------------------- text
    def append_lines(self, C, addr, insert, isglobal):
        self.cur = addr
        while True:
            if not isglobal:
                line = self.read_line()
                if line is None:
                    return
            else:
                if C.i >= len(C.s):
                    return
                nl = C.s.find("\n", C.i)
                if nl < 0:
                    line = C.s[C.i:] + "\n"
                    C.i = len(C.s)
                else:
                    line = C.s[C.i:nl + 1]
                    C.i = nl + 1
            if line == ".\n":
                return
            if insert:
                insert = False
                if self.cur > 0:
                    self.cur -= 1
            self.lines.insert(self.cur, Line(line[:-1]))
            self.cur += 1
            self.touch()

    # --------------------------------------------------------------- subst
    def extract_replacement(self, C, delim, isglobal):
        C.i += 1  # skip delimiter
        if C.peek() == "%" and (C.peek(1) == delim or
                                (C.peek(1) == "\n" and
                                 (not isglobal or C.peek(2) == ""))):
            C.i += 1
            if self.subst_repl is None:
                raise EdError("No previous substitution")
            return self.subst_repl
        buf = []
        while C.peek() != delim:
            ch = C.peek()
            if ch == "":
                break
            if ch == "\n" and (not isglobal or C.peek(1) == ""):
                break
            C.i += 1
            buf.append(ch)
            if ch == "\\":
                ch2 = C.getc()
                buf.append(ch2)
                if ch2 == "\n" and not isglobal:
                    line = self.read_line()
                    if line is None:
                        raise EdError("Unexpected end-of-file")
                    C.s = line
                    C.i = 0
        return "".join(buf)

    def expand(self, repl, sub, caps, ngroups):
        res = []
        i = 0
        n = len(repl)
        while i < n:
            c = repl[i]
            if c == "&":
                s, e = caps[0]
                res.append(sub[s:e])
            elif c == "\\" and i + 1 < n:
                i += 1
                d = repl[i]
                if "1" <= d <= "9":
                    k = int(d)
                    if k < len(caps) and caps[k] is not None:
                        s, e = caps[k]
                        res.append(sub[s:e])
                else:
                    res.append(d)
            else:
                res.append(c)
            i += 1
        return "".join(res)

    def replace_text(self, text, rx, gl, count, repl):
        out = []
        pos = 0
        matchno = 0
        changed = False
        notbol = False
        L = len(text)
        while True:
            sub = text[pos:]
            m = rx.search(sub, notbol)
            if m is None:
                break
            ms, me, caps = m
            matchno += 1
            if gl or matchno == count:
                changed = True
                out.append(sub[:ms])
                out.append(self.expand(repl, sub, caps, rx.ngroups))
            else:
                out.append(sub[:me])
            pos += me
            notbol = True
            if pos >= L:
                break
            if changed and not (gl and me > 0):
                break
        if not changed:
            return None
        out.append(text[pos:])
        return "".join(out)

    def search_and_replace(self, f, s, rx, gl, count, repl, isglobal):
        xa = self.cur
        nsubs = 0
        self.cur = f - 1
        for _ in range(s - f + 1):
            self.cur += 1
            ln = self.lines[self.cur - 1]
            new = self.replace_text(ln.text, rx, gl, count, repl)
            if new is not None:
                self.cut = [ln.text]
                pieces = new.split("\n")
                self.lines[self.cur - 1:self.cur] = [Line(p) for p in pieces]
                self.unmark([ln])
                self.cur += len(pieces) - 1
                self.touch()
                nsubs += 1
                xa = self.cur
        self.cur = xa
        if nsubs == 0 and not isglobal:
            raise EdError("No match")

    def cmd_subst(self, C, cnt, f, s, isglobal):
        ch = C.peek()
        if ch in ("\n", "g", "p", "r", "") or isdig(ch):
            # repeat last substitution
            if self.subst_regex is None or self.subst_repl is None:
                raise EdError("No previous substitution")
            use_last = False
            gtoggle = False
            ptoggle = False
            newcount = None
            while C.peek() != "\n":
                ch = C.peek()
                if ch == "g":
                    gtoggle = True
                    C.i += 1
                elif ch == "p":
                    ptoggle = True
                    C.i += 1
                elif ch == "r":
                    use_last = True
                    C.i += 1
                elif isdig(ch):
                    newcount = self.parse_int(C)
                    if newcount <= 0:
                        raise EdError("Invalid command suffix")
                else:
                    raise EdError("Invalid command suffix")
            C.i += 1
            if newcount is not None:
                self.s_count = newcount
                self.s_global = False
            if gtoggle:
                self.s_global = not self.s_global
                self.s_count = 1
            if ptoggle:
                self.s_pflags = (self.s_pflags ^ PF_P) & PF_P
            if use_last:
                if self.last_regex is None:
                    raise EdError("No previous regular expression")
                rx = self.last_regex
            else:
                rx = self.subst_regex
            repl = self.subst_repl
        else:
            delim = C.getc()
            if delim == " ":
                raise EdError("Invalid pattern delimiter")
            pat = self.parse_pattern(C, delim)
            if C.peek() != delim:
                raise EdError("Missing pattern delimiter")
            repl = self.extract_replacement(C, delim, isglobal)
            gl = False
            count = 0
            pflags = 0
            icase = False
            if C.peek() == "\n" or C.peek() == "":
                pflags = PF_P
                C.i += 1
            else:
                C.i += 1  # skip delimiter
                while True:
                    ch = C.peek()
                    if ch != "" and "1" <= ch <= "9":
                        if count or gl:
                            raise EdError("Invalid command suffix")
                        count = self.parse_int(C)
                        continue
                    elif ch == "g":
                        if gl or count:
                            raise EdError("Invalid command suffix")
                        gl = True
                    elif ch == "I" or ch == "i":
                        icase = True
                    elif ch == "p":
                        if pflags & PF_P:
                            break
                        pflags |= PF_P
                    elif ch == "l":
                        if pflags & PF_L:
                            break
                        pflags |= PF_L
                    elif ch == "n":
                        if pflags & PF_N:
                            break
                        pflags |= PF_N
                    else:
                        break
                    C.i += 1
                if C.getc() != "\n":
                    raise EdError("Invalid command suffix")
            rx = self.compile(pat, icase)
            self.subst_regex = rx
            self.subst_repl = repl
            self.s_global = gl
            self.s_count = count if count else 1
            self.s_pflags = pflags
        f, s = self.check_range(self.cur, self.cur, cnt, f, s)
        if not isglobal:
            self.clear_undo()
        self.search_and_replace(f, s, rx, self.s_global, self.s_count,
                                repl, isglobal)
        return self.s_pflags

    # -------------------------------------------------------------- global
    def exec_global(self, C, active, pflags, interactive):
        cmd = None
        if not interactive:
            rest = C.s[C.i:]
            if self.traditional and rest == "\n":
                cmd = "p\n"
                C.i = len(C.s)
            else:
                cmd = self.get_extended_line(C, False)
            C.i = len(C.s)
        self.clear_undo()
        self.active_cleared = False
        for lp in active:
            if self.active_cleared:
                break
            a = self.addr_of(lp)
            if a < 0:
                continue
            self.cur = a
            if interactive:
                self.print_lines(self.cur, self.cur, pflags)
                line = self.read_line()
                if line is None:
                    raise EdError("Unexpected end-of-file")
                if line == "\n":
                    continue
                if line == "&\n":
                    if cmd is None:
                        raise EdError("No previous command")
                else:
                    LC = Cursor(line)
                    cmd = self.get_extended_line(LC, False)
            G = Cursor(cmd)
            while G.i < len(G.s):
                st = self.exec_command(G, 0, True)
                if st != 0:
                    return st
        return 0

    # ------------------------------------------------------------- undo
    def undo(self, isglobal):
        if self.undo_snap is None or not self.undo_changed:
            raise EdError("Nothing to undo")
        snap = (list(self.lines), self.cur, self.modified)
        lines, cur, mod = self.undo_snap
        self.lines = list(lines)
        self.cur = cur
        self.modified = mod
        self.undo_snap = snap
        if isglobal:
            self.active_cleared = True

    # ---------------------------------------------------------- dispatch
    def exec_command(self, C, prev, isglobal):
        try:
            return self._exec(C, prev, isglobal)
        except EdError as e:
            self.errmsg = str(e)
            return ERR

    def _exec(self, C, prev, isglobal):
        pflags = 0
        cnt, f, s = self.extract_addresses(C)
        C.skip_blanks()
        c = C.getc()
        last = self.last
        if c == "a":
            pflags = self.get_command_suffix(C)
            if not isglobal:
                self.clear_undo()
            self.append_lines(C, s, False, isglobal)
        elif c == "c":
            if f == 0:
                f = 1
            if s == 0:
                s = 1
            f, s = self.check_range(self.cur, self.cur, cnt, f, s)
            pflags = self.get_command_suffix(C)
            if not isglobal:
                self.clear_undo()
            self.delete_lines(f, s)
            self.append_lines(C, self.cur, self.cur >= f, isglobal)
        elif c == "d":
            f, s = self.check_range(self.cur, self.cur, cnt, f, s)
            pflags = self.get_command_suffix(C)
            if not isglobal:
                self.clear_undo()
            self.delete_lines(f, s)
        elif c == "e" or c == "E":
            if c == "e" and self.modified and prev != EMOD:
                return EMOD
            if cnt:
                raise EdError("Unexpected address")
            if not isspace(C.peek()):
                raise EdError("Unexpected command suffix")
            fn = self.get_filename(C)
            if self.lines:
                self.delete_lines(1, self.last)
            self.marks = {}
            if fn:
                self.def_filename = fn
            self.undo_snap = None
            self.read_file(fn if fn else self.def_filename, 0)
            self.undo_snap = None
            self.undo_changed = False
            self.modified = False
        elif c == "f":
            if cnt:
                raise EdError("Unexpected address")
            if not isspace(C.peek()):
                raise EdError("Unexpected command suffix")
            fn = self.get_filename(C, self.traditional)
            if fn:
                self.def_filename = fn
            self.write(strip_escapes(self.def_filename) + "\n")
        elif c in ("g", "v", "G", "V"):
            if isglobal:
                raise EdError("Cannot nest global commands")
            f, s = self.check_range(1, last, cnt, f, s)
            delim = C.getc()
            if delim in ("\n", " ", ""):
                raise EdError("Invalid pattern delimiter")
            rx = self.get_regex(C, delim)
            match = c in ("g", "G")
            active = [ln for ln in self.lines[f - 1:s]
                      if (rx.search(ln.text) is not None) == match]
            interactive = c in ("G", "V")
            gp = 0
            if interactive:
                gp = self.get_command_suffix(C)
            st = self.exec_global(C, active, gp, interactive)
            if st != 0:
                return st
        elif c == "h" or c == "H":
            if cnt:
                raise EdError("Unexpected address")
            pflags = self.get_command_suffix(C)
            if c == "H":
                self.verbose = not self.verbose
            if (c == "h" or self.verbose) and self.errmsg:
                self.write(self.errmsg + "\n")
        elif c == "i":
            pflags = self.get_command_suffix(C)
            if not isglobal:
                self.clear_undo()
            self.append_lines(C, s, True, isglobal)
        elif c == "j":
            f, s = self.check_range(self.cur, self.cur + 1, cnt, f, s)
            pflags = self.get_command_suffix(C)
            if not isglobal:
                self.clear_undo()
            if f != s:
                removed = self.lines[f - 1:s]
                self.cut = [l.text for l in removed]
                self.lines[f - 1:s] = [Line("".join(l.text for l in removed))]
                self.unmark(removed)
                self.cur = f
                self.touch()
        elif c == "k":
            ch = C.getc()
            if s == 0:
                raise EdError("Invalid address")
            pflags = self.get_command_suffix(C)
            if ch == "" or not ("a" <= ch <= "z"):
                raise EdError("Invalid mark character")
            self.marks[ch] = self.lines[s - 1]
        elif c in ("l", "n", "p"):
            n = {"l": PF_L, "n": PF_N, "p": PF_P}[c]
            f, s = self.check_range(self.cur, self.cur, cnt, f, s)
            pflags = self.get_command_suffix(C)
            self.print_lines(f, s, pflags | n)
            pflags = 0
        elif c == "m":
            f, s = self.check_range(self.cur, self.cur, cnt, f, s)
            addr = self.get_third_addr(C)
            if f <= addr < s:
                raise EdError("Invalid destination")
            pflags = self.get_command_suffix(C)
            if not isglobal:
                self.clear_undo()
            if addr == f - 1 or addr == s:
                self.cur = s
            else:
                block = self.lines[f - 1:s]
                del self.lines[f - 1:s]
                if addr > s:
                    ins = addr - len(block)
                else:
                    ins = addr
                self.lines[ins:ins] = block
                self.cur = ins + len(block)
            self.touch()
        elif c in ("P", "q", "Q"):
            if cnt:
                raise EdError("Unexpected address")
            pflags = self.get_command_suffix(C)
            if c == "P":
                self.prompt_on = not self.prompt_on
            elif c == "q" and self.modified and prev != EMOD:
                return EMOD
            else:
                return QUIT
        elif c == "r":
            if not isspace(C.peek()):
                raise EdError("Unexpected command suffix")
            if cnt == 0:
                s = last
            fn = self.get_filename(C)
            if not self.def_filename and fn:
                self.def_filename = fn
            if not isglobal:
                self.clear_undo()
            n = self.read_file(fn if fn else self.def_filename, s)
            if n:
                self.modified = True
        elif c == "s":
            pflags = self.cmd_subst(C, cnt, f, s, isglobal)
        elif c == "t":
            f, s = self.check_range(self.cur, self.cur, cnt, f, s)
            addr = self.get_third_addr(C)
            pflags = self.get_command_suffix(C)
            if not isglobal:
                self.clear_undo()
            texts = [l.text for l in self.lines[f - 1:s]]
            self.insert_texts(addr, texts)
        elif c == "u":
            if cnt:
                raise EdError("Unexpected address")
            pflags = self.get_command_suffix(C)
            self.undo(isglobal)
        elif c == "w" or c == "W":
            n = C.peek()
            if n == "q" or n == "Q":
                C.i += 1
            else:
                n = ""
            if not isspace(C.peek()):
                raise EdError("Unexpected command suffix")
            fn = self.get_filename(C)
            if cnt == 0 and last == 0:
                f = s = 0
            else:
                f, s = self.check_range(1, last, cnt, f, s)
            if not self.def_filename and fn:
                self.def_filename = fn
            k = self.write_file(fn if fn else self.def_filename,
                                "ab" if c == "W" else "wb", f, s)
            if k == self.last:
                self.modified = False
            elif n == "q" and self.modified and prev != EMOD:
                return EMOD
            if n == "q" or n == "Q":
                return QUIT
        elif c == "x":
            if s < 0 or s > last:
                raise EdError("Invalid address")
            pflags = self.get_command_suffix(C)
            if not isglobal:
                self.clear_undo()
            if not self.cut:
                raise EdError("Nothing to put")
            self.insert_texts(s, list(self.cut))
        elif c == "y":
            f, s = self.check_range(self.cur, self.cur, cnt, f, s)
            pflags = self.get_command_suffix(C)
            self.cut = [l.text for l in self.lines[f - 1:s]]
        elif c == "z":
            inc = 1 if (self.traditional or not isglobal) else 0
            f, s = self.check_range(1, self.cur + inc, cnt, 1, s)
            if C.peek() != "" and "1" <= C.peek() <= "9":
                self.window_lines = self.parse_int(C)
            pflags = self.get_command_suffix(C)
            self.print_lines(s, min(self.last, s + self.window_lines - 1),
                             pflags)
            pflags = 0
        elif c == "=":
            pflags = self.get_command_suffix(C)
            self.write("%d\n" % (s if cnt else last))
        elif c == "\n":
            inc = 1 if (self.traditional or not isglobal) else 0
            f, s = self.check_range(1, self.cur + inc, cnt, 1, s)
            self.print_lines(s, s, 0)
        elif c == "#":
            while True:
                ch = C.getc()
                if ch == "\n" or ch == "":
                    break
        elif c == "!":
            raise EdError("Unknown command")
        else:
            raise EdError("Unknown command")
        if pflags:
            self.print_lines(self.cur, self.cur, pflags)
        return 0

    # --------------------------------------------------------- main loop
    def main_loop(self, initial_error):
        err_status = 0
        status = 0
        regular = stdin_is_regular()
        if initial_error:
            status = ERR
            if not self.loose:
                err_status = 1
        while True:
            if status < 0 and self.verbose:
                self.write(self.errmsg + "\n")
            if self.prompt_on:
                self.write(self.prompt)
            line = self.read_line()
            if line is None:
                if not self.modified or status == EMOD:
                    status = QUIT
                else:
                    status = EMOD
            else:
                status = self.exec_command(Cursor(line), status, False)
            if status == 0:
                continue
            if status == QUIT:
                return err_status
            self.write("?\n")
            if not self.loose and err_status == 0:
                err_status = 1
            if status == EMOD:
                self.errmsg = "Warning: buffer modified"
            if regular:
                self.diag("script, line %d: %s" % (self.linenum, self.errmsg))
                return 2


def usage_error(msg):
    sys.stderr.write("ed: %s\n" % msg)
    sys.stderr.write("Try 'ed --help' for more information.\n")
    return 1


def run(argv):
    ed = Ed()
    files = []
    i = 0
    only_files = False
    longmap = {"--extended-regexp": "E", "--traditional": "G",
               "--loose-exit-status": "l", "--quiet": "q", "--silent": "q",
               "--restricted": "r", "--script": "s", "--verbose": "v"}
    while i < len(argv):
        a = argv[i]
        i += 1
        if only_files or a == "-" or not a.startswith("-"):
            files.append(a)
            continue
        if a == "--":
            only_files = True
            continue
        if a.startswith("--"):
            if a.startswith("--prompt="):
                ed.prompt = a[len("--prompt="):]
                ed.prompt_on = True
                continue
            if a == "--prompt":
                if i >= len(argv):
                    return usage_error("option '--prompt' requires an argument")
                ed.prompt = argv[i]
                i += 1
                ed.prompt_on = True
                continue
            if a in longmap:
                opts = longmap[a]
            elif a == "--strip-trailing-cr":
                continue
            else:
                return usage_error("unrecognized option '%s'" % a)
        else:
            opts = a[1:]
        j = 0
        while j < len(opts):
            o = opts[j]
            j += 1
            if o == "E":
                ed.extended = True
            elif o == "G":
                ed.traditional = True
            elif o == "l":
                ed.loose = True
            elif o == "q":
                ed.quiet = True
            elif o == "r":
                ed.restricted = True
            elif o == "s":
                ed.scripted = True
            elif o == "v":
                ed.verbose = True
            elif o == "p":
                if j < len(opts):
                    ed.prompt = opts[j:]
                else:
                    if i >= len(argv):
                        return usage_error("option requires an argument -- 'p'")
                    ed.prompt = argv[i]
                    i += 1
                ed.prompt_on = True
                break
            else:
                return usage_error("invalid option -- '%s'" % o)
    initial_error = False
    if files:
        fn = files[0]
        try:
            ed.may_access(fn)
            ok = True
        except EdError as e:
            ed.errmsg = str(e)
            ed.diag(str(e))
            ok = False
        if not ok:
            if stdin_is_regular():
                return 2
            initial_error = True
        else:
            try:
                ed.read_file(fn, 0)
                ed.undo_changed = False
            except EdError as e:
                ed.errmsg = str(e)
                if stdin_is_regular():
                    ed.out.flush()
                    return 2
                initial_error = True
            ed.def_filename = fn
    try:
        return ed.main_loop(initial_error)
    finally:
        try:
            ed.out.flush()
        except Exception:
            pass


def main(argv):
    import threading
    sys.setrecursionlimit(200000)
    threading.stack_size(512 * 1024 * 1024)
    result = [1]

    def target():
        result[0] = run(argv)
    t = threading.Thread(target=target)
    t.start()
    t.join()
    try:
        sys.stdout.flush()
    except Exception:
        pass
    return result[0]


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
