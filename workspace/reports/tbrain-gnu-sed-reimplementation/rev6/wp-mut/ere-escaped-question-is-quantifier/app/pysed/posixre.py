"""GNU sed regular expressions (BRE and ERE) with POSIX leftmost-longest matching."""

import string

CLASSES = {
    "alpha": string.ascii_letters, "digit": string.digits, "alnum": string.ascii_letters + string.digits,
    "upper": string.ascii_uppercase, "lower": string.ascii_lowercase, "space": " \t\n\r\f\v",
    "blank": " \t", "punct": string.punctuation, "xdigit": string.hexdigits,
    "cntrl": "".join(chr(i) for i in range(32)) + "\x7f",
    "print": "".join(chr(i) for i in range(32, 127)), "graph": "".join(chr(i) for i in range(33, 127)),
}
WORD = frozenset(string.ascii_letters + string.digits + "_")
ANY = frozenset(chr(i) for i in range(256))


class RegexError(Exception):
    pass


class Parser:
    """A BRE or ERE as a tree: ("set", chars, negated), ("cat", items), ("alt", branches),
    ("group", n, node), ("rep", node, lo, hi) and the assertions ("bol",), ("eol",),
    ("wordb",), ("nwordb",), ("wbeg",), ("wend",)."""

    def __init__(self, src, ere):
        self.s, self.i, self.ere = src, 0, ere
        self.ngroups = 0

    def peek(self, k=0):
        j = self.i + k
        return self.s[j] if j < len(self.s) else None

    def parse(self):
        node = self.alt()
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

    def alt(self):
        branches = [self.concat()]
        while self.at_alt():
            self.i += 1 if self.ere else 2
            branches.append(self.concat())
        return branches[0] if len(branches) == 1 else ("alt", branches)

    def concat(self):
        items = []
        start = True
        while self.peek() is not None and not self.at_alt() and not self.at_close():
            items.append(self.quantifiers(self.atom(start)))
            start = False
        return ("cat", items)

    def quantifiers(self, atom):
        quantified = False
        while True:
            c = self.peek()
            if c is None:
                return atom
            if not self.ere and quantified and (c == "*" or (c == "\\" and self.peek(1) == "{")):
                # GNU sed 4.9 rejects a BRE * or \{ right after another repetition
                raise RegexError("Invalid preceding regular expression")
            quantified = True
            if c == "*":
                self.i += 1
                atom = ("rep", atom, 0, None)
            elif self.ere and c in "+?":
                self.i += 1
                atom = ("rep", atom, 1, None) if c == "+" else ("rep", atom, 0, 1)
            elif self.ere and c == "\\" and self.peek(1) == "?":
                self.i += 2
                atom = ("rep", atom, 0, 1)
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
        """{lo}, {lo,} or {lo,hi}; in an ERE an unterminated { is a literal instead."""
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
        return lo, hi

    @staticmethod
    def lit(ch):
        return ("set", frozenset((ch,)), False)

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
            return ("set", ANY, False)
        if c == "^":
            self.i += 1
            # an ERE ^ is an anchor anywhere (so a^b never matches); a BRE ^ only at the start
            if self.ere or start:
                if not self.ere and self.peek() == "*":
                    self.i += 1
                    return ("cat", [("bol",), self.lit("*")])
                return ("bol",)
            return self.lit("^")
        if c == "$":
            self.i += 1
            if self.ere or self.peek() is None or self.at_close() or self.at_alt():
                return ("eol",)
            return self.lit("$")
        if c == "*" and start:
            self.i += 1
            return self.lit("*")
        if self.ere and c in "+?{" and start:
            self.i += 1
            return self.lit(c)
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
        if n.isdigit() or n in "`'cdox":
            raise RegexError("outside the subset: \\" + n)
        table = {"w": ("set", WORD, False), "W": ("set", WORD, True),
                 "s": ("set", frozenset(CLASSES["space"]), False), "S": ("set", frozenset(CLASSES["space"]), True),
                 "b": ("wordb",), "B": ("nwordb",), "<": ("wbeg",), ">": ("wend",)}
        if n in table:
            return table[n]
        if n == "n":
            return self.lit("\n")
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
            if c == "[" and self.peek(1) in ("=", "."):
                raise RegexError("outside the subset: [" + self.peek(1))
            if c == "[" and self.peek(1) == ":":
                end = self.s.find(":]", self.i + 2)
                if end < 0:
                    raise RegexError("bad class")
                name = self.s[self.i + 2:end]
                if name not in CLASSES:
                    raise RegexError("bad class name")
                chars.update(CLASSES[name])
                self.i = end + 2
                continue
            self.i += 1
            lo = c
            if c == "\\" and self.peek() == "n":
                self.i += 1
                lo = "\n"
            if self.peek() == "-" and self.peek(1) not in ("]", None):
                self.i += 1
                hi = self.peek()
                self.i += 1
                if hi == "\\" and self.peek() == "n":  # \n ends a range too: [\t-\n]
                    self.i += 1
                    hi = "\n"
                chars.update(chr(k) for k in range(ord(lo), ord(hi) + 1))
            else:
                chars.add(lo)
        return ("set", frozenset(chars), negate)


def _assert(kind, s, i):
    if kind == "bol":
        return i == 0
    if kind == "eol":
        return i == len(s)
    before = i > 0 and s[i - 1] in WORD
    after = i < len(s) and s[i] in WORD
    return {"wordb": before != after, "nwordb": before == after,
            "wbeg": (not before) and after, "wend": before and not after}[kind]


class Regex:
    def __init__(self, src, ere=False):
        p = Parser(src, ere)
        self.node = p.parse()
        self.ngroups = p.ngroups
        self.prog = _compile(self.node)

    def search(self, s, start=0):
        """Leftmost-longest match at or after start: (begin, end, groups) or None."""
        for i in range(start, len(s) + 1):
            r = self._longest_at(s, i)
            if r is not None:
                end, caps = r
                return i, end, caps
        return None

    def _longest_at(self, s, start):
        """Longest match starting at start, by simulating the thread program (a Pike VM):
        every thread advances one character per step, so the time is bounded by the
        program size times the input length. When several paths give the same longest
        match the groups come from the first path in traversal order, which is the path a
        depth-first search would find first; -E (a|aa)(a?) on aa reports \\1 = a, as GNU
        sed 4.9 does."""
        prog = self.prog
        nslots = 2 * (self.ngroups + 1)

        def add(threads, seen, pc, i, caps):
            stack = [(pc, caps)]
            while stack:
                pc, caps = stack.pop()
                if pc in seen:
                    continue
                seen.add(pc)
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
                    if _assert(op[1], s, i):
                        stack.append((pc + 1, caps))
                else:
                    threads.append((pc, caps))

        best = None
        threads = []
        add(threads, set(), 0, start, (None,) * nslots)
        i = start
        while threads:
            nxt = []
            seen = set()
            ch = s[i] if i < len(s) else None
            for pc, caps in threads:
                op = prog[pc]
                if op[0] == "match":
                    if best is None or i > best[0]:
                        best = (i, caps)
                    continue  # later threads may still reach a longer end
                if ch is None or (ch in op[1]) == op[2]:
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


def _compile(node):
    """Tree to a thread program: char/split/jmp/save/assert/match."""
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
        elif kind == "rep":
            sub, lo, hi = n[1], n[2], n[3]
            for _ in range(lo):
                gen(sub)
            if hi is None:
                # an extra iteration may not match the empty string: it would loop back to a
                # state already visited at this position, which the simulation drops
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
