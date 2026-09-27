"""GNU sed regular expressions (BRE and ERE) with POSIX leftmost-longest matching."""

import string

CLASSES = {
    "alpha": string.ascii_letters, "digit": string.digits, "alnum": string.ascii_letters + string.digits,
    "upper": string.ascii_uppercase, "lower": string.ascii_lowercase, "space": " \t\n\r\f\v",
    "blank": " \t", "punct": string.punctuation, "xdigit": string.hexdigits,
    "cntrl": "".join(chr(i) for i in range(32)) + "\x7f",
    "print": "".join(chr(i) for i in range(32, 127)), "graph": "".join(chr(i) for i in range(33, 127)),
}
WORD = set(string.ascii_letters + string.digits + "_")
ALL = [chr(i) for i in range(256)]


class RegexError(Exception):
    pass


class Parser:
    def __init__(self, src, ere, icase):
        self.s, self.i, self.ere, self.icase = src, 0, ere, icase
        self.ngroups = 0

    def peek(self, k=0):
        j = self.i + k
        return self.s[j] if j < len(self.s) else None

    def parse(self):
        node = self.alt(top=True)
        if self.i != len(self.s):
            raise RegexError("unmatched ) or trailing text")
        return node

    def at_alt(self):
        if self.ere:
            return self.peek() == "|"
        return self.peek() == "\\" and self.peek(1) == "|"

    def at_close(self):
        if self.ere:
            return self.peek() == ")"
        return self.peek() == "\\" and self.peek(1) == ")"

    def alt(self, top=False):
        branches = [self.concat()]
        while self.at_alt():
            self.i += 1 if self.ere else 2
            branches.append(self.concat())
        return branches[0] if len(branches) == 1 else ("alt", branches)

    def concat(self):
        items = []
        start = True
        while self.peek() is not None and not self.at_alt() and not self.at_close():
            atom = self.atom(start)
            start = False
            if atom is None:
                continue
            atom = self.quantifiers(atom)
            items.append(atom)
        return ("cat", items)

    def quantifiers(self, atom):
        quantified = False
        while True:
            c = self.peek()
            if c is None:
                return atom
            if (not self.ere and quantified
                    and (c == "*" or (c == "\\" and self.peek(1) == "{"))):
                # GNU sed 4.9 (glibc) rejects a BRE * or \{ right after another repetition
                pass
            quantified = True
            if c == "*":
                self.i += 1
                atom = ("rep", atom, 0, None)
            elif self.ere and c in "+?":
                self.i += 1
                atom = ("rep", atom, 1, None) if c == "+" else ("rep", atom, 0, 1)
            elif not self.ere and c == "\\" and self.peek(1) in ("+", "?"):
                q = self.peek(1)
                self.i += 2
                atom = ("rep", atom, 1, None) if q == "+" else ("rep", atom, 0, 1)
            elif (self.ere and c == "{") or (not self.ere and c == "\\" and self.peek(1) == "{"):
                save = self.i
                self.i += 1 if self.ere else 2
                lo_hi = self.interval()
                if lo_hi is None:
                    self.i = save
                    return atom
                atom = ("rep", atom, lo_hi[0], lo_hi[1])
            else:
                return atom

    def interval(self):
        j = self.i
        num = ""
        while self.peek() and self.peek().isdigit():
            num += self.peek()
            self.i += 1
        lo = int(num) if num else 0
        hi = lo
        if self.peek() == ",":
            self.i += 1
            num2 = ""
            while self.peek() and self.peek().isdigit():
                num2 += self.peek()
                self.i += 1
            hi = int(num2) if num2 else None
        if self.ere:
            if self.peek() != "}":
                self.i = j
                return None
            self.i += 1
        else:
            if not (self.peek() == "\\" and self.peek(1) == "}"):
                raise RegexError("bad interval")
            self.i += 2
        if not num and self.ere:
            pass
        return lo, hi

    def lit(self, ch):
        if self.icase and ch.isalpha():
            return ("set", frozenset({ch.lower(), ch.upper()}), False)
        return ("set", frozenset({ch}), False)

    def atom(self, start):
        c = self.peek()
        if c == "\\":
            n = self.peek(1)
            if n is None:
                raise RegexError("trailing backslash")
            if not self.ere and n == "(":
                self.i += 2
                return self.group()
            if not self.ere and n == "{" and start:
                self.i += 2
                return self.lit("{")
            self.i += 2
            return self.escape(n)
        if self.ere and c == "(":
            self.i += 1
            return self.group()
        if c == "[":
            self.i += 1
            return self.bracket()
        if c == ".":
            self.i += 1
            return ("set", frozenset(ALL), False)
        if c == "^":
            self.i += 1
            # ERE ^ and $ are anchors anywhere (glibc, as GNU sed 4.9 runs them: a^b never matches)
            if self.ere or start:
                if not self.ere and self.peek() == "*":
                    self.i += 1
                    return ("cat", [("bol",), self.lit("*")])
                return ("bol",)
            return self.lit("^")
        if c == "$":
            self.i += 1
            if self.ere:
                return ("eol",)
            # BRE: anchor only at the end of the RE or before \) or \|
            if self.peek() is None or self.at_close() or self.at_alt():
                return ("eol",)
            return self.lit("$")
        if c == "*" and start:
            self.i += 1
            return self.lit("*")
        if self.ere and c in ("*", "+", "?") and start:
            self.i += 1
            return self.lit(c)
        if self.ere and c == "{" and start:
            self.i += 1
            return self.lit("{")
        self.i += 1
        return self.lit(c)

    def group(self):
        self.ngroups += 1
        idx = self.ngroups
        inner = self.alt()
        if not self.at_close():
            raise RegexError("unmatched (")
        self.i += 1 if self.ere else 2
        return ("group", idx, inner)

    def escape(self, n):
        if n.isdigit() and n != "0":
            k = int(n)
            if k > self.ngroups:
                raise RegexError("invalid reference")
            return ("backref", k)
        table = {"w": ("set", frozenset(WORD), False), "W": ("set", frozenset(WORD), True),
                 "s": ("set", frozenset(CLASSES["space"]), False), "S": ("set", frozenset(CLASSES["space"]), True),
                 "b": ("wordb",), "B": ("nwordb",), "<": ("wbeg",), ">": ("wend",), "`": ("bos",), "'": ("eos",)}
        if n in table:
            return table[n]
        if n == "n":
            return self.lit("\n")
        if self.ere and n in "|(){}+?":
            return self.lit(n)
        if not self.ere and n in "+?{}|()":
            return self.lit(n)
        return self.lit(n)

    def bracket(self):
        negate = False
        if self.peek() == "^":
            negate = True
            self.i += 1
        chars = set()
        first = True
        while True:
            c = self.peek()
            if c is None:
                raise RegexError("unterminated [")
            if c == "]" and not first:
                self.i += 1
                break
            first = False
            if c == "[" and self.peek(1) in (":", "=", "."):
                kind = self.peek(1)
                end = self.s.find(kind + "]", self.i + 2)
                if end < 0:
                    raise RegexError("bad class")
                name = self.s[self.i + 2:end]
                self.i = end + 2
                if kind == ":":
                    if name not in CLASSES:
                        raise RegexError("bad class name")
                    chars |= set(CLASSES[name])
                else:
                    chars |= set(name)
                continue
            self.i += 1
            lo = c
            if c == "\\" and self.peek() == "n":
                self.i += 1
                lo = "\n"
            if self.peek() == "-" and self.peek(1) not in ("]", None):
                self.i += 1
                hi = self.peek()
                if hi == "[" and self.peek(1) == ".":
                    end = self.s.find(".]", self.i + 2)
                    hi = self.s[self.i + 2:end]
                    self.i = end + 2
                else:
                    self.i += 1
                for k in range(ord(lo), ord(hi) + 1):
                    chars.add(chr(k))
            else:
                chars.add(lo)
        if self.icase:
            chars |= {ch.swapcase() for ch in chars if ch.isalpha()}
        return ("set", frozenset(chars), negate)


