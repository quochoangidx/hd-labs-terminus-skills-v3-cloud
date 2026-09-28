"""pysed: a GNU sed 4.9 replacement in pure Python, for the subset the task lists.

Usage: python3 /app/pysed/sed.py [-n] [-E] [-s] [-e SCRIPT]... [SCRIPT] [input-file]...
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from posixre import Regex  # noqa: E402

SIMPLE_ESCAPES = {"a": "\a", "f": "\f", "n": "\n", "r": "\r", "t": "\t", "v": "\v"}


class Usage(Exception):
    pass


def conv_escapes(text, in_regex):
    """The section 5.8 escapes \\a \\f \\n \\r \\t \\v become their characters; in a regular
    expression \\n is left for the regex parser (it may stand inside a bracket)."""
    out = []
    i = 0
    while i < len(text):
        c = text[i]
        if c == "\\" and i + 1 < len(text):
            n = text[i + 1]
            if n in SIMPLE_ESCAPES and not (in_regex and n == "n"):
                out.append(SIMPLE_ESCAPES[n])
            else:
                out.append(c + n)
            i += 2
        else:
            out.append(c)
            i += 1
    return "".join(out)


# ---------------------------------------------------------------- parsing

class Cmd:
    def __init__(self):
        self.a1 = self.a2 = None
        self.neg = False
        self.name = None
        self.arg = None
        self.range_active = False
        self.range_end = None
        self.orig_a1 = None


class ScriptParser:
    def __init__(self, text, ere):
        self.s = text
        self.i = 0
        self.ere = ere
        self.cmds = []
        self.labels = {}
        self.blocks = []

    def peek(self, k=0):
        j = self.i + k
        return self.s[j] if j < len(self.s) else None

    def skip_ws(self, newlines=True):
        while self.peek() is not None and (self.peek() in " \t" or (newlines and self.peek() in "\n;")):
            self.i += 1

    def read_delimited(self, delim):
        """A regular expression up to its unescaped delimiter. \\delim stands for delim, a
        backslash-newline for a newline, and a bracket expression may contain the delimiter."""
        out = []
        if delim == "\\":
            # a backslash delimiter cannot be escaped: the field ends at the next backslash
            j = self.s.find("\\", self.i)
            if j < 0:
                raise Usage("unterminated address regex")
            text, self.i = self.s[self.i:j], j + 1
            return text
        while True:
            c = self.peek()
            if c is None:
                raise Usage("unterminated address regex")
            if c == "\\":
                n = self.peek(1)
                if n == delim:
                    out.append(delim)
                elif n == "\n":
                    out.append("\n")
                else:
                    out.append(c + (n or ""))
                self.i += 2
                continue
            if c == delim:
                self.i += 1
                return "".join(out)
            if c == "[" and delim != "[":
                j = self.i + 1
                if j < len(self.s) and self.s[j] == "^":
                    j += 1
                if j < len(self.s) and self.s[j] == "]":
                    j += 1
                while j < len(self.s) and self.s[j] not in "]\n":
                    if self.s[j] == "[" and j + 1 < len(self.s) and self.s[j + 1] == ":":
                        end = self.s.find(":]", j + 2)
                        j = end + 2 if end >= 0 else j + 1
                        continue
                    j += 1
                if j < len(self.s) and self.s[j] == "]":
                    out.append(self.s[self.i:j + 1])
                    self.i = j + 1
                    continue
            out.append(c)
            self.i += 1

    def make_regex(self, src):
        if src == "":
            return None  # the empty regex: the last regex used
        return Regex(conv_escapes(src, True), self.ere)

    def address(self):
        c = self.peek()
        if c is None:
            return None
        if c.isdigit():
            first = self.number()
            if self.peek() == "~":
                self.i += 1
                return ("step", first, self.number())
            return ("line", first)
        if c == "$":
            self.i += 1
            return ("last",)
        if c == "/" or c == "\\":
            self.i += 1
            delim = "/"
            if c == "\\":
                delim = self.peek()
                self.i += 1
            src = self.read_delimited(delim)
            if self.peek() in ("I", "M"):
                raise Usage("outside the subset: address modifier " + self.peek())
            return ("re", self.make_regex(src))
        return None

    def number(self):
        j = self.i
        while self.peek() is not None and self.peek().isdigit():
            self.i += 1
        return int(self.s[j:self.i] or "0")

    def read_label(self):
        self.skip_ws(newlines=False)
        j = self.i
        while self.peek() is not None and self.peek() not in "\n;":
            self.i += 1
        label = self.s[j:self.i].rstrip(" \t")
        if self.peek() == ";":
            self.i += 1
        return label

    def read_text(self):
        """The text of a, i or c: the one-line form, or the classic form that starts with a
        backslash and a newline. A backslash-newline continues the text on the next line,
        \\X gives X (or the character of a section 5.8 escape)."""
        self.skip_ws(newlines=False)
        if self.peek() == "\\":
            self.i += 1
            if self.peek() == "\n":
                self.i += 1
        out = []
        while self.peek() is not None:
            c = self.peek()
            if c == "\n":
                self.i += 1
                break
            if c == "\\":
                n = self.peek(1)
                if n is None:
                    self.i += 1
                    break
                if n in "cdox":
                    raise Usage("outside the subset: text escape \\" + n)
                out.append(SIMPLE_ESCAPES.get(n, n))
                self.i += 2
                continue
            out.append(c)
            self.i += 1
        return "".join(out)

    def end_of_cmd(self):
        self.skip_ws(newlines=False)
        c = self.peek()
        if c == "#":
            while self.peek() is not None and self.peek() != "\n":
                self.i += 1
        elif c in ("\n", ";"):
            self.i += 1
        elif c is not None and c != "}":
            raise Usage(f"extra characters after command: {self.s[self.i:self.i + 10]!r}")

    def parse(self):
        while True:
            self.skip_ws()
            c = self.peek()
            if c is None:
                break
            if c == "#":
                while self.peek() is not None and self.peek() != "\n":
                    self.i += 1
                continue
            cmd = Cmd()
            cmd.a1 = self.address()
            if cmd.a1 is not None:
                self.skip_ws(newlines=False)
                if self.peek() == ",":
                    self.i += 1
                    self.skip_ws(newlines=False)
                    if self.peek() in ("+", "~"):
                        kind = "plus" if self.peek() == "+" else "mult"
                        self.i += 1
                        cmd.a2 = (kind, self.number())
                    else:
                        cmd.a2 = self.address()
            if cmd.a1 == ("line", 0) and (cmd.a2 is None or cmd.a2[0] != "re"):
                raise Usage("invalid usage of line address 0")
            self.skip_ws(newlines=False)
            while self.peek() == "!":
                cmd.neg = True
                self.i += 1
                self.skip_ws(newlines=False)
            name = self.peek()
            if name is None:
                raise Usage("missing command")
            self.i += 1
            cmd.name = name
            if name == "{":
                self.blocks.append(len(self.cmds))
            elif name == "}":
                self.cmds[self.blocks.pop()].arg = len(self.cmds) + 1
                self.end_of_cmd()
            elif name in "aic":
                cmd.arg = self.read_text()
            elif name == ":":
                cmd.arg = self.read_label()
                self.labels[cmd.arg] = len(self.cmds)
            elif name in "btT":
                cmd.arg = self.read_label()
            elif name in "qQ":
                if cmd.a2 is not None:
                    raise Usage("command only uses one address")
                self.skip_ws(newlines=False)
                cmd.arg = self.number() if self.peek() is not None and self.peek().isdigit() else 0
                self.end_of_cmd()
            elif name == "s":
                delim = self.peek()
                if delim == "\\":
                    raise Usage("backslash is kept for escapes")
                self.i += 1
                pat = self.read_delimited(delim)
                rep = self.read_repl(delim)
                flags = {"g": False, "p": False, "n": 1}
                num = ""
                while self.peek() is not None and self.peek() in "gp0123456789":
                    f = self.peek()
                    self.i += 1
                    if f.isdigit():
                        num += f
                    else:
                        flags[f] = True
                if self.peek() in ("i", "I", "m", "M", "e", "w"):
                    raise Usage("outside the subset: s flag " + self.peek())
                if num:
                    flags["n"] = int(num)
                cmd.arg = (self.make_regex(pat), rep, flags)
                self.end_of_cmd()
            elif name in "=dDgGhHnNpPxz":
                self.end_of_cmd()
            else:
                raise Usage(f"outside the subset: command {name!r}")
            self.cmds.append(cmd)
        if self.blocks:
            raise Usage("unmatched {")
        return self.cmds, self.labels

    def read_repl(self, delim):
        """The replacement as a list of literal strings and ("grp", n) items (n = 0 for &)."""
        items = []
        lit = []
        while True:
            c = self.peek()
            if c is None:
                raise Usage("unterminated s command")
            self.i += 1
            if c == delim:
                break
            if c == "\\":
                n = self.peek()
                self.i += 1
                if n is None:
                    raise Usage("unterminated s command")
                if n.isdigit():
                    items.append("".join(lit))
                    lit = []
                    items.append(("grp", int(n)))
                elif n in "LUluEdoxc":
                    raise Usage("outside the subset: replacement escape \\" + n)
                elif n == delim or n == "&":
                    lit.append(n)
                else:
                    lit.append(SIMPLE_ESCAPES.get(n, n))
            elif c == "&":
                items.append("".join(lit))
                lit = []
                items.append(("grp", 0))
            else:
                lit.append(c)
        items.append("".join(lit))
        return [x for x in items if x != ""]


# ---------------------------------------------------------------- execution

class Input:
    """The input lines of every file in order, with the file boundaries kept so that -s can
    number lines, find $ and end n/N per file. Files are opened one at a time, only when the
    next line is needed or when $ or n/N asks whether any input is left, as GNU sed does: a
    file that is never reached (after q, say) is never opened, so a missing one cannot change
    the exit status."""

    def __init__(self, names, separate):
        self.separate = separate
        self.names = list(names)
        self.opened = 0
        self.status = 0
        self.lines = []
        self.pos = 0
        self.line_no = 0
        self.file_bounds = []

    def open_next(self):
        name = self.names[self.opened]
        self.opened += 1
        try:
            if name == "-":
                data = sys.stdin.buffer.read().decode("latin-1")
            else:
                with open(name, "rb") as handle:
                    data = handle.read().decode("latin-1")
        except OSError as exc:
            sys.stderr.write(f"sed: can't read {name}: {exc.strerror}\n")
            self.status = 2
            return
        parts = data.split("\n")
        if parts and parts[-1] == "":
            parts.pop()
        start = len(self.lines)
        self.lines.extend(parts)
        self.file_bounds.append((start, len(self.lines)))

    def has_next(self):
        while self.pos >= len(self.lines) and self.opened < len(self.names):
            self.open_next()
        return self.pos < len(self.lines)

    def has_next_here(self):
        """Is there a next line for n/N? Under -s the current file's last line has none."""
        if self.separate:
            return not self.is_last() and self.has_next()
        return self.has_next()

    def starts_file(self):
        """Does the next line start a new file? (Only asked under -s.)"""
        return any(self.pos == start for start, end in self.file_bounds if start != end)

    def next(self):
        line = self.lines[self.pos]
        self.pos += 1
        self.line_no += 1
        return line

    def is_last(self):
        """Is the line just read the last one ($)?"""
        if self.separate:
            for start, end in self.file_bounds:
                if start < self.pos <= end:
                    return self.pos == end
            return True
        return not self.has_next()


