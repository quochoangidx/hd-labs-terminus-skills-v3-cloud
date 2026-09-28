"""Command scripts generated from the task's command grammar when the verifier collects.

The hand-written families pin one rule each. These scripts combine the rules instead:
every address form, command, suffix, s flag and form, regular-expression construct,
file command and option below is drawn at random into short scripts over small
buffers, and GNU ed 1.19 decides each expected result at run time, as for every other
case. Nothing here holds an expected result.

The generator is seeded, so the same scripts come out on every run. Every entry of the
grammar tables is counted as it is drawn, and collection fails unless each one was
drawn at least MIN_USES times, so no part of the grammar can quietly drop out.
"""

import random
from collections import Counter

SEED = 19_026_926
BUCKETS = 8
PER_BUCKET = 80
MIN_USES = 3

LINES = [
    "alpha one", "beta two", "gamma three", "delta four", "epsilon five", "a!b", "x1 y2 z3",
    "back\\slash", "tab\there", "", "  lead", "trail  ", "[-a]", "a-b", "aaa", "abab",
    "{2}", "a|b", "e.e", "123", "#hash", "foo bar foo", "Mixed Case", "under_score", "ab*c",
    "a.b", "/slash/", "tt th t", "0", "phalp",
]

# addresses
ATOMS = [".", ".", ".", "$", "$", "$", "NUM", "NUM", "NUM", "NUM", "NUM", "NUM", "NUM", "NUM", "+", "-",
         "++", "--", "+2", "-2", "/RE/", "/RE/", "?RE?", "//", "??", "'a", "'b"]
OFFSETS = ["", "", "", "", "", "", "", "", "+1", "-1", "+", "-", " +1"]
RANGES = ["one", "one", "one", "one", "none", "none", "none", "none", "none", "none", "A,B", "A;B",
          ",", ";", "A,", ",B", "A;", "A,B,C", " A , B "]

# regular expressions (the delimiter is chosen so that it never occurs inside)
BRE = ["e", "a", "o*", "^", "$", "^$", ".", "[-a]", "[a-]", "[]a]", "[^a-e]", "[[:digit:]]",
       "[[:space:]]", "[[:alpha:]]\\+", "[[:upper:]]", "\\(.\\)\\1", "\\(a\\|al\\)\\(p\\|ph\\)",
       "t\\|th", "a\\{0\\}", "a\\{2\\}", "a\\{1,2\\}", "o\\{0,1\\}", "b\\{1,\\}", "a\\?b", "x*y*",
       ".*", "\\.", "\\*", "[.]", "e.e", "a*b", "\\(ab\\)*", "!", "1", "\\(a\\)\\(b\\)", "*a",
       "^\\*", "[[:punct:]]", "\\{2\\}", "a\\{2", "\\(a", "[a", "\\(\\)", "[[.-.]]",
       "[[=a=]]", "|", "a$b", "a^"]
ERE = ["(ab|a)(bc|c)", "o+", "a{2,}", "a{0}", "(o)(o)?", "^(foo|bar)+$", "a|b", "\\|", "[-a]",
       "x?y", "(a|ab)(c|bcd)?", "[[:digit:]]+", "(.)\\1", "^$", "a{1,2}b", "(a", "e.e", "t|th",
       "\\.", "(^a|b$)", "[^[:alpha:] ]", "a^b"]

# replacements; "\\\n" splits the line at that point
REPLACEMENTS = ["E", "&&", "<&>", "", "%", "\\1", "\\2\\1", "\\&", "a\\\nb", "\\\n", "\\\\",
                "-&-", "\\n"]
S_FLAGS = ["", "", "g", "2", "3g", "gp", "p", "n", "gn", "I", "gI", "pn", "g2", "0", "q"]
S_REPEATS = ["s", "sg", "sp", "sn", "s2", "sr", "sgp", "s3", "srg", "s\t"]
DELIMITERS = ["/", "|", ",", "#", ";", "."]

