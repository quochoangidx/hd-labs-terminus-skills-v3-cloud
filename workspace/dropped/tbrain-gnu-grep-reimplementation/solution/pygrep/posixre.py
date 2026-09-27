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
        while True:
            c = self.peek()
            if c is None:
                return atom
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
        self.icase_backref = icase

    def _m(self, node, s, i, caps, k):
        """Generate every (end, caps) for node matching s at i, then call continuation."""
        kind = node[0]
        if kind == "set":
            if i < len(s) and ((s[i] in node[1]) != node[2]):
                if not (self.multiline and s[i] == "\n" and (node[2] or len(node[1]) == 256)):
                    yield from k(i + 1, caps)
            return
        if kind == "cat":
            items = node[1]

            def step(n, j, cp):
                if n == len(items):
                    yield from k(j, cp)
                else:
                    yield from self._m(items[n], s, j, cp, lambda jj, cc: step(n + 1, jj, cc))
            yield from step(0, i, caps)
            return
        if kind == "alt":
            for b in node[1]:
                yield from self._m(b, s, i, caps, k)
            return
        if kind == "group":
            idx = node[1]

            def close(j, cp):
                cp2 = cp[:idx] + ((i, j),) + cp[idx + 1:]
                yield from k(j, cp2)
            yield from self._m(node[2], s, i, caps, close)
            return
        if kind == "backref":
            span = caps[node[1]]
            if span is None:
                return
            text = s[span[0]:span[1]]
            if s.startswith(text, i) if not self.icase_backref else s[i:i + len(text)].lower() == text.lower():
                yield from k(i + len(text), caps)
            return
        if kind == "rep":
            sub, lo, hi = node[1], node[2], node[3]

            def loop(count, j, cp):
                if hi is None or count < hi:
                    def after(jj, cc):
                        if jj == j and count >= lo:
                            return iter(())
                        return loop(count + 1, jj, cc)
                    yield from self._m(sub, s, j, cp, after)
                if count >= lo:
                    yield from k(j, cp)
            yield from loop(0, i, caps)
            return
        if kind == "bol":
            if (i == 0 and not self.notbol) or (self.multiline and i > 0 and s[i - 1] == "\n"):
                yield from k(i, caps)
            return
        if kind == "eol":
            if i == len(s) or (self.multiline and s[i] == "\n"):
                yield from k(i, caps)
            return
        if kind == "bos":
            if i == 0:
                yield from k(i, caps)
            return
        if kind == "eos":
            if i == len(s):
                yield from k(i, caps)
            return
        before = i > 0 and s[i - 1] in WORD
        after_ = i < len(s) and s[i] in WORD
        ok = {"wordb": before != after_, "nwordb": before == after_,
              "wbeg": (not before) and after_, "wend": before and not after_}[kind]
        if ok:
            yield from k(i, caps)

    icase_backref = False

    def match_at(self, s, i):
        """Longest match starting at i: (end, caps) or None."""
        best = None
        init = (None,) * (self.ngroups + 1)
        for end, caps in self._m(self.node, s, i, init, lambda j, c: iter([(j, c)])):
            if best is None or end > best[0]:
                best = (end, caps)
        return best

    @staticmethod
    def _better(a, b):
        # POSIX: earlier subexpressions first, each leftmost then longest
        for x, y in zip(a[1:], b[1:]):
            if x == y:
                continue
            if x is None:
                return False
            if y is None:
                return True
            if x[0] != y[0]:
                return x[0] < y[0]
            return (x[1] - x[0]) > (y[1] - y[0])
        return False

    notbol = False

    def search(self, s, start=0, notbol=False):
        """Leftmost-longest match at or after start: (begin, end, groups) or None."""
        self.notbol = notbol
        for i in range(start, len(s) + 1):
            r = self.match_at(s, i)
            if r is not None:
                end, caps = r
                return i, end, caps
        return None
