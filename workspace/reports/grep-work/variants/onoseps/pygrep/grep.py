"""pygrep: a GNU grep 3.8 replacement in pure Python.

Usage: python3 /app/pygrep/grep.py [OPTION]... PATTERNS [FILE]...
"""

import os
import stat
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from posixre import Regex, RegexError, WORD  # noqa: E402

INTMAX = 2 ** 63 - 1


class Usage(Exception):
    pass


# --------------------------------------------------------------------------- matching

class Matcher:
    """The compiled patterns: leftmost-longest matching over all of them."""

    def __init__(self, patterns, mode, icase, words, lines):
        self.words, self.lines = words, lines
        self.res = []
        for p in patterns:
            if mode == "F":
                src = "".join("\\" + c if c in ".[]()*+?{}|^$\\" else c for c in p)
                ere = True
            else:
                src = p
                ere = mode == "E"
            try:
                self.res.append(Regex(src, ere=ere, icase=icase))
            except (RegexError, RecursionError, IndexError, ValueError) as e:
                raise Usage(str(e))

    @staticmethod
    def _ends(rx, s, i):
        rx.notbol = False
        init = (None,) * (rx.ngroups + 1)
        return {end for end, _c in rx._m(rx.node, s, i, init, lambda j, c: iter([(j, c)]))}

    def line_matches(self, s):
        """Whether the line contains a match (the DFA's decision)."""
        if self.lines:
            for rx in self.res:
                rx.notbol = False
                r = rx.match_at(s, 0)
                if r is not None and r[0] == len(s):
                    return True
            return False
        if self.words:
            for rx in self.res:
                for i in range(len(s) + 1):
                    if i > 0 and s[i - 1] in WORD:
                        continue
                    for j in self._ends(rx, s, i):
                        if j < len(s) and s[j] in WORD:
                            continue
                        return True
            return False
        for rx in self.res:
            if rx.search(s) is not None:
                return True
        return False

    def _longest_at(self, rx, s, i, limit):
        """Longest match of rx starting at i inside s[:limit], $ not matching at the cut."""
        t = s[:limit]
        best = None
        for j in self._ends_cut(rx, t, i, limit < len(s)):
            if best is None or j > best:
                best = j
        return None if best is None else best - i

    def _ends_cut(self, rx, t, i, not_eol):
        if not not_eol:
            return self._ends(rx, t, i)
        # a '$' may not match at the artificial end: append a sentinel
        return {j for j in self._ends(rx, t + "\0", i) if j <= len(t)} if "\0" not in t else self._ends(rx, t, i)

    def find(self, s, start):
        """Leftmost-longest match at or after `start` as (begin, length), or None (-o path)."""
        best = None
        for rx in self.res:
            r = rx.search(s, start)
            if r is None:
                continue
            m, e = r[0], r[1]
            ln = e - m
            if self.words:
                found = None
                while True:
                    if not (m + ln < len(s) and s[m + ln] in WORD) and not (m > 0 and s[m - 1] in WORD):
                        found = (m, ln)
                        break
                    shorter = 0
                    if ln > 0:
                        ln -= 1
                        size = m + ln - start
                        got = self._longest_at(rx, s, m, size) if m <= size else None
                        if got is not None:
                            shorter = got
                    if shorter > 0:
                        ln = shorter
                    else:
                        if m == len(s):
                            break
                        m += 1
                        r = rx.search(s, m)
                        if r is None:
                            break
                        m, ln = r[0], r[1] - r[0]
                if found is None:
                    continue
                m, ln = found
            if best is None or m < best[0] or (m == best[0] and ln > best[1]):
                best = (m, ln)
        return best


# --------------------------------------------------------------------------- the program