SUFFIXES = ["", "", "", "", "", "p", "p", "n", "pn", "np", "pp", "x"]
# lines typed in input mode; when the command that opens input mode fails, ed reads them
# as commands, so none of them may start an out-of-scope command either
TEXT_LINES = ["new", "q y", "", "beta", "..", " .", "e.e", "a|b"]
INPUT_SUFFIXES = ["", "", "", "p", "n", "pn"]
G_LISTS = ["p", "d", "s/e/E/", "m0", "t.", "-1p", "j", ".=", "s//X/g", "n", "", "a\\\nadded\\\n.",
           "i\\\nins\\\n.", "c\\\nchg\\\n.", "s/a/A/\\\np", "u", "+d", "s/zz/y/", "ka", "w out.txt",
           "q", "s/./&&/\\\n.=", "s/e/E"]
FILE_COMMANDS = ["w", "W", "r", "e", "E", "f", "wq", "q", "Q"]
FILE_NAMES = ["out.txt", "f.txt", "other.txt", "missing.txt", "", "sub/new.txt"]
SEPARATORS = [" ", "\t", " ", ""]
ERRORS = ["bogus", "p x", "1,2k", "kA", "0d", "2,1p", "=5", "1,2j3", "s/a/b/q", "tq", "1s/a/b/2g3",
          "3,1d", "u1", "cp x"]
OPTIONS = [[], [], ["-s"], ["-s"], ["-l"], ["-E"], ["-s", "-l"], ["-sE"], ["-lsE"], ["-sl"],
           ["-E", "-s"], ["-ls"]]
COMMANDS = ["print", "print", "=", "null", "#", "a", "a", "i", "c", "d", "d", "j", "m", "t", "k", "u",
            "u", "s", "s", "s", "s-open", "s-repeat", "g", "g", "v", "file", "file", "error", "error",
            "addressed-u"]