class Sed:
    def __init__(self, cmds, labels, quiet, out):
        self.cmds, self.labels, self.quiet, self.out = cmds, labels, quiet, out
        self.last_regex = None
        self.inp = None

    def regex(self, r):
        if r is None:
            if self.last_regex is None:
                raise Usage("no previous regular expression")
            return self.last_regex
        self.last_regex = r
        return r

    def match_addr(self, a, ps):
        kind = a[0]
        if kind == "line":
            return self.inp.line_no == a[1]
        if kind == "last":
            return self.inp.is_last()
        if kind == "step":
            first, step = a[1], a[2]
            if step <= 0:
                return self.inp.line_no == first
            return self.inp.line_no >= first and (self.inp.line_no - first) % step == 0
        return self.regex(a[1]).search(ps) is not None

    def selected(self, cmd, ps):
        if cmd.a1 is None:
            return True
        if cmd.a2 is None:
            return self.match_addr(cmd.a1, ps)
        ln = self.inp.line_no
        if cmd.range_active:
            kind = cmd.a2[0]
            if kind == "line":
                if ln > cmd.a2[1]:
                    cmd.range_active = False
                    return self.match_first(cmd, ps)
                end = ln >= cmd.a2[1]
            elif kind in ("plus", "mult"):
                end = ln >= cmd.range_end
            elif kind == "last":
                end = self.inp.is_last()
            else:
                end = self.regex(cmd.a2[1]).search(ps) is not None
            if end:
                cmd.range_active = False
            return True
        return self.match_first(cmd, ps)

    def match_first(self, cmd, ps):
        ln = self.inp.line_no
        if cmd.a1[0] == "never":
            return False
        if cmd.a1[0] == "line":
            if cmd.a1[1] == 0:
                # 0,/re/: the end regex is tried on the very first line
                cmd.orig_a1, cmd.a1 = cmd.a1, ("never",)
                cmd.range_active = self.regex(cmd.a2[1]).search(ps) is None
                return True
            if ln < cmd.a1[1]:
                return False
            # a range whose first address is a number starts at the first line at or past it
            cmd.orig_a1, cmd.a1 = cmd.a1, ("never",)
        elif not self.match_addr(cmd.a1, ps):
            return False
        kind = cmd.a2[0]
        if kind == "line":
            cmd.range_active = cmd.a2[1] > ln
        elif kind == "plus":
            cmd.range_end = ln + cmd.a2[1]
            cmd.range_active = cmd.a2[1] > 0
        elif kind == "mult":
            # the range runs to the next line after addr1 whose number is a multiple of N
            m = cmd.a2[1]
            cmd.range_end = (ln // m + 1) * m if m > 0 else ln
            cmd.range_active = m > 0
        elif kind == "last":
            cmd.range_active = not self.inp.is_last()
        else:
            cmd.range_active = True
        return True

    def emit(self, text):
        self.out.append(text)

    def flush(self, queue):
        for text in queue:
            self.emit(text)
        queue.clear()

    def run(self, inp):
        self.inp = inp
        hold = ""
        append_queue = []
        ps = ""
        tflag = False
        restart = False  # D: run the next cycle without reading a new line
        while True:
            if not restart:
                if not inp.has_next():
                    break
                if inp.separate and inp.starts_file() and inp.pos > 0:
                    # GNU sed 4.9 (checked against the binary): with -s every file starts with
                    # line 1, an empty hold space and every range closed
                    inp.line_no = 0
                    hold = ""
                    for c in self.cmds:
                        c.range_active = False
                        if c.orig_a1 is not None:
                            c.a1 = c.orig_a1
                ps = inp.next()
                tflag = False  # a new line of input resets the t flag
            restart = False
            pc = 0
            quit_code = None
            deleted = False
            while pc < len(self.cmds):
                cmd = self.cmds[pc]
                name = cmd.name
                if name == "}":
                    pc += 1
                    continue
                sel = self.selected(cmd, ps) != cmd.neg
                if not sel:
                    pc = cmd.arg if name == "{" else pc + 1
                    continue
                pc += 1
                if name in "{:":
                    continue
                if name == "=":
                    self.emit(f"{inp.line_no}\n")
                elif name == "a":
                    append_queue.append(cmd.arg + "\n")
                elif name == "i":
                    self.emit(cmd.arg + "\n")
                elif name == "c":
                    # over a range the text is printed once, when the range ends; a range still
                    # open when the input ends prints nothing (GNU sed 4.9, checked on the binary)
                    if cmd.a2 is None or not cmd.range_active or cmd.neg:
                        self.emit(cmd.arg + "\n")
                    deleted = True
                    break
                elif name == "d":
                    deleted = True
                    break
                elif name == "D":
                    if "\n" not in ps:
                        deleted = True
                        break
                    ps = ps[ps.index("\n") + 1:]
                    restart = True  # the t flag carries over: no new line was read
                    break
                elif name == "g":
                    ps = hold
                elif name == "G":
                    ps = ps + "\n" + hold
                elif name == "h":
                    hold = ps
                elif name == "H":
                    hold = hold + "\n" + ps
                elif name == "x":
                    ps, hold = hold, ps
                elif name in "nN":
                    if not inp.has_next_here():
                        # no next line (under -s: in this file): the cycle ends with the usual
                        # autoprint and the rest of the script is skipped; later files still run
                        break
                    if name == "n":
                        if not self.quiet:
                            self.emit(ps + "\n")
                        self.flush(append_queue)
                        ps = inp.next()
                    else:
                        self.flush(append_queue)
                        ps = ps + "\n" + inp.next()
                    tflag = False
                elif name == "p":
                    self.emit(ps + "\n")
                elif name == "P":
                    self.emit(ps.split("\n", 1)[0] + "\n")
                elif name == "q":
                    quit_code = cmd.arg
                    break
                elif name == "Q":
                    return cmd.arg
                elif name == "s":
                    regex, rep, flags = cmd.arg
                    new, changed = substitute(self.regex(regex), rep, flags, ps)
                    if changed:
                        ps = new
                        tflag = True
                        if flags["p"]:
                            self.emit(ps + "\n")
                elif name == "b":
                    pc = self.labels[cmd.arg] if cmd.arg else len(self.cmds)
                elif name == "t":
                    if tflag:
                        tflag = False
                        pc = self.labels[cmd.arg] if cmd.arg else len(self.cmds)
                elif name == "T":
                    if not tflag:
                        pc = self.labels[cmd.arg] if cmd.arg else len(self.cmds)
                    tflag = False  # GNU sed 4.9 also resets the flag when T does not branch
                elif name == "z":
                    ps = ""
            if restart:
                continue  # text queued by a stays queued across a D restart
            if not deleted and not self.quiet:
                self.emit(ps + "\n")
            self.flush(append_queue)
            if quit_code is not None:
                return quit_code
        return 0


def substitute(regex, rep, flags, ps):
    out = []
    pos = 0
    count = 0
    changed = False
    search_at = 0
    prev_end = -1
    while search_at <= len(ps):
        m = regex.search(ps, search_at)
        if m is None:
            break
        b, e, caps = m
        if b == e and b == prev_end:
            # an empty match right after the previous match does not count
            if b >= len(ps):
                break
            search_at = b + 1
            continue
        count += 1
        if count >= flags["n"]:
            out.append(ps[pos:b])
            out.append(expand(rep, ps, b, e, caps))
            pos = e
            changed = True
            if not flags["g"]:
                break
        prev_end = e
        search_at = e + 1 if e == b else e
    out.append(ps[pos:])
    return "".join(out), changed


def expand(rep, ps, b, e, caps):
    parts = []
    for item in rep:
        if isinstance(item, str):
            parts.append(item)
        elif item[1] == 0:
            parts.append(ps[b:e])
        else:
            span = caps[item[1]] if item[1] < len(caps) else None
            parts.append(ps[span[0]:span[1]] if span else "")
    return "".join(parts)


def main(argv):
    quiet = ere = separate = False
    scripts = []
    files = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "-n":
            quiet = True
        elif a == "-E":
            ere = True
        elif a == "-s":
            separate = True
        elif a == "-e":
            i += 1
            if i >= len(argv):
                sys.stderr.write("sed: option requires an argument -- 'e'\n")
                return 1
            scripts.append(argv[i])
        elif a.startswith("-") and a != "-":
            sys.stderr.write(f"sed: unknown option {a}\n")
            return 1
        else:
            files.append(a)
        i += 1
    if not scripts:
        if not files:
            sys.stderr.write("Usage: sed [OPTION]... {script-only-if-no-other-script} [input-file]...\n")
            return 1
        scripts.append(files.pop(0))
    text = "\n".join(scripts)
    if text.startswith("#n"):
        quiet = True
    try:
        cmds, labels = ScriptParser(text, ere).parse()
    except Exception as exc:  # an invalid script
        sys.stderr.write(f"sed: -e expression #1: {exc}\n")
        return 1
    out = []
    inp = Input(files or ["-"], separate)
    code = Sed(cmds, labels, quiet, out).run(inp)
    sys.stdout.buffer.write("".join(out).encode("latin-1"))
    return inp.status or code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