class Grep:
    def __init__(self, o):
        self.o = o
        self.out = []
        self.used = False
        self.errseen = False

    def w(self, s):
        self.out.append(s)

    def err(self, msg):
        if not self.o["s"]:
            sys.stderr.write("grep: " + msg + "\n")

    def run_file(self, name, data, size_known, size):
        o = self.o
        eol = "\0" if o["z"] else "\n"
        self.filename = o["label"] if name == "-" else name
        count_matches, done_on_match, out_quiet = o["count"], o["done_on_match"], o["out_quiet"]
        if eol == "\n" and o["binary_files"] != "text" and "\0" in data:
            if o["binary_files"] == "without-match":
                return 0
            if not count_matches:
                done_on_match = out_quiet = True
            data = data.replace("\0", eol)
            binary = True
        else:
            binary = False
        lines = data.split(eol)
        if lines and lines[-1] == "":
            lines.pop()
        self.eol = eol
        # line offsets
        offs = []
        pos = 0
        for ln in lines:
            offs.append(pos)
            pos += len(ln) + 1
        self.offset_width = 0
        if o["T"]:
            num = size if size_known else INTMAX
            if o["n"] and num < INTMAX:
                num += 1
            self.offset_width = len(str(num))
        outleft = o["max_count"]
        lastout = None
        pending = 0
        nlines = 0
        after = o["after"] if not out_quiet else 0
        n = len(lines)
        i = 0
        while i < n:
            if outleft <= 0 or (done_on_match and nlines > 0):
                break
            sel = self.m.line_matches(lines[i]) != o["v"]
            if not sel:
                i += 1
                continue
            # prtext for line i
            if not out_quiet and pending > 0:
                start = lastout if lastout is not None else 0
                while pending > 0 and start < i:
                    self.prline(lines, offs, start, "-")
                    start += 1
                    pending -= 1
                    lastout = start
            if not out_quiet:
                bp = lastout if lastout is not None else 0
                p = i
                for _ in range(max(0, o["before"])):
                    if p > bp:
                        p -= 1
                if (o["before"] >= 0 or o["after"] >= 0) and not o["o"] and self.used and p != lastout and o["group_sep"] is not None:
                    self.w(o["group_sep"] + "\n")
                while p < i:
                    self.prline(lines, offs, p, "-")
                    p += 1
                self.prline(lines, offs, i, ":")
            lastout = i + 1
            pending = 0 if out_quiet else max(0, o["after"])
            self.used = True
            outleft -= 1
            nlines += 1
            if o["q"]:
                raise SystemExit(0)
            i += 1
        if pending and not out_quiet:
            start = lastout if lastout is not None else 0
            while pending > 0 and start < n:
                self.prline(lines, offs, start, "-")
                start += 1
                pending -= 1
        if binary and o["binary_files"] == "binary" and not o["out_quiet"] and nlines > 0:
            if not o["s"]:
                sys.stderr.write("grep: %s: binary file matches\n" % self.filename)
        return nlines

    def head(self, offs_pos, lineno, length, sep):
        o = self.o
        if o["out_file"]:
            self.w(self.filename)
            self.w(sep if o["filename_mask"] else "\0")
        if o["n"]:
            self.w(str(lineno).rjust(self.offset_width))
            self.w(sep)
        if o["b"]:
            self.w(str(offs_pos).rjust(self.offset_width))
            self.w(sep)
        if o["T"] and (o["out_file"] or o["n"] or o["b"]) and length != 0:
            self.w("\t")

    def prline(self, lines, offs, idx, sep):
        o = self.o
        line = lines[idx]
        if not o["o"]:
            self.head(offs[idx], idx + 1, len(line), sep)
        matching = (sep == ":") != o["v"]
        if o["o"] and matching:
            cur = 0
            while cur < len(line) + 1:
                r = self.m.find(line, cur)
                if r is None:
                    break
                b, size = r
                if b == len(line) + 1 or (b == len(line) and size == 0):
                    break
                if size == 0:
                    cur = b + 1
                    continue
                osep = "-" if o["v"] else ":"
                self.head(offs[idx] + b, idx + 1, size, osep)
                self.w(line[b:b + size])
                self.w(self.eol)
                cur = b + size
            return
        if not o["o"]:
            self.w(line + self.eol)


