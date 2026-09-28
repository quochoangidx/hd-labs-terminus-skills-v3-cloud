"""POSIX basic and extended regular expressions with GNU extensions and
leftmost-longest matching, as used by ed (glibc regcomp/regexec semantics)."""

import string

CLASSES = {
    "alpha": string.ascii_letters, "digit": string.digits, "alnum": string.ascii_letters + string.digits,
    "upper": string.ascii_uppercase, "lower": string.ascii_lowercase, "space": " \t\n\r\f\v",
    "blank": " \t", "punct": string.punctuation, "xdigit": string.hexdigits,
    "cntrl": "".join(chr(i) for i in range(32)) + "\x7f",
    "print": "".join(chr(i) for i in range(32, 127)), "graph": "".join(chr(i) for i in range(33, 127)),
}
WORD = set(string.ascii_letters + string.digits + "_")
DUP_MAX = 32767  # the largest repeat count the C library accepts
# In the C locale case folding touches the ASCII letters only; Python's str.lower() would
# also fold Latin-1 letters such as \xc9 and \xe9, which glibc leaves alone.
ASCII_FOLD = str.maketrans(string.ascii_uppercase + string.ascii_lowercase,
                           string.ascii_lowercase + string.ascii_uppercase)


def c_fold(text):
    """Lower-case the ASCII letters of text and nothing else."""
    return text.translate(str.maketrans(string.ascii_uppercase, string.ascii_lowercase))
ANCHORS = ("bol", "eol", "bos", "eos", "wordb", "nwordb", "wbeg", "wend")
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
        anchor = atom[0] in ANCHORS
        repeated = False
        while True:
            c = self.peek()
            if c is None:
                return atom
            if c == "*":
                if anchor if self.ere else repeated:
                    raise RegexError("nothing to repeat")
                self.i += 1
                atom, repeated = ("rep", atom, 0, None), True
            elif self.ere and c in "+?":
                if anchor:
                    raise RegexError("nothing to repeat")
                self.i += 1
                atom = ("rep", atom, 1, None) if c == "+" else ("rep", atom, 0, 1)
            elif not self.ere and c == "\\" and self.peek(1) in ("+", "?"):
                q = self.peek(1)
                self.i += 2
                atom = ("rep", atom, 1, None) if q == "+" else ("rep", atom, 0, 1)
                repeated = True
            elif (self.ere and c == "{") or (not self.ere and c == "\\" and self.peek(1) == "{"):
                if anchor or (repeated and not self.ere):
                    raise RegexError("nothing to repeat")
                self.i += 1 if self.ere else 2
                lo, hi = self.interval()
                atom, repeated = ("rep", atom, lo, hi), True
            else:
                return atom

    def interval(self):
        num = ""
        while self.peek() and self.peek().isdigit():
            num += self.peek()
            self.i += 1
        lo = int(num) if num else 0
        hi = lo
        comma = self.peek() == ","
        if comma:
            self.i += 1
            num2 = ""
            while self.peek() and self.peek().isdigit():
                num2 += self.peek()
                self.i += 1
            hi = int(num2) if num2 else None
        if not num and not comma:
            raise RegexError("bad interval")
        if self.ere:
            if self.peek() != "}":
                raise RegexError("bad interval")
            self.i += 1
        else:
            if not (self.peek() == "\\" and self.peek(1) == "}"):
                raise RegexError("bad interval")
            self.i += 2
        if hi is not None and hi < lo:
            raise RegexError("bad interval bounds")
        if lo > DUP_MAX or (hi is not None and hi > DUP_MAX):
            raise RegexError("repeat count too large")
        return lo, hi

    def lit(self, ch):
        if self.icase and ch in string.ascii_letters:
            return ("set", frozenset({ch, ch.translate(ASCII_FOLD)}), False)
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
            if not self.ere and n == "{":
                raise RegexError("nothing to repeat")
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
        if self.ere and c in ("*", "+", "?", "{"):
            raise RegexError("nothing to repeat")
        if c == "*" and start:
            self.i += 1
            return self.lit("*")
        self.i += 1
        return self.lit(c)

    def group(self):
        self.depth = getattr(self, "depth", 0) + 1
        if self.depth > 2:
            raise RegexError("nesting too deep")
        self.ngroups += 1
        idx = self.ngroups
        inner = self.alt()
        if not self.at_close():
            raise RegexError("unmatched (")
        self.i += 1 if self.ere else 2
        self.depth -= 1
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
        if self.ere and n in "|(){}+?":
            return self.lit(n)
        if not self.ere and n in "+?{}|()":
            return self.lit(n)
        return self.lit(n)

    def bracket_item(self):
        """One member of a bracket expression: a character, a class or an equivalence class."""
        c = self.peek()
        if c == "[" and self.peek(1) in (":", "=", "."):
            kind = self.peek(1)
            end = self.s.find(kind + "]", self.i + 2)
            if end < 0:
                raise RegexError("unterminated bracket element")
            name = self.s[self.i + 2:end]
            self.i = end + 2
            if kind == ":":
                if name not in CLASSES:
                    raise RegexError("bad class name")
                return "class", set(CLASSES[name])
            if len(name) != 1:
                raise RegexError("bad collating element")
            if kind == ".":
                return "char", name
            return "equiv", {name}
        self.i += 1
        return "char", c

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
            kind, value = self.bracket_item()
            if self.peek() == "-" and self.peek(1) not in ("]", None):
                self.i += 1
                hi_kind, hi_value = self.bracket_item()
                if kind != "char" or hi_kind != "char":
                    raise RegexError("bad range endpoint")
                if ord(value) > ord(hi_value):
                    raise RegexError("bad range")
                for k in range(ord(value), ord(hi_value) + 1):
                    chars.add(chr(k))
            elif kind == "char":
                chars.add(value)
            else:
                chars |= value
        if self.icase:
            chars |= {ch.translate(ASCII_FOLD) for ch in chars if ch in string.ascii_letters}
        return ("set", frozenset(chars), negate)


