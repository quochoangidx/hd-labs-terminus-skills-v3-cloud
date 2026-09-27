"""pysed: a GNU sed 4.9 replacement in pure Python.

Usage: python3 /app/pysed/sed.py [OPTION]... {script-only-if-no-other-script} [input-file]...
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from posixre import Regex  # noqa: E402


class Usage(Exception):
    pass


GNU_NUMERIC_RANGE_START = True  # a range whose first address is a line number starts at the first line reached at or past it


# ---------------------------------------------------------------- escapes

def conv_escapes(text, in_regex):
    """GNU sed's processing of \\n, \\t, \\dNNN, \\oNNN, \\xHH, \\cX before use."""
    out = []
    i = 0
    simple = {"a": "\a", "f": "\f", "n": "\n", "r": "\r", "t": "\t", "v": "\v"}
    while i < len(text):
        c = text[i]
        if c != "\\" or i + 1 >= len(text):
            out.append(c)
            i += 1
            continue
        n = text[i + 1]
        if n in simple and not (in_regex and n == "n"):
            out.append(simple[n])
            i += 2
        elif n in "dox":
            digits = {"d": "0123456789", "o": "01234567", "x": "0123456789abcdefABCDEF"}[n]
            width = 2 if n == "x" else 3
            j = i + 2
            while j < len(text) and j < i + 2 + width and text[j] in digits:
                j += 1
            if j == i + 2:
                out.append(c + n)
                i += 2
                continue
            ch = chr(int(text[i + 2:j], {"d": 10, "o": 8, "x": 16}[n]) & 0xFF)
            out.append(("\\" + ch) if in_regex and ch in "\\^$.*[]+?(){}|" else ch)
            i = j
        elif n == "c" and i + 2 < len(text):
            out.append(chr(ord(text[i + 2].upper()) ^ 0x40))
            i += 3
        else:
            out.append(c + n)
            i += 2
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