def parse_args(argv):
    o = {"mode": "G", "i": False, "v": False, "w": False, "x": False, "count": False, "l": False, "L": False,
         "max_count": INTMAX, "o": False, "q": False, "s": False, "b": False, "H": None, "label": "(standard input)",
         "n": False, "T": False, "Z": False, "z": False, "after": -1, "before": -1, "context": -1,
         "group_sep": "--", "binary_files": "binary"}
    keys = []
    have_keys = False
    operands = []
    i = 0
    with_arg = set("efmABCdD")

    def num(v, what):
        try:
            k = int(v)
        except ValueError:
            raise Usage("invalid %s" % what)
        if k < 0:
            raise Usage("invalid %s" % what)
        return k

    while i < len(argv):
        a = argv[i]
        if a == "--":
            operands += argv[i + 1:]
            break
        if a.startswith("--") and len(a) > 2:
            name, eq, val = a[2:].partition("=")
            longs_arg = {"regexp": "e", "file": "f", "max-count": "m", "after-context": "A", "before-context": "B",
                         "context": "C", "label": "label", "group-separator": "group-separator",
                         "binary-files": "binary-files"}
            flags = {"extended-regexp": "E", "fixed-strings": "F", "basic-regexp": "G", "ignore-case": "i",
                     "no-ignore-case": "no-i", "invert-match": "v", "word-regexp": "w", "line-regexp": "x",
                     "count": "c", "files-with-matches": "l", "files-without-match": "L", "only-matching": "o",
                     "quiet": "q", "silent": "q", "no-messages": "s", "byte-offset": "b", "with-filename": "H",
                     "no-filename": "h", "line-number": "n", "initial-tab": "T", "null": "Z", "null-data": "z",
                     "text": "a", "no-group-separator": "no-group-separator"}
            if name in longs_arg:
                if not eq:
                    i += 1
                    if i >= len(argv):
                        raise Usage("option requires an argument")
                    val = argv[i]
                apply_opt(o, longs_arg[name], val, keys, num)
                if longs_arg[name] in ("e", "f"):
                    have_keys = True
            elif name in flags:
                apply_opt(o, flags[name], None, keys, num)
            else:
                raise Usage("unrecognized option")
            i += 1
            continue
        if a.startswith("-") and len(a) > 1:
            j = 1
            while j < len(a):
                c = a[j]
                if c.isdigit():
                    k = j
                    while k < len(a) and a[k].isdigit():
                        k += 1
                    o["context"] = int(a[j:k])
                    j = k
                    continue
                if c in with_arg:
                    val = a[j + 1:]
                    if not val:
                        i += 1
                        if i >= len(argv):
                            raise Usage("option requires an argument")
                        val = argv[i]
                    apply_opt(o, c, val, keys, num)
                    if c in "ef":
                        have_keys = True
                    break
                apply_opt(o, c, None, keys, num)
                j += 1
            i += 1
            continue
        operands.append(a)
        i += 1
    return o, keys, have_keys, operands


def apply_opt(o, c, val, keys, num):
    if c == "e":
        keys.extend(val.split("\n"))
    elif c == "f":
        try:
            if val == "-":
                data = sys.stdin.buffer.read().decode("latin-1")
            else:
                with open(val, "rb") as f:
                    data = f.read().decode("latin-1")
        except OSError as e:
            raise Usage("%s: %s" % (val, e.strerror))
        if data.endswith("\n"):
            data = data[:-1]
        if data or False:
            keys.extend(data.split("\n"))
        elif False:
            pass
    elif c == "m":
        o["max_count"] = num(val, "max count")
    elif c in "ABC":
        k = num(val, "context length argument")
        o[{"A": "after", "B": "before", "C": "context"}[c]] = k
    elif c in ("E", "F", "G"):
        if o.get("mode_set") and o["mode"] != c:
            raise Usage("conflicting matchers specified")
        o["mode"] = c
        o["mode_set"] = True
    elif c == "P":
        raise Usage("-P unsupported")
    elif c == "i" or c == "y":
        o["i"] = True
    elif c == "no-i":
        o["i"] = False
    elif c in ("v", "w", "x", "o", "q", "s", "b", "n", "T", "Z", "z"):
        o[c] = True
    elif c == "c":
        o["count"] = True
    elif c == "l":
        o["l"] = True
        o["L"] = False
    elif c == "L":
        o["L"] = True
        o["l"] = False
    elif c == "H":
        o["H"] = True
    elif c == "h":
        o["H"] = False
    elif c == "a":
        o["binary_files"] = "text"
    elif c == "I":
        o["binary_files"] = "without-match"
    elif c == "label":
        o["label"] = val
    elif c == "group-separator":
        o["group_sep"] = val
    elif c == "no-group-separator":
        o["group_sep"] = None
    elif c == "binary-files":
        if val not in ("binary", "text", "without-match"):
            raise Usage("unknown binary-files type")
        o["binary_files"] = val
    elif c in ("d", "D", "r", "R", "U", "u"):
        pass
    else:
        raise Usage("invalid option -- '%s'" % c)