class Regex:
    """A compiled expression: the parse tree is flattened into a small program, and
    a match is a depth-first walk of that program over the text in the order the
    pattern is written, so the first way of matching wins among equally long ones.

    Every (instruction, position) pair is explored at most once per search when
    the expression has no backreference: a later arrival at the same pair can
    only reach the same ends with a lower priority, so the walk is linear in the
    text rather than exponential, and a search that fails at one starting point
    keeps what it learned for the next."""

    def __init__(self, src, ere=False, icase=False, multiline=False):
        p = Parser(src, ere, icase)
        self.node = p.parse()
        self.ngroups = p.ngroups
        self.multiline = multiline
        self.icase_backref = icase
        self.prog = []
        self.nregs = 0
        self.has_backref = False
        self._compile(self.node)
        self.prog.append(("match",))

    # ---- compiler -----------------------------------------------------------
    def _emit(self, ins):
        self.prog.append(ins)
        return len(self.prog) - 1

    def _compile(self, node):
        kind = node[0]
        prog = self.prog
        if kind == "set":
            self._emit(("char", node[1], node[2]))
        elif kind == "cat":
            for item in node[1]:
                self._compile(item)
        elif kind == "alt":
            jumps = []
            branches = node[1]
            for n, b in enumerate(branches):
                if n < len(branches) - 1:
                    split = self._emit(None)
                    self._compile(b)
                    jumps.append(self._emit(None))
                    prog[split] = ("split", split + 1, len(prog))
                else:
                    self._compile(b)
            for j in jumps:
                prog[j] = ("jmp", len(prog))
        elif kind == "group":
            self._emit(("save", 2 * node[1]))
            self._compile(node[2])
            self._emit(("save", 2 * node[1] + 1))
        elif kind == "backref":
            self.has_backref = True
            self._emit(("backref", node[1]))
        elif kind == "rep":
            sub, lo, hi = node[1], node[2], node[3]
            if hi is not None and sub[0] == "set":
                # a bounded run of one character class is one instruction that
                # tries the longest run first, so a large count is not a large program
                self._emit(("repc", sub[1], sub[2], lo, hi))
                return
            for _ in range(lo):
                self._compile(sub)
            reg = self.nregs
            self.nregs += 1
            if hi is None:
                head = self._emit(None)
                self._emit(("mark", reg))
                self._compile(sub)
                self._emit(("check", reg))
                self._emit(("jmp", head))
                prog[head] = ("split", head + 1, len(prog))
            else:
                splits = []
                for _ in range(hi - lo):
                    splits.append(self._emit(None))
                    self._emit(("mark", reg))
                    self._compile(sub)
                    self._emit(("check", reg))
                for sp in splits:
                    prog[sp] = ("split", sp + 1, len(prog))
        elif kind in ("bol", "eol", "bos", "eos", "wordb", "nwordb", "wbeg", "wend"):
            self._emit(("assert", kind))
        else:
            raise RegexError("bad node")

    # ---- matcher ------------------------------------------------------------
    def _assert(self, kind, s, i):
        if kind == "bol":
            return (i == 0 and not self.notbol) or (self.multiline and i > 0 and s[i - 1] == "\n")
        if kind == "eol":
            return i == len(s) or (self.multiline and s[i] == "\n")
        if kind == "bos":
            return i == 0
        if kind == "eos":
            return i == len(s)
        before = i > 0 and s[i - 1] in WORD
        after = i < len(s) and s[i] in WORD
        if kind == "wordb":
            return before != after
        if kind == "nwordb":
            return before == after
        if kind == "wbeg":
            return (not before) and after
        return before and not after

    def _walk(self, s, start, seen, runs):
        """Longest match starting at start: (end, caps) or None. seen is the set of
        (instruction, position) pairs already explored in this search, and runs
        remembers, per bounded-run instruction, the positions it has already
        offered as places to continue from."""
        prog = self.prog
        n = len(s)
        multiline = self.multiline
        memo = seen is not None
        best = None
        init_caps = (None,) * (2 * self.ngroups + 2)
        stack = [(0, start, init_caps, (None,) * self.nregs)]
        while stack:
            pc, i, caps, regs = stack.pop()
            while True:
                if memo:
                    key = (pc, i)
                    if key in seen:
                        break
                    seen.add(key)
                ins = prog[pc]
                op = ins[0]
                if op == "char":
                    if i < n and ((s[i] in ins[1]) != ins[2]) and not (
                            multiline and s[i] == "\n" and (ins[2] or len(ins[1]) == 256)):
                        pc += 1
                        i += 1
                        continue
                    break
                if op == "split":
                    stack.append((ins[2], i, caps, regs))
                    pc = ins[1]
                    continue
                if op == "repc":
                    chars, negate, lo, hi = ins[1], ins[2], ins[3], ins[4]
                    # how far the class matches from each position, measured once per search
                    lengths = runs.get(("len", pc))
                    if lengths is None:
                        lengths = [0] * (n + 1)
                        for j in range(n - 1, -1, -1):
                            if ((s[j] in chars) != negate) and not (
                                    multiline and s[j] == "\n" and (negate or len(chars) == 256)):
                                lengths[j] = lengths[j + 1] + 1
                        runs[("len", pc)] = lengths
                    r = lengths[i] if lengths[i] < hi else hi
                    if r < lo:
                        break
                    # shorter runs are tried after the longest; a run offered by an
                    # earlier start of this search was walked then and is not offered again
                    done = runs.get(pc)
                    first, last = i + lo, i + r - 1
                    if done is None:
                        fresh = [(first, last)]
                    else:
                        fresh = [(first, min(last, done[0] - 1)), (max(first, done[1] + 1), last)]
                    for lo_q, hi_q in fresh:
                        for q in range(lo_q, hi_q + 1):
                            stack.append((pc + 1, q, caps, regs))
                    # the remembered stretch stays one contiguous range of offered positions
                    if done is not None and i + lo <= done[1] + 1 and i + r >= done[0] - 1:
                        done[0] = min(done[0], i + lo)
                        done[1] = max(done[1], i + r)
                    else:
                        runs[pc] = [i + lo, i + r]
                    pc += 1
                    i += r
                    continue
                if op == "jmp":
                    pc = ins[1]
                    continue
                if op == "save":
                    caps = caps[:ins[1]] + (i,) + caps[ins[1] + 1:]
                    pc += 1
                    continue
                if op == "mark":
                    regs = regs[:ins[1]] + (i,) + regs[ins[1] + 1:]
                    pc += 1
                    continue
                if op == "check":
                    if regs[ins[1]] == i:
                        break
                    pc += 1
                    continue
                if op == "assert":
                    if self._assert(ins[1], s, i):
                        pc += 1
                        continue
                    break
                if op == "backref":
                    k = ins[1]
                    b, e = caps[2 * k], caps[2 * k + 1]
                    if b is None or e is None:
                        break
                    text = s[b:e]
                    if (c_fold(s[i:i + len(text)]) == c_fold(text) if self.icase_backref
                            else s.startswith(text, i)):
                        pc += 1
                        i += len(text)
                        continue
                    break
                # match
                if best is None or i > best[0]:
                    best = (i, caps)
                    if i == n:
                        return best
                break
        return best

    notbol = False

    def match_at(self, s, i):
        """Longest match starting at i: (end, groups) or None, groups being a tuple
        of (begin, end) per group with entry 0 unused, as the replacement code reads it."""
        r = self._walk(s, i, None if self.has_backref else set(), {})
        if r is None:
            return None
        return r[0], self._groups(r[1])

    def _groups(self, caps):
        return tuple(None if caps[2 * k] is None or caps[2 * k + 1] is None else (caps[2 * k], caps[2 * k + 1])
                     for k in range(self.ngroups + 1))

    def search(self, s, start=0, notbol=False):
        """Leftmost-longest match at or after start: (begin, end, groups) or None."""
        self.notbol = notbol
        seen = None if self.has_backref else set()
        runs = {}
        for i in range(start, len(s) + 1):
            r = self._walk(s, i, seen, runs)
            if r is not None:
                return i, r[0], self._groups(r[1])
        return None