class Grammar:
    def __init__(self, rng):
        self.rng = rng
        self.used = Counter()

    def pick(self, table, name):
        index = self.rng.randrange(len(table))
        self.used[(name, index)] += 1
        return table[index]

    def regex(self, ere):
        return self.pick(ERE, "ere") if ere else self.pick(BRE, "bre")

    def delimited(self, ere, pieces):
        """A delimiter that none of the pieces contains."""
        for _ in range(len(DELIMITERS)):
            delim = self.pick(DELIMITERS, "delimiter")
            if not any(delim in piece for piece in pieces):
                return delim
        return None

    def atom(self, ere, size):
        atom = self.pick(ATOMS, "atom")
        if atom == "NUM":
            if size and self.rng.random() < 0.85:
                return str(self.rng.randint(1, size))
            return str(self.rng.randint(0, size + 2))
        if "RE" in atom:
            pattern = self.regex(ere)
            delim = atom[0]
            if delim in pattern:
                return str(self.rng.randint(1, max(size, 1)))
            return atom.replace("RE", pattern)
        return atom

    def address(self, ere, size):
        return self.atom(ere, size) + self.pick(OFFSETS, "offset")

    def addresses(self, ere, size):
        shape = self.pick(RANGES, "range")
        if shape == "none":
            return ""
        if shape == "one":
            return self.address(ere, size)
        text = shape
        for slot in ("A", "B", "C"):
            text = text.replace(slot, self.address(ere, size), 1)
        return text

    def text_block(self):
        lines = [self.pick(TEXT_LINES, "text") for _ in range(self.rng.randint(0, 3))]
        return "".join(line + "\n" for line in lines) + "."

    def substitute(self, ere, open_end=False):
        pattern = self.regex(ere)
        replacement = self.pick(REPLACEMENTS, "replacement")
        delim = self.delimited(ere, [pattern, replacement])
        if delim is None:
            pattern, replacement, delim = "e", "E", "/"
        if open_end:
            return "s" + delim + pattern + delim + replacement
        return "s" + delim + pattern + delim + replacement + delim + self.pick(S_FLAGS, "s-flag")

    def command(self, ere, size):
        kind = self.pick(COMMANDS, "command")
        addr = self.addresses(ere, size)
        if kind == "print":
            base = self.rng.choice("pn")
            suffix = self.pick(SUFFIXES, "suffix")
            return addr + base + (suffix if base not in suffix else "")
        if kind == "=":
            return addr + "="
        if kind == "null":
            return addr
        if kind == "#":
            return addr + "# note"
        if kind in "aic":
            return addr + kind + self.pick(INPUT_SUFFIXES, "input-suffix") + "\n" + self.text_block()
        if kind in ("d", "j"):
            return addr + kind + self.pick(SUFFIXES, "suffix")
        if kind in ("m", "t"):
            return addr + kind + self.address(ere, size) + self.pick(SUFFIXES, "suffix")
        if kind == "k":
            return addr + "k" + self.rng.choice("ab")
        if kind == "u":
            return "u" + self.pick(SUFFIXES, "suffix")
        if kind == "addressed-u":
            return self.address(ere, size) + "u"
        if kind == "s":
            return addr + self.substitute(ere)
        if kind == "s-open":
            return addr + self.substitute(ere, open_end=True)
        if kind == "s-repeat":
            return addr + self.pick(S_REPEATS, "s-repeat")
        if kind in ("g", "v"):
            pattern = self.regex(ere)
            listing = self.pick(G_LISTS, "g-list")
            delim = self.delimited(ere, [pattern])
            if delim is None:
                pattern, delim = "e", "/"
            return addr + kind + delim + pattern + delim + listing
        if kind == "file":
            name = self.pick(FILE_COMMANDS, "file-command")
            target = self.pick(FILE_NAMES, "file-name") if name not in ("q", "Q") else ""
            separator = self.pick(SEPARATORS, "separator") if target else ""
            prefix = addr if name in ("w", "W", "r", "wq") else ""
            return prefix + name + separator + target
        return self.pick(ERRORS, "error")

    def buffer(self):
        count = self.rng.randint(2, 14)
        return "".join(self.pick(LINES, "line") + "\n" for _ in range(count))

    def case(self):
        options = list(self.pick(OPTIONS, "options"))
        ere = any("E" in option for option in options)
        files = {"f.txt": self.buffer(), "other.txt": self.buffer()}
        stdin = self.rng.choice(["pipe", "pipe", "file"])
        start = self.rng.random()
        if start < 0.75:
            operand = ["f.txt"]
            size = files["f.txt"].count("\n")
        elif start < 0.85 and stdin == "pipe":
            operand = ["new.txt"]
            size = 0
        else:
            operand = []
            size = 0
        if operand and self.rng.random() < 0.25:
            args = operand + options
        else:
            args = options + operand
        commands = []
        if size == 0:
            # an empty buffer turns nearly every address into an error, so give it lines
            size = self.rng.randint(2, 8)
            commands.append("a\n" + "".join(self.pick(LINES, "line") + "\n" for _ in range(size)) + ".")
        commands += [self.command(ere, size) for _ in range(self.rng.randint(3, 9))]
        commands.append(self.rng.choice([",n", ",p", "w", "Q", ",p"]))
        return {"args": args, "stdin": stdin, "script": "".join(c + "\n" for c in commands),
                "files": sorted(files.items())}

    def table_sizes(self):
        return {"atom": ATOMS, "offset": OFFSETS, "range": RANGES, "bre": BRE, "ere": ERE,
                "replacement": REPLACEMENTS, "s-flag": S_FLAGS, "s-repeat": S_REPEATS,
                "delimiter": DELIMITERS, "suffix": SUFFIXES, "input-suffix": INPUT_SUFFIXES, "text": TEXT_LINES, "g-list": G_LISTS,
                "file-command": FILE_COMMANDS, "file-name": FILE_NAMES, "separator": SEPARATORS,
                "error": ERRORS, "options": OPTIONS, "command": COMMANDS, "line": LINES}


def generate():
    """Return {bucket name: [case, ...]}, failing if any grammar entry was drawn too rarely."""
    grammar = Grammar(random.Random(SEED))
    buckets = {}
    for bucket in range(1, BUCKETS + 1):
        buckets["generated_%d" % bucket] = [grammar.case() for _ in range(PER_BUCKET)]
    rare = [(name, table[index], grammar.used[(name, index)])
            for name, table in grammar.table_sizes().items()
            for index in range(len(table)) if grammar.used[(name, index)] < MIN_USES]
    if rare:
        raise AssertionError("grammar entries drawn fewer than %d times: %r" % (MIN_USES, rare))
    for cases in buckets.values():
        for case in cases:
            if any(len(line) > 200 for line in case["script"].split("\n")):
                raise AssertionError("a generated script line exceeds 200 bytes")
    return buckets