def main(argv):
    stdin_data = None
    try:
        o, keys, have_keys, operands = parse_args(argv)
    except Usage as e:
        sys.stderr.write("grep: %s\n" % e)
        return 2
    if not have_keys:
        if not operands:
            sys.stderr.write("Usage: grep [OPTION]... PATTERNS [FILE]...\n")
            return 2
        pat = operands.pop(0)
        if o["mode"] != "F" and pat.startswith("\\-"):
            pat = pat[1:]
        keys = pat.split("\n")
    # duplicate patterns are dropped
    seen = []
    for k in keys:
        if k not in seen:
            seen.append(k)
    keys = seen
    if have_keys and not keys:
        # no patterns at all (e.g. -f /dev/null): match nothing
        o["v"] = not o["v"]
        o["w"] = o["x"] = False
        keys = [""]
        nokeys = True
    else:
        nokeys = False
    if o["after"] < 0:
        o["after"] = o["context"]
    if o["before"] < 0:
        o["before"] = o["context"]
    list_files = "L" if o["L"] else "l" if o["l"] else None
    if o["q"]:
        list_files = None
    done_on_match = False
    if o["q"] or list_files:
        o["count"] = False
        done_on_match = True
    o["list"] = list_files
    o["done_on_match"] = done_on_match
    o["out_quiet"] = o["count"] or done_on_match
    o["filename_mask"] = not o["Z"]
    if (o["max_count"] == 0 or (nokeys and o["v"] and not o["x"] and not o["w"])) and list_files != "L":
        return 1
    try:
        matcher = Matcher(keys, o["mode"], o["i"], o["w"], o["x"])
    except Usage as e:
        sys.stderr.write("grep: %s\n" % e)
        return 2
    files = operands or ["-"]
    o["out_file"] = o["H"] if o["H"] is not None else len(operands) > 1
    g = Grep(o)
    g.m = matcher
    status = True
    code = None
    try:
        for name in files:
            if name == "-":
                if stdin_data is None:
                    stdin_data = sys.stdin.buffer.read().decode("latin-1")
                    try:
                        st = os.fstat(0)
                        size_known = stat.S_ISREG(st.st_mode)
                        size = st.st_size
                    except OSError:
                        size_known, size = False, 0
                    data = stdin_data
                else:
                    data = ""
            else:
                try:
                    with open(name, "rb") as f:
                        data = f.read().decode("latin-1")
                    size_known, size = True, os.path.getsize(name)
                except OSError as e:
                    g.err("%s: %s" % (name, e.strerror))
                    g.errseen = True
                    continue
            count = g.run_file(name, data, size_known, size)
            if o["count"]:
                if o["out_file"]:
                    g.w(g.filename)
                    g.w(":" if o["filename_mask"] else "\0")
                g.w("%d\n" % count)
            st_ = not count
            if list_files and list_files == ("L" if st_ else "l"):
                g.w(g.filename + ("\n" if o["filename_mask"] else "\0"))
            status = status and st_
    except SystemExit as e:
        code = e.code
    sys.stdout.buffer.write("".join(g.out).encode("latin-1"))
    sys.stdout.flush()
    if code is not None:
        return code
    return 2 if g.errseen else (1 if status else 0)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