class Regex:
    def __init__(self, src, ere=False, icase=False, multiline=False):
        p = Parser(src, ere, icase)
        self.node = p.parse()
        self.ngroups = p.ngroups
        self.multiline = multiline
        self.icase_backref = icase  # I/i also makes \N compare case-insensitively
        self.prog = _compile(self.node)
        refs = sorted(_backrefs(self.node))
        self.ref_slots = tuple(k for g in refs for k in (2 * g, 2 * g + 1))

    def match_at(self, s, i):
        """Longest match starting at i: (end, caps) or None."""
        return self._pike(s, i)

    def search(self, s, start=0):
        """Leftmost-longest match at or after start: (begin, end, groups) or None."""
        for i in range(start, len(s) + 1):
            r = self.match_at(s, i)
            if r is not None:
                end, caps = r
                return i, end, caps
        return None

    def _assert(self, kind, s, i):
        if kind == "bol":
            return i == 0 or (self.multiline and s[i - 1] == "\n")
        if kind == "eol":
            return i == len(s) or (self.multiline and s[i] == "\n")
        if kind == "bos":
            return i == 0
        if kind == "eos":
            return i == len(s)
        before = i > 0 and s[i - 1] in WORD
        after_ = i < len(s) and s[i] in WORD
        return {"wordb": before != after_, "nwordb": before == after_,
                "wbeg": (not before) and after_, "wend": before and not after_}[kind]

    def _pike(self, s, start):
        """Longest match at start, in polynomial time. When several paths give that longest
        match, the groups come from the first path in traversal order; for -E (a|aa)(a?) on
        aa this reports \\1 = a, as GNU sed 4.9 does. Threads run in priority (traversal)
        order and the first thread to reach a given end wins, which is the path a
        depth-first search would find first. Two threads at the same instruction and
        position whose back-referenced groups hold the same spans behave identically from
        there on, so only the first (higher-priority) one is kept."""
        prog = self.prog
        nslots = 2 * (self.ngroups + 1)
        ref_slots = self.ref_slots
        icase = self.icase_backref

        def key(pc, off, caps):
            return (pc, off) + tuple(caps[k] for k in ref_slots)

        def add(threads, seen, pc, i, caps):
            stack = [(pc, caps)]
            while stack:
                pc, caps = stack.pop()
                k = key(pc, 0, caps)
                if k in seen:
                    continue
                seen.add(k)
                op = prog[pc]
                kind = op[0]
                if kind == "jmp":
                    stack.append((op[1], caps))
                elif kind == "split":
                    stack.append((op[2], caps))
                    stack.append((op[1], caps))
                elif kind == "save":
                    caps = caps[:op[1]] + (i,) + caps[op[1] + 1:]
                    stack.append((pc + 1, caps))
                elif kind == "assert":
                    if self._assert(op[1], s, i):
                        stack.append((pc + 1, caps))
                elif kind == "backref":
                    b, e = caps[2 * op[1]], caps[2 * op[1] + 1]
                    if b is None or e is None:
                        continue  # an unset group matches nothing
                    if b == e:
                        stack.append((pc + 1, caps))
                    else:
                        threads.append((pc, caps, 0))
                else:
                    threads.append((pc, caps, 0))

        best = None
        threads = []
        add(threads, set(), 0, start, (None,) * nslots)
        i = start
        while threads:
            nxt = []
            seen = set()
            ch = s[i] if i < len(s) else None
            for pc, caps, off in threads:
                op = prog[pc]
                kind = op[0]
                if kind == "match":
                    if best is None or i > best[0]:
                        best = (i, caps)
                    continue  # later threads may still reach a longer end
                if ch is None:
                    continue
                if kind == "backref":
                    b, e = caps[2 * op[1]], caps[2 * op[1] + 1]
                    want = s[b + off]
                    if want != ch and not (icase and want.lower() == ch.lower()):
                        continue
                    if b + off + 1 < e:
                        k = key(pc, off + 1, caps)
                        if k not in seen:
                            seen.add(k)
                            nxt.append((pc, caps, off + 1))
                    else:
                        add(nxt, seen, pc + 1, i + 1, caps)
                    continue
                chars, neg = op[1], op[2]
                if (ch in chars) == neg:
                    continue
                if self.multiline and ch == "\n" and (neg or len(chars) == 256):
                    continue
                add(nxt, seen, pc + 1, i + 1, caps)
            threads = nxt
            i += 1
        if best is None:
            return None
        end, slots = best
        caps = [None]
        for g in range(1, self.ngroups + 1):
            b, e = slots[2 * g], slots[2 * g + 1]
            caps.append((b, e) if b is not None and e is not None else None)
        return end, tuple(caps)