class ScriptParser:
    def __init__(self, text, ere):
        self.s = text
        self.i = 0
        self.ere = ere
        self.cmds = []
        self.labels = {}
        self.blocks = []
        self.last_regex = None

    def peek(self, k=0):
        j = self.i + k
        return self.s[j] if j < len(self.s) else None

    def skip_ws(self, newlines=True):
        while self.peek() is not None and (self.peek() in " \t" or (newlines and self.peek() in "\n;")):
            self.i += 1

    def read_delimited(self, delim):
        """Text up to an unescaped delimiter; \\delim becomes delim; newline via \\n kept."""
        out = []
        while True:
            c = self.peek()
            if c is None:
                raise Usage("unterminated")
            if c == "\\":
                n = self.peek(1)
                if n == delim:
                    out.append(delim if delim not in "\\" else "\\\\")
                    self.i += 2
                    continue
                if n == "\n":
                    out.append("\n")
                    self.i += 2
                    continue
                out.append(c + (n or ""))
                self.i += 2
                continue
            if c == delim:
                self.i += 1
                return "".join(out)
            if c == "[" and delim != "[":
                # bracket expressions may contain the delimiter
                j = self.i + 1
                if j < len(self.s) and self.s[j] == "^":
                    j += 1
                if j < len(self.s) and self.s[j] == "]":
                    j += 1
                while j < len(self.s) and self.s[j] != "]":
                    if self.s[j] == "[" and j + 1 < len(self.s) and self.s[j + 1] in ":=.":
                        end = self.s.find(self.s[j + 1] + "]", j + 2)
                        j = end + 2 if end >= 0 else j + 1
                        continue
                    if self.s[j] == "\n":
                        break
                    j += 1
                if j < len(self.s) and self.s[j] == "]":
                    out.append(self.s[self.i:j + 1])
                    self.i = j + 1
                    continue
            out.append(c)
            self.i += 1

    def regex_flags(self):
        icase = multi = False
        while self.peek() in ("I", "M"):
            if self.peek() == "I":
                icase = True
            else:
                multi = True
            self.i += 1
        return icase, multi

    def make_regex(self, src, icase, multi):
        if src == "":
            return None  # empty regex: the last regex used
        return Regex(conv_escapes(src, True), self.ere, icase, multi)

    def address(self):
        c = self.peek()
        if c is None:
            return None
        if c.isdigit():
            j = self.i
            while self.peek() is not None and self.peek().isdigit():
                self.i += 1
            first = int(self.s[j:self.i])
            if self.peek() == "~":
                self.i += 1
                k = self.i
                while self.peek() is not None and self.peek().isdigit():
                    self.i += 1
                step = int(self.s[k:self.i] or "0")
                return ("step", first, step)
            return ("line", first)
        if c == "$":
            self.i += 1
            return ("last",)
        if c == "/" or c == "\\":
            if c == "\\":
                self.i += 1
                delim = self.peek()
                self.i += 1
            else:
                delim = "/"
                self.i += 1
            src = self.read_delimited(delim)
            icase, multi = self.regex_flags()
            return ("re", self.make_regex(src, icase, multi))
        return None

    def read_label(self):
        self.skip_ws(newlines=False)
        j = self.i
        while self.peek() is not None and self.peek() not in "\n;":
            self.i += 1
        return self.s[j:self.i].rstrip(" \t")

    def read_text(self):
        """Text argument of a, i, c (one-line GNU form or classic backslash form)."""
        self.skip_ws(newlines=False)
        if self.peek() == "\\":
            self.i += 1
            if self.peek() == "\n":
                self.i += 1
        out = []
        while self.peek() is not None:
            c = self.peek()
            if c == "\\":
                n = self.peek(1)
                if n is None:
                    self.i += 1
                    break
                if n == "\n":
                    out.append("\n")
                    self.i += 2
                    continue
                conv = conv_escapes(self.s[self.i:self.i + 5], False)
                if conv != self.s[self.i:self.i + 5] and n in "afnrtvdoxc":
                    # consume exactly the escape that conv_escapes converted
                    for width in (2, 3, 4, 5):
                        piece = self.s[self.i:self.i + width]
                        if conv_escapes(piece, False) != piece and len(conv_escapes(piece, False)) == 1:
                            best = width
                    out.append(conv_escapes(self.s[self.i:self.i + best], False))
                    self.i += best
                    continue
                out.append(n)
                self.i += 2
                continue
            if c == "\n":
                self.i += 1
                break
            out.append(c)
            self.i += 1
        return conv_escapes_text("".join(out))

    def end_of_cmd(self):
        self.skip_ws(newlines=False)
        c = self.peek()
        if c == "#":
            while self.peek() is not None and self.peek() != "\n":
                self.i += 1
            return
        if c in (None, "\n", ";"):
            if c is not None:
                self.i += 1
            return
        if c == "}":
            return
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
                    if self.peek() == "+" or self.peek() == "~":
                        kind = "plus" if self.peek() == "+" else "mult"
                        self.i += 1
                        j = self.i
                        while self.peek() is not None and self.peek().isdigit():
                            self.i += 1
                        cmd.a2 = (kind, int(self.s[j:self.i]))
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
                self.cmds.append(cmd)
                continue
            if name == "}":
                start = self.blocks.pop()
                self.cmds[start].arg = len(self.cmds) + 1
                self.cmds.append(cmd)
                self.end_of_cmd()
                continue
            if name in "aic":
                cmd.arg = self.read_text()
            elif name == ":":
                label = self.read_label()
                self.labels[label] = len(self.cmds)
                if self.peek() == ";":
                    self.i += 1
                cmd.arg = label
            elif name in "btT":
                cmd.arg = self.read_label()
                if self.peek() == ";":
                    self.i += 1
            elif name in "qQlL":
                self.skip_ws(newlines=False)
                j = self.i
                while self.peek() is not None and self.peek().isdigit():
                    self.i += 1
                cmd.arg = int(self.s[j:self.i]) if self.i > j else None
                self.end_of_cmd()
            elif name == "s":
                delim = self.peek()
                self.i += 1
                pat = self.read_delimited(delim)
                rep = self.read_repl(delim)
                flags = {"g": False, "p": False, "n": 1, "i": False, "m": False}
                num = ""
                while self.peek() is not None and self.peek() in "gpiImM0123456789":
                    f = self.peek()
                    self.i += 1
                    if f.isdigit():
                        num += f
                    elif f == "g":
                        flags["g"] = True
                    elif f == "p":
                        flags["p"] = True
                    elif f in "iI":
                        flags["i"] = True
                    else:
                        flags["m"] = True
                if num:
                    flags["n"] = int(num)
                cmd.arg = (self.make_regex(pat, flags["i"], flags["m"]), rep, flags)
                self.end_of_cmd()
            elif name == "y":
                delim = self.peek()
                self.i += 1
                src = y_text(self.read_delimited(delim))
                dst = y_text(self.read_delimited(delim))
                if len(src) != len(dst):
                    raise Usage("y lengths differ")
                cmd.arg = dict(zip(src, dst))
                self.end_of_cmd()
            else:
                if name not in "=dDgGhHnNpPxz":
                    raise Usage(f"unknown command {name!r}")
                self.end_of_cmd()
            self.cmds.append(cmd)
        if self.blocks:
            raise Usage("unmatched {")
        return self.cmds, self.labels

    def read_repl(self, delim):
        """Replacement: list of literal strings and ('grp', n) / ('case', x) items."""
        items = []
        lit = []
        while True:
            c = self.peek()
            if c is None:
                raise Usage("unterminated s")
            self.i += 1
            if c == delim:
                break
            if c == "\\":
                n = self.peek()
                self.i += 1
                if n == delim:
                    lit.append(n)
                elif n is not None and n.isdigit():
                    items.append("".join(lit))
                    lit = []
                    items.append(("grp", int(n)))
                elif n == "&":
                    lit.append("&")
                elif n in ("L", "U", "l", "u", "E"):
                    items.append("".join(lit))
                    lit = []
                    items.append(("case", n))
                elif n == "\n":
                    lit.append("\n")
                elif n == "n":
                    lit.append("\n")
                else:
                    lit.append(conv_escapes("\\" + n, False) if n in "atfrvdoxc" else n)
                    if n in "doxc":
                        # re-read numeric escapes properly
                        lit.pop()
                        start = self.i - 2
                        width = {"d": 5, "o": 5, "x": 4, "c": 3}[n]
                        chunk = self.s[start:start + width]
                        conv = conv_escapes(chunk, False)
                        if conv != chunk:
                            lit.append(conv)
                            self.i = start + width
                        else:
                            lit.append(n)
            elif c == "&":
                items.append("".join(lit))
                lit = []
                items.append(("grp", 0))
            else:
                lit.append(c)
        items.append("".join(lit))
        return [x for x in items if x != ""]


def conv_escapes_text(t):
    return t


def y_text(t):
    """y lists: \\\\ is a backslash, the escapes of conv_escapes are decoded, any other \\X is X."""
    out = []
    i = 0
    while i < len(t):
        c = t[i]
        if c == "\\" and i + 1 < len(t):
            n = t[i + 1]
            if n in "afnrtvdoxc":
                for width in (5, 4, 3, 2):
                    piece = t[i:i + width]
                    conv = conv_escapes(piece, False)
                    if len(piece) == width and conv != piece and len(conv) == 1:
                        out.append(conv)
                        i += width
                        break
                else:
                    out.append(n)
                    i += 2
                continue
            out.append(n)
            i += 2
        else:
            out.append(c)
            i += 1
    return "".join(out)


# ---------------------------------------------------------------- execution

class Input:
    def __init__(self, sources, separate):
        self.sources = sources
        self.separate = separate
        self.lines = []
        self.pos = 0
        self.file_index = -1
        self.line_no = 0
        self.file_bounds = []
        self.new_file = False
        for data in sources:
            parts = data.split("\n")
            if parts and parts[-1] == "":
                parts.pop()
            start = len(self.lines)
            self.lines.extend(parts)
            self.file_bounds.append((start, len(self.lines)))

    def has_next(self):
        return self.pos < len(self.lines)

    def has_next_here(self):
        """Is there a next line for n/N? Under -s the current file's last line has none."""
        if self.separate and self.has_next():
            return not self.is_last()
        return self.has_next()

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
        return self.pos >= len(self.lines)

    def reset_line_no_if_new_file(self):
        if self.separate:
            for start, end in self.file_bounds:
                if self.pos == start and start != end:
                    self.line_no = 0
                    self.new_file = True