def _backrefs(node):
    kind = node[0]
    if kind == "backref":
        return {node[1]}
    if kind in ("cat", "alt"):
        return set().union(*(_backrefs(n) for n in node[1]))
    if kind == "group":
        return _backrefs(node[2])
    if kind == "rep":
        return _backrefs(node[1])
    return set()


def _compile(node):
    """Tree to a Pike-VM program: char/split/jmp/save/assert/backref/match."""
    prog = []

    def emit(op):
        prog.append(op)
        return len(prog) - 1

    def gen(n):
        kind = n[0]
        if kind == "set":
            emit(("char", n[1], n[2]))
        elif kind == "cat":
            for item in n[1]:
                gen(item)
        elif kind == "alt":
            jumps = []
            for b in n[1][:-1]:
                sp = emit(None)
                gen(b)
                jumps.append(emit(None))
                prog[sp] = ("split", sp + 1, len(prog))
            gen(n[1][-1])
            for j in jumps:
                prog[j] = ("jmp", len(prog))
        elif kind == "group":
            emit(("save", 2 * n[1]))
            gen(n[2])
            emit(("save", 2 * n[1] + 1))
        elif kind == "backref":
            emit(("backref", n[1]))
        elif kind == "rep":
            sub, lo, hi = n[1], n[2], n[3]
            for _ in range(lo):
                gen(sub)
            if hi is None:
                # an extra iteration may not match the empty string (it would loop back to
                # a state already visited at this position, which the VM drops)
                sp = emit(None)
                gen(sub)
                emit(("jmp", sp))
                prog[sp] = ("split", sp + 1, len(prog))
            else:
                holes = []
                for _ in range(hi - lo):
                    holes.append(emit(None))
                    gen(sub)
                for h in holes:
                    prog[h] = ("split", h + 1, len(prog))
        else:
            emit(("assert", kind))

    gen(node)
    emit(("match",))
    return prog