class Sed:
    def __init__(self, cmds, labels, quiet, out):
        self.cmds, self.labels, self.quiet, self.out = cmds, labels, quiet, out
        self.last_regex = None

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
        if kind == "re":
            return self.regex(a[1]).search(ps) is not None
        raise AssertionError(kind)

    def selected(self, cmd, ps):
        if cmd.a1 is None:
            return True
        if cmd.a2 is None:
            return self.match_addr(cmd.a1, ps)
        ln = self.inp.line_no
        if cmd.range_active:
            kind = cmd.a2[0]
            if kind == "line":
                end = ln >= cmd.a2[1]
                if ln > cmd.a2[1]:
                    cmd.range_active = False
                    return self.match_first(cmd, ps)
            elif kind == "plus":
                end = ln >= cmd.range_end
            elif kind == "mult":
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
        if cmd.a1[0] == "line" and cmd.a1[1] == 0:
            # 0,/re/: the end regex may match on the very first line
            if cmd.a2[0] == "re":
                cmd.orig_a1 = cmd.a1
                if self.regex(cmd.a2[1]).search(ps) is not None:
                    cmd.a1 = ("never",)
                    return True
                cmd.range_active = True
                cmd.a1 = ("never",)
                return True
            return False
        if cmd.a1[0] == "never":
            return False
        if cmd.a1[0] == "line" and GNU_NUMERIC_RANGE_START:
            if ln < cmd.a1[1]:
                return False
            cmd.orig_a1 = cmd.a1
            cmd.a1 = ("never",)
        elif not self.match_addr(cmd.a1, ps):
            return False
        kind = cmd.a2[0]
        if kind == "line":
            if cmd.a2[1] > ln:
                cmd.range_active = True
        elif kind == "plus":
            if cmd.a2[1] > 0:
                cmd.range_end = ln + cmd.a2[1]
                cmd.range_active = True
        elif kind == "mult":
            # the range runs to the next line after addr1 whose number is a multiple of N
            m = cmd.a2[1]
            if m > 0:
                cmd.range_end = (ln // m + 1) * m
                cmd.range_active = True
        elif kind == "last":
            if not self.inp.is_last():
                cmd.range_active = True
        else:
            cmd.range_active = True
        return True

    def emit(self, text):
        self.out.append(text)

    def run(self, inp):
        self.inp = inp
        hold = ""
        append_queue = []
        exit_code = 0
        ps = None
        restart_without_read = False
        while True:
            if not restart_without_read:
                if not inp.has_next():
                    break
                inp.reset_line_no_if_new_file()
                if inp.new_file:
                    inp.new_file = False
                    if inp.pos > 0:
                        # GNU sed 4.9 (checked against the binary): with -s each file starts with
                        # an empty hold space and every range closed
                        hold = ""
                        for c in self.cmds:
                            c.range_active = False
                            if hasattr(c, "orig_a1"):
                                c.a1 = c.orig_a1
                ps = inp.next()
            restart_without_read = False
            tflag = False if not getattr(self, "_keep_t", False) else self._tflag
            self._keep_t = False
            pc = 0
            quit_now = None
            deleted = False
            while pc < len(self.cmds):
                cmd = self.cmds[pc]
                sel = self.selected(cmd, ps)
                if cmd.neg:
                    sel = not sel
                name = cmd.name
                if name == "}":
                    pc += 1
                    continue
                if not sel:
                    pc = cmd.arg if name == "{" else pc + 1
                    continue
                pc += 1
                if name == "{":
                    continue
                if name == "=":
                    self.emit(f"{inp.line_no}\n")
                elif name == "a":
                    append_queue.append(cmd.arg + "\n")
                elif name == "i":
                    self.emit(cmd.arg + "\n")
                elif name == "c":
                    # GNU sed 4.9: over a range the text is printed once, when the range ends;
                    # a range still open at end of input prints nothing (both checked on the binary)
                    if cmd.a2 is None or not cmd.range_active or cmd.neg:
                        self.emit(cmd.arg + "\n")
                    deleted = True
                    break
                elif name == "d":
                    deleted = True
                    break
                elif name == "D":
                    if "\n" in ps:
                        ps = ps[ps.index("\n") + 1:]
                        restart_without_read = True
                        # no new input line is read, so the t flag carries over
                        self._keep_t, self._tflag = True, tflag
                        break
                    deleted = True
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
                elif name == "l":
                    self.emit(l_format(ps, 70 if cmd.arg is None else cmd.arg))
                elif name == "n":
                    if not inp.has_next_here():
                        # no next line (under -s: in this file): end the cycle with the usual
                        # autoprint, skipping the rest of the script; later files still run
                        break
                    if not self.quiet:
                        self.emit(ps + "\n")
                    self.flush(append_queue)
                    inp.reset_line_no_if_new_file()
                    ps = inp.next()
                    tflag = False
                elif name == "N":
                    if not inp.has_next_here():
                        break
                    self.flush_before_N(append_queue)
                    inp.reset_line_no_if_new_file()
                    ps = ps + "\n" + inp.next()
                    tflag = False
                elif name == "p":
                    self.emit(ps + "\n")
                elif name == "P":
                    self.emit(ps.split("\n", 1)[0] + "\n")
                elif name == "q":
                    quit_now = cmd.arg or 0
                    break
                elif name == "Q":
                    return cmd.arg or 0
                elif name == "s":
                    regex, rep, flags = cmd.arg
                    new, changed = substitute(self.regex(regex), rep, flags, ps)
                    if changed:
                        ps = new
                        tflag = True
                        if flags["p"]:
                            self.emit(ps + "\n")
                elif name == "y":
                    ps = "".join(cmd.arg.get(ch, ch) for ch in ps)
                elif name == ":":
                    pass
                elif name == "b":
                    pc = self.labels[cmd.arg] if cmd.arg else len(self.cmds)
                elif name == "t":
                    if tflag:
                        tflag = False
                        pc = self.labels[cmd.arg] if cmd.arg else len(self.cmds)
                elif name == "T":
                    if not tflag:
                        pc = self.labels[cmd.arg] if cmd.arg else len(self.cmds)
                    else:
                        tflag = False  # GNU sed 4.9 also resets the flag when T does not branch
                elif name == "z":
                    ps = ""
            if restart_without_read:
                # GNU keeps text queued by a/r across a D restart until a line is output
                continue
            if not deleted and not self.quiet:
                self.emit(ps + "\n")
            self.flush(append_queue)
            if quit_now is not None:
                return quit_now
        return exit_code

    def flush(self, q):
        for t in q:
            self.emit(t)
        q.clear()

    def flush_before_N(self, q):
        self.flush(q)


def l_format(ps, width):
    esc = {"\\": "\\\\", "\a": "\\a", "\b": "\\b", "\f": "\\f", "\n": "\\n", "\r": "\\r", "\t": "\\t", "\v": "\\v"}
    pieces = []
    for ch in ps:
        if ch in esc:
            pieces.append(esc[ch])
        elif 32 <= ord(ch) < 127:
            pieces.append(ch)
        else:
            pieces.append("\\%03o" % ord(ch))
    out = []
    line = ""
    if width == 1:
        width = 0
    for p in pieces:
        if width > 1 and len(line) + len(p) > width - 1:
            out.append(line + "\\\n")
            line = ""
        line += p
    out.append(line + "$\n")
    return "".join(out)


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
            # an empty match right after the previous match is not allowed
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
        if e == b:
            search_at = e + 1
            if e < len(ps):
                pass
        else:
            search_at = e
    out.append(ps[pos:])
    return "".join(out), changed


def expand(rep, ps, b, e, caps):
    parts = []
    mode = None
    one = None
    for item in rep:
        if isinstance(item, str):
            text = item
        elif item[0] == "grp":
            n = item[1]
            if n == 0:
                text = ps[b:e]
            else:
                span = caps[n] if n < len(caps) else None
                text = ps[span[0]:span[1]] if span else ""
        else:
            x = item[1]
            if x in "LU":
                mode = x
                one = None
            elif x == "E":
                mode = None
                one = None
            else:
                one = x
            continue
        if mode == "L":
            text = text.lower()
        elif mode == "U":
            text = text.upper()
        if one:
            if text:
                text = (text[0].lower() if one == "l" else text[0].upper()) + text[1:]
            one = None
        parts.append(text)
    return "".join(parts)


def main(argv):
    quiet = ere = separate = False
    scripts = []
    files = []
    i = 0
    only_files = False
    while i < len(argv):
        a = argv[i]
        if only_files or not a.startswith("-") or a == "-":
            files.append(a)
        elif a == "--":
            only_files = True
        elif a in ("-n", "--quiet", "--silent"):
            quiet = True
        elif a in ("-E", "-r", "--regexp-extended"):
            ere = True
        elif a in ("-s", "--separate"):
            separate = True
        elif a == "-e":
            i += 1
            scripts.append(argv[i])
        elif a.startswith("--expression="):
            scripts.append(a[len("--expression="):])
        elif a.startswith("-e"):
            scripts.append(a[2:])
        elif len(a) > 2 and a[0] == "-" and a[1] != "-":
            # clustered short options
            for ch in a[1:]:
                if ch == "n":
                    quiet = True
                elif ch in "Er":
                    ere = True
                elif ch == "s":
                    separate = True
                else:
                    sys.stderr.write(f"sed: invalid option -- '{ch}'\n")
                    return 1
        else:
            sys.stderr.write(f"sed: unknown option {a}\n")
            return 1
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
    except Exception as exc:  # invalid script
        sys.stderr.write(f"sed: -e expression #1: {exc}\n")
        return 1
    sources = []
    status = 0
    if not files:
        files = ["-"]
    for f in files:
        try:
            if f == "-":
                sources.append(sys.stdin.buffer.read().decode("latin-1"))
            else:
                with open(f, "rb") as h:
                    sources.append(h.read().decode("latin-1"))
        except OSError as exc:
            sys.stderr.write(f"sed: can't read {f}: {exc.strerror}\n")
            status = 2
    out = []
    code = Sed(cmds, labels, quiet, out).run(Input(sources, separate))
    sys.stdout.buffer.write("".join(out).encode("latin-1"))
    return status or code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
