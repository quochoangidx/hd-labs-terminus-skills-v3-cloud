"""pyed: a GNU ed 1.19 replacement in pure Python.

Usage: python3 /app/pyed/ed.py [OPTIONS] [FILE]
"""

import os
import stat
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from posixre import Regex, RegexError  # noqa: E402

QUIT, ERR, EMOD, FATAL = -1, -2, -3, -4
PF_L, PF_N, PF_P = 1, 2, 4
UADD, UDEL, UMOV, VMOV = 0, 1, 2, 3
INV_COM_SUF = "Invalid command suffix"
NO_PREV_SUBST = "No previous substitution"


class Line:
    __slots__ = ("text", "prev", "next")

    def __init__(self, text=""):
        self.text = text
        # True for a line that came from a binary file with no final newline: ed
        # writes such a line back without one, as the manual's Limitations say.
        self.prev = self.next = self


def link(prev, nxt):
    prev.next = nxt
    nxt.prev = prev


def insert_node(lp, prev):
    link(lp, prev.next)
    link(prev, lp)


class Undo:
    __slots__ = ("type", "head", "tail")

    def __init__(self, t, head, tail):
        self.type, self.head, self.tail = t, head, tail


class Cmd:
    """A command buffer: text plus a read position (the C code's ibufp)."""

    def __init__(self, text):
        self.s = text
        self.i = 0

    def ch(self, k=0):
        j = self.i + k
        return self.s[j] if j < len(self.s) else "\0"


class Ed:
    def __init__(self, data, opts):
        self.stdin = data
        self.sin = 0
        self.out = []
        self.ere = opts["E"]
        self.trad = opts["G"]
        self.quiet = opts["q"]
        self.restricted_ = opts["r"]
        self.scripted = opts["s"]
        self.verbose = opts["v"]
        self.prompt_str = "*"
        self.prompt_on = False
        if opts["p"] is not None:
            self.prompt_str = opts["p"]
            self.prompt_on = True
        self.errmsg = ""
        self.def_filename = ""
        self.first_addr = self.second_addr = 0
        self.head = Line()
        self.yank = Line()
        self.current = 0
        self.last = 0
        self.modified = False
        self.marks = [None] * 26
        self.ustack = []
        self.u_current = -1
        self.u_last = -1
        self.u_modified = False
        self.active = []
        self.active_idx = 0
        self.active_idxm = 0
        self.last_regexp = None
        self.subst_regexp = None
        self.rbuf = None
        self.window_lines = 22
        self.window_columns = 72
        self.linenum = 0
        self.snum = 1
        self.s_pflags = 0
        self.pmask = PF_P
        self.isbinary = False
        self.unterminated = None
        try:
            self.interactive = not stat.S_ISREG(os.fstat(0).st_mode)
        except OSError:
            self.interactive = True

    # ---- output and errors -------------------------------------------------
    def write(self, s):
        self.out.append(s)

    def set_error(self, msg):
        self.errmsg = msg[:79]

    def invalid_address(self):
        self.set_error("Invalid address")

    def strerror(self, filename, err):
        if not self.quiet:
            sys.stderr.write((filename + ": " if filename else "") + err + "\n")

    # ---- stdin --------------------------------------------------------------
    def get_stdin_line(self):
        """Return a complete line including its newline, or '' at end of input."""
        j = self.stdin.find("\n", self.sin)
        if j < 0:
            rest = len(self.stdin) - self.sin
            self.sin = len(self.stdin)
            self.set_error("Unexpected end-of-file")
            if rest > 0:
                self.linenum += 1
            return ""
        line = self.stdin[self.sin:j + 1]
        self.sin = j + 1
        self.linenum += 1
        return line

    def get_extended_line(self, cmd, strip):
        """Join continuation lines ending in an odd number of backslashes."""
        s, i = cmd.s, cmd.i
        end = s.index("\n", i) + 1
        line = s[i:end]
        if len(line) < 2 or not trailing_escape(line[:-1]):
            return True
        buf = line[:-2] + "\n"
        if strip:
            buf = buf[:-1]
        while True:
            nxt = self.get_stdin_line()
            if not nxt:
                return False
            buf += nxt
            if len(nxt) < 2 or not trailing_escape(buf[:-1]):
                break
            buf = buf[:-2] + "\n"
            if strip:
                buf = buf[:-1]
        cmd.s = buf + s[end:]
        cmd.i = 0
        return True

    # ---- buffer -------------------------------------------------------------
    def search_line_node(self, addr):
        lp = self.head
        for _ in range(addr):
            lp = lp.next
        return lp

    def get_line_node_addr(self, lp):
        p = self.head
        addr = 0
        while p is not lp:
            p = p.next
            if p is self.head:
                break
            addr += 1
        if addr and p is self.head:
            self.invalid_address()
            return -1
        return addr

    def inc_addr(self, addr):
        addr += 1
        return 0 if addr > self.last else addr

    def dec_addr(self, addr):
        addr -= 1
        return self.last if addr < 0 else addr

    def add_line_node(self, lp):
        prev = self.search_line_node(self.current)
        insert_node(lp, prev)
        self.current += 1
        self.last += 1

    def put_sbuf_line(self, text):
        """Add the line up to the first newline of text; return the rest."""
        j = text.index("\n")
        lp = Line(text[:j])
        self.add_line_node(lp)
        return text[j + 1:]

    def push_undo(self, t, frm, to):
        u = Undo(t, self.search_line_node(frm), self.search_line_node(to))
        self.ustack.append(u)
        return u

    def unterminated_last_line(self):
        return self.unterminated is not None and self.unterminated is self.search_line_node(self.last)

    def clear_undo_stack(self):
        for u in reversed(self.ustack):
            if u.type == UDEL:
                ep = u.tail.next
                bp = u.head
                while bp is not ep:
                    nxt = bp.next
                    self.unmark(bp)
                    if bp is self.unterminated:
                        self.unterminated = None
                    bp = nxt
        self.ustack = []
        self.u_current = self.current
        self.u_last = self.last
        self.u_modified = self.modified

    def reset_undo_state(self):
        self.clear_undo_stack()
        self.u_current = self.u_last = -1
        self.u_modified = False

    def unmark(self, lp):
        for i in range(26):
            if self.marks[i] is lp:
                self.marks[i] = None

    def append_lines(self, cmd, addr, insert, isglobal):
        up = None
        self.current = addr
        while True:
            if not isglobal:
                line = self.get_stdin_line()
                if not line:
                    return True
            else:
                if cmd.i >= len(cmd.s):
                    return True
                j = cmd.s.index("\n", cmd.i) + 1
                line = cmd.s[cmd.i:j]
                cmd.i = j
            if line == ".\n":
                return True
            if insert:
                insert = False
                if self.current > 0:
                    self.current -= 1
            self.put_sbuf_line(line)
            if up:
                up.tail = self.search_line_node(self.current)
            else:
                up = self.push_undo(UADD, self.current, self.current)
            self.modified = True

    def clear_yank(self):
        link(self.yank, self.yank)

    def yank_lines(self, frm, to):
        ep = self.search_line_node(self.inc_addr(to))
        bp = self.search_line_node(frm)
        lp = self.yank
        self.clear_yank()
        while bp is not ep:
            p = Line(bp.text)
            insert_node(p, lp)
            bp = bp.next
            lp = p
        return True

    def copy_lines(self, first, second, addr):
        np = self.search_line_node(first)
        up = None
        n = second - first + 1
        m = 0
        self.current = addr
        if first <= addr < second:
            n = addr - first + 1
            m = second - addr
        while n > 0:
            while n > 0:
                n -= 1
                lp = Line(np.text)
                self.add_line_node(lp)
                if up:
                    up.tail = lp
                else:
                    up = self.push_undo(UADD, self.current, self.current)
                self.modified = True
                np = np.next
            n, m = m, 0
            np = self.search_line_node(self.current + 1)
        return True

    def delete_lines(self, frm, to, isglobal):
        self.yank_lines(frm, to)
        self.push_undo(UDEL, frm, to)
        n = self.search_line_node(self.inc_addr(to))
        p = self.search_line_node(frm - 1)
        if isglobal:
            self.unset_active_nodes(p.next, n)
        link(p, n)
        self.last -= to - frm + 1
        self.current = min(frm, self.last)
        self.modified = True
        return True

    def join_lines(self, frm, to, isglobal):
        ep = self.search_line_node(self.inc_addr(to))
        bp = self.search_line_node(frm)
        buf = ""
        while bp is not ep:
            buf += bp.text
            bp = bp.next
        self.delete_lines(frm, to, isglobal)
        self.current = frm - 1
        self.put_sbuf_line(buf + "\n")
        self.push_undo(UADD, self.current, self.current)
        self.modified = True
        return True

    def move_lines(self, first, second, addr, isglobal):
        n = self.inc_addr(second)
        p = first - 1
        if addr == first - 1 or addr == second:
            a2 = self.search_line_node(n)
            b2 = self.search_line_node(p)
            self.current = second
        else:
            self.push_undo(UMOV, p, n)
            self.push_undo(UMOV, addr, self.inc_addr(addr))
            a1 = self.search_line_node(n)
            if addr < first:
                b1 = self.search_line_node(p)
                b2 = self.search_line_node(addr)
            else:
                b2 = self.search_line_node(addr)
                b1 = self.search_line_node(p)
            a2 = b2.next
            link(b2, b1.next)
            link(a1.prev, a2)
            link(b1, a1)
            self.current = addr + (second - first + 1 if addr < first else 0)
        if isglobal:
            self.unset_active_nodes(b2.next, a2)
        self.modified = True
        return True

    def put_lines(self, addr):
        lp = self.yank.next
        if lp is self.yank:
            self.set_error("Nothing to put")
            return False
        up = None
        self.current = addr
        while lp is not self.yank:
            p = Line(lp.text)
            self.add_line_node(p)
            if up:
                up.tail = p
            else:
                up = self.push_undo(UADD, self.current, self.current)
            self.modified = True
            lp = lp.next
        return True

    def undo(self, isglobal):
        o_current, o_last, o_modified = self.current, self.last, self.modified
        if not self.ustack or self.u_current < 0 or self.u_last < 0:
            self.set_error("Nothing to undo")
            return False
        us = self.ustack
        n = len(us) - 1
        while n >= 0:
            u = us[n]
            if u.type == UADD:
                link(u.head.prev, u.tail.next)
            elif u.type == UDEL:
                link(u.head.prev, u.head)
                link(u.tail, u.tail.next)
            else:
                link(us[n - 1].head, u.head.next)
                link(u.tail.prev, us[n - 1].tail)
                link(u.head, u.tail)
                n -= 1
            us[n].type ^= 1
            n -= 1
        us.reverse()
        if isglobal:
            self.clear_active_list()
        self.current, self.u_current = self.u_current, o_current
        self.last, self.u_last = self.u_last, o_last
        self.modified, self.u_modified = self.u_modified, o_modified
        return True

    # ---- global active list -------------------------------------------------
    def clear_active_list(self):
        self.active = []
        self.active_idx = self.active_idxm = 0

    def next_active_node(self):
        while self.active_idx < len(self.active) and self.active[self.active_idx] is None:
            self.active_idx += 1
        if self.active_idx < len(self.active):
            lp = self.active[self.active_idx]
            self.active_idx += 1
            return lp
        return None

    def unset_active_nodes(self, bp, ep):
        n = len(self.active)
        while bp is not ep:
            for _ in range(n):
                self.active_idxm += 1
                if self.active_idxm >= n:
                    self.active_idxm = 0
                if self.active[self.active_idxm] is bp:
                    self.active[self.active_idxm] = None
                    break
            bp = bp.next

    # ---- regular expressions ------------------------------------------------
    def compile_regex(self, pat, icase):
        try:
            rx = Regex(pat, ere=self.ere, icase=icase)
        except (RegexError, RecursionError, ValueError, IndexError):
            self.set_error("Invalid regular expression")
            return None
        self.last_regexp = rx
        return rx

    def extract_pattern(self, cmd, delim):
        s = cmd.s
        nd = cmd.i
        while s[nd] != delim and s[nd] != "\n":
            if s[nd] == "[":
                nd = parse_char_class(s, nd + 1)
                if nd < 0:
                    self.set_error("Unbalanced brackets ([])")
                    return None
            elif s[nd] == "\\":
                nd += 1
                if s[nd] == "\n":
                    self.set_error("Trailing backslash (\\)")
                    return None
            nd += 1
        pat = s[cmd.i:nd]
        cmd.i = nd
        return pat

    def get_compiled_regex(self, cmd):
        delim = cmd.ch()
        if delim in (" ", "\n"):
            self.set_error("Invalid pattern delimiter")
            return None
        cmd.i += 1
        if cmd.ch() == delim or cmd.ch() == "\n":
            if not self.last_regexp:
                self.set_error("No previous pattern")
                return None
            if cmd.ch() == delim:
                cmd.i += 1
                if cmd.ch() == "I":
                    self.set_error("Suffix 'I' not allowed on empty regexp")
                    return None
            return self.last_regexp
        pat = self.extract_pattern(cmd, delim)
        if pat is None:
            return None
        icase = False
        if cmd.ch() == delim:
            cmd.i += 1
            if cmd.ch() == "I":
                icase = True
                cmd.i += 1
        return self.compile_regex(pat, icase)

    def get_pattern_for_s(self, cmd):
        delim = cmd.ch()
        if delim in (" ", "\n"):
            self.set_error("Invalid pattern delimiter")
            return None
        cmd.i += 1
        if cmd.ch() == delim:
            if not self.last_regexp:
                self.set_error("No previous pattern")
                return None
            return ""
        pat = self.extract_pattern(cmd, delim)
        if pat is None:
            return None
        if cmd.ch() != delim:
            self.set_error("Missing pattern delimiter")
            return None
        return pat

    def set_subst_regex(self, pat, icase):
        if not pat and icase:
            self.set_error("Suffix 'I' not allowed on empty regexp")
            return False
        rx = self.compile_regex(pat, icase) if pat else self.last_regexp
        if rx is not None:
            self.subst_regexp = rx
        return rx is not None

    def build_active_list(self, cmd, first, second, match):
        rx = self.get_compiled_regex(cmd)
        if rx is None:
            return False
        self.clear_active_list()
        lp = self.search_line_node(first)
        for _ in range(first, second + 1):
            if (rx.search(lp.text) is not None) == match:
                self.active.append(lp)
            lp = lp.next
        return True

    def next_matching_node_addr(self, cmd):
        forward = cmd.ch() == "/"
        rx = self.get_compiled_regex(cmd)
        addr = self.current
        if rx is None:
            return -1
        while True:
            addr = self.inc_addr(addr) if forward else self.dec_addr(addr)
            if addr:
                if rx.search(self.search_line_node(addr).text) is not None:
                    return addr
            if addr == self.current:
                break
        self.set_error("No match")
        return -1

    def extract_replacement(self, cmd, isglobal):
        delim = cmd.ch()
        if delim == "\n":
            self.set_error("Missing pattern delimiter")
            return False
        cmd.i += 1
        if cmd.ch() == "%" and (cmd.ch(1) == delim or (cmd.ch(1) == "\n" and (not isglobal or cmd.i + 2 >= len(cmd.s)))):
            cmd.i += 1
            if self.rbuf is None:
                self.set_error(NO_PREV_SUBST)
                return False
            return True
        buf = []
        while cmd.ch() != delim:
            if cmd.ch() == "\n" and (not isglobal or cmd.i + 1 >= len(cmd.s)):
                break
            c = cmd.ch()
            buf.append(c)
            cmd.i += 1
            if c == "\\":
                c2 = cmd.ch()
                buf.append(c2)
                cmd.i += 1
                if c2 == "\n" and not isglobal:
                    line = self.get_stdin_line()
                    if not line:
                        return False
                    cmd.s = line
                    cmd.i = 0
        self.rbuf = "".join(buf)
        return True

    def replace_matched_text(self, txt, m, nsub):
        out = []
        r = self.rbuf
        i = 0
        while i < len(r):
            c = r[i]
            if c == "&":
                out.append(txt[m[0][0]:m[0][1]])
            elif c == "\\":
                i += 1
                d = r[i] if i < len(r) else "\0"
                if "1" <= d <= "9" and int(d) <= nsub:
                    span = m[int(d)]
                    if span is not None:
                        out.append(txt[span[0]:span[1]])
                elif i < len(r):
                    out.append(d)
            else:
                out.append(c)
            i += 1
        return "".join(out)

    def regexec(self, rx, txt, notbol=False):
        r = rx.search(txt, 0, notbol)
        if r is None:
            return None
        b, e, caps = r
        return [(b, e)] + list(caps[1:])

    def line_replace(self, lp, snum):
        rx = self.subst_regexp
        txt = lp.text
        glob = snum <= 0
        changed = False
        out = []
        m = self.regexec(rx, txt)
        if m is None:
            return None
        matchno = 0
        infloop = False
        while True:
            matchno += 1
            if glob or snum == matchno:
                changed = True
                out.append(txt[:m[0][0]])
                out.append(self.replace_matched_text(txt, m, rx.ngroups))
            else:
                out.append(txt[:m[0][1]])
            txt = txt[m[0][1]:]
            if glob and m[0][1] == 0:
                if not infloop:
                    infloop = True
                else:
                    self.set_error("Infinite substitution loop")
                    return False
            if not (txt and (not changed or glob)):
                break
            m = self.regexec(rx, txt, notbol=True)
            if m is None:
                break
        if not changed:
            return None
        return "".join(out) + txt + "\n"

    def search_and_replace(self, first, second, snum, isglobal):
        addr = first
        match_found = False
        for _ in range(second - first + 1):
            lp = self.search_line_node(addr)
            new = self.line_replace(lp, snum)
            if new is False:
                return False
            if new is not None:
                up = None
                self.delete_lines(addr, addr, isglobal)
                self.current = addr - 1
                while new:
                    new = self.put_sbuf_line(new)
                    if up:
                        up.tail = self.search_line_node(self.current)
                    else:
                        up = self.push_undo(UADD, self.current, self.current)
                addr = self.current
                match_found = True
            addr += 1
        if not match_found and not isglobal:
            self.set_error("No match")
            return False
        return True

    # ---- files --------------------------------------------------------------
    def may_access_filename(self, name):
        if self.restricted_:
            if name.startswith("!"):
                self.set_error("Shell access restricted")
                return False
            if name == ".." or "/" in name:
                self.set_error("Directory access restricted")
                return False
        return True

    def read_file(self, filename, addr, load=False):
        try:
            with open(filename, "rb") as f:
                data = f.read().decode("latin-1")
        except OSError as e:
            self.strerror(filename, e.strerror or "error")
            self.set_error("Cannot open input file")
            return -1
        lp = self.search_line_node(addr)
        up = None
        total = 0
        # ed's model: a global isbinary flag that any NUL sets and only a fresh
        # buffer clears, and one remembered line node, the last line of the last
        # read that ended without a newline into a binary buffer. The newline is
        # left off on writing only while that node is still the last line.
        o_isbinary = self.isbinary
        appended = addr == self.last
        o_unterminated = self.unterminated_last_line()
        newline_added = False
        self.current = addr
        pos = 0
        while pos < len(data):
            j = data.find("\n", pos)
            if j < 0:
                seg = data[pos:]
                pos = len(data)
                if "\x00" in seg:
                    self.isbinary = True
                newline_added = True
                # the added newline counts as read unless the buffer is binary
                total += len(seg) + (0 if self.isbinary else 1)
                line = seg + "\n"
            else:
                line = data[pos:j + 1]
                pos = j + 1
                if "\x00" in line:
                    self.isbinary = True
                total += len(line)
            self.put_sbuf_line(line)
            lp = lp.next
            if up:
                up.tail = lp
            else:
                up = self.push_undo(UADD, self.current, self.current)
        if addr and appended and total and o_unterminated:
            self.write("Newline inserted\n")
        elif newline_added and (not appended or not self.isbinary):
            self.write("Newline appended\n")
        if not appended and self.isbinary and not o_isbinary and newline_added:
            total += 1
        if appended and self.isbinary and (newline_added or total == 0):
            self.unterminated = self.search_line_node(self.last)
        if not self.scripted:
            self.write("%d\n" % total)
        return self.current - addr

    def write_file(self, filename, mode, frm, to):
        try:
            f = open(filename, mode + "b")
        except OSError as e:
            self.strerror(filename, e.strerror or "error")
            self.set_error("Cannot open output file")
            return -1
        size = 0
        with f:
            lp = self.search_line_node(frm)
            a = frm
            while a and a <= to:
                # the newline is left off only for the remembered unterminated line,
                # and only while it is still the last line of the buffer
                bare = a == self.last and self.isbinary and lp is self.unterminated
                data = (lp.text + ("" if bare else "\n")).encode("latin-1")
                f.write(data)
                size += len(data)
                a += 1
                lp = lp.next
        if not self.scripted:
            self.write("%d\n" % size)
        return to - frm + 1 if (frm and frm <= to) else 0

    def get_filename(self, cmd, trad_f):
        skip_blanks(cmd)
        if cmd.ch() != "\n":
            if not self.get_extended_line(cmd, True):
                return None
        elif not trad_f and not self.def_filename:
            self.set_error("No current filename")
            return None
        j = cmd.s.index("\n", cmd.i)
        name = cmd.s[cmd.i:j]
        cmd.i = j
        while cmd.ch() == "\n":
            cmd.i += 1
        return name if self.may_access_filename(name) else None

    # ---- printing -----------------------------------------------------------
    def print_line(self, text, pflags):
        out = []
        col = 0
        if pflags & PF_N:
            out.append("%d\t" % self.current)
            col = 8
        for ch in text:
            if not pflags & PF_L:
                out.append(ch)
                continue
            col += 1
            if col > self.window_columns:
                col = 1
                out.append("\\\n")
            o = ord(ch)
            if 32 <= o <= 126:
                if ch in "$\\":
                    col += 1
                    out.append("\\")
                out.append(ch)
            else:
                col += 1
                out.append("\\")
                esc = "\a\b\f\n\r\t\v".find(ch)
                if o and esc >= 0:
                    out.append("abfnrtv"[esc])
                else:
                    col += 2
                    out.append("%03o" % o)
        if not self.trad and pflags & PF_L:
            out.append("$")
        out.append("\n")
        self.write("".join(out))

    def print_lines(self, frm, to, pflags):
        ep = self.search_line_node(self.inc_addr(to))
        bp = self.search_line_node(frm)
        if not frm:
            self.invalid_address()
            return False
        while bp is not ep:
            self.current = frm
            frm += 1
            self.print_line(bp.text, pflags)
            bp = bp.next
        return True

    # ---- command parsing ----------------------------------------------------
    def parse_int(self, cmd):
        s = cmd.s
        j = cmd.i
        k = j
        if k < len(s) and s[k] in "+-":
            k += 1
        e = k
        while e < len(s) and s[e].isdigit():
            e += 1
        if e == k:
            self.set_error("Invalid number")
            return None
        v = int(s[j:e])
        if abs(v) > 2147483647:
            self.set_error("Number out of range")
            return None
        cmd.i = e
        return v

    def extract_addresses(self, cmd):
        first = True
        self.first_addr = self.second_addr = -1
        skip_blanks(cmd)
        while True:
            ch = cmd.ch()
            if ch.isdigit():
                n = self.parse_int(cmd)
                if n is None:
                    return -1
                if first:
                    first = False
                    self.second_addr = n
                else:
                    self.second_addr += n
            elif ch in "\t ":
                cmd.i += 1
                skip_blanks(cmd)
            elif ch in "+-":
                if first:
                    first = False
                    self.second_addr = self.current
                if cmd.ch(1).isdigit():
                    n = self.parse_int(cmd)
                    if n is None:
                        return -1
                    self.second_addr += n
                else:
                    cmd.i += 1
                    self.second_addr += 1 if ch == "+" else -1
            elif ch in ".$":
                if not first:
                    self.invalid_address()
                    return -1
                first = False
                cmd.i += 1
                self.second_addr = self.current if ch == "." else self.last
            elif ch in "/?":
                if not first:
                    self.invalid_address()
                    return -1
                self.second_addr = self.next_matching_node_addr(cmd)
                if self.second_addr < 0:
                    return -1
                first = False
            elif ch == "'":
                if not first:
                    self.invalid_address()
                    return -1
                first = False
                cmd.i += 1
                c = cmd.ch()
                cmd.i += 1
                self.second_addr = self.get_marked_node_addr(c)
                if self.second_addr < 0:
                    return -1
            elif ch in "%,;":
                if first:
                    if self.first_addr < 0:
                        self.first_addr = self.current if ch == ";" else 1
                        self.second_addr = self.last
                    else:
                        self.first_addr = self.second_addr
                else:
                    if self.second_addr < 0 or self.second_addr > self.last:
                        self.invalid_address()
                        return -1
                    if ch == ";":
                        self.current = self.second_addr
                    self.first_addr = self.second_addr
                    first = True
                cmd.i += 1
            else:
                if not first and (self.second_addr < 0 or self.second_addr > self.last):
                    self.invalid_address()
                    return -1
                cnt = 0
                if self.second_addr >= 0:
                    cnt = 2 if self.first_addr >= 0 else 1
                if cnt <= 0:
                    self.second_addr = self.current
                if cnt <= 1:
                    self.first_addr = self.second_addr
                return cnt

    def get_marked_node_addr(self, c):
        k = ord(c) - ord("a")
        if k < 0 or k >= 26:
            self.set_error("Invalid mark character")
            return -1
        return self.get_line_node_addr(self.marks[k])

    def get_third_addr(self, cmd):
        o1, o2 = self.first_addr, self.second_addr
        cnt = self.extract_addresses(cmd)
        if cnt < 0:
            return None
        if self.trad and cnt == 0:
            self.set_error("Destination expected")
            return None
        if self.second_addr < 0 or self.second_addr > self.last:
            self.invalid_address()
            return None
        addr = self.second_addr
        self.first_addr, self.second_addr = o1, o2
        return addr

    def check_addr_range(self, n, m, cnt):
        if cnt == 0:
            self.first_addr, self.second_addr = n, m
        if self.first_addr < 1 or self.first_addr > self.second_addr or self.second_addr > self.last:
            self.invalid_address()
            return False
        return True

    def check_addr_range2(self, cnt):
        return self.check_addr_range(self.current, self.current, cnt)

    def check_second_addr(self, addr, cnt):
        if cnt == 0:
            self.second_addr = addr
        if self.second_addr < 1 or self.second_addr > self.last:
            self.invalid_address()
            return False
        return True

    def get_command_suffix(self, cmd, pflags):
        while True:
            ch = cmd.ch()
            bit = {"l": PF_L, "n": PF_N, "p": PF_P}.get(ch)
            if bit is None or pflags[0] & bit:
                break
            pflags[0] |= bit
            cmd.i += 1
        c = cmd.ch()
        cmd.i += 1
        if c != "\n":
            self.set_error(INV_COM_SUF)
            return False
        return True

    def get_command_s_suffix(self, cmd, pflags):
        rep = False
        error = False
        icase = False
        snum = None
        while True:
            ch = cmd.ch()
            if "1" <= ch <= "9":
                n = self.parse_int(cmd) if not rep else None
                if rep or n is None or n <= 0:
                    error = True
                    break
                rep = True
                snum = n
                continue
            elif ch == "g":
                if rep:
                    break
                rep = True
                snum = 0
            elif ch in "iI":
                if icase:
                    break
                icase = True
            elif ch in "lnp":
                bit = {"l": PF_L, "n": PF_N, "p": PF_P}[ch]
                if pflags[0] & bit:
                    break
                pflags[0] |= bit
            else:
                break
            cmd.i += 1
        c = cmd.ch()
        cmd.i += 1
        if error or c != "\n":
            self.set_error(INV_COM_SUF)
            return None
        return snum, icase

    def unexpected_address(self, cnt):
        if cnt > 0:
            self.set_error("Unexpected address")
            return True
        return False

    def unexpected_command_suffix(self, ch):
        if not ch.isspace():
            self.set_error("Unexpected command suffix")
            return True
        return False

    def command_s(self, cmd, pflags, cnt, isglobal):
        sflags = 0
        if not self.check_addr_range2(cnt):
            return False
        while True:
            error = False
            ch = cmd.ch()
            if "1" <= ch <= "9":
                n = self.parse_int(cmd) if not (sflags & 1) else None
                if (sflags & 1) or n is None or n <= 0:
                    error = True
                else:
                    sflags |= 1
                    self.snum = n
            elif ch == "\n":
                sflags |= 8
            elif ch == "g":
                if sflags & 1:
                    error = True
                else:
                    sflags |= 1
                    self.snum = 0 if self.snum else 1
                    cmd.i += 1
            elif ch == "p":
                if sflags & 2 or sflags & 4:
                    error = True
                else:
                    sflags |= 2
                    cmd.i += 1
            elif ch == "r":
                if sflags & 4:
                    error = True
                else:
                    sflags |= 4
                    cmd.i += 1
            else:
                if sflags:
                    error = True
            if error:
                self.set_error(INV_COM_SUF)
                return False
            if not (sflags and cmd.ch() != "\n"):
                break
        if sflags:
            if self.subst_regexp is None:
                self.set_error(NO_PREV_SUBST)
                return False
            if sflags & 4:
                if self.last_regexp is None:
                    self.set_error("No previous pattern")
                    return False
                self.subst_regexp = self.last_regexp
            if sflags & 2:
                self.s_pflags ^= self.pmask
        else:
            pat = self.get_pattern_for_s(cmd)
            if pat is None:
                return False
            delim = cmd.ch()
            if not self.extract_replacement(cmd, isglobal):
                return False
            self.s_pflags = 0
            self.snum = 1
            icase = False
            if cmd.ch() == "\n":
                self.s_pflags = PF_P
            else:
                if cmd.ch() == delim:
                    cmd.i += 1
                pf = [self.s_pflags]
                r = self.get_command_s_suffix(cmd, pf)
                if r is None:
                    return False
                self.s_pflags = pf[0]
                if r[0] is not None:
                    self.snum = r[0]
                icase = r[1]
            self.pmask = self.s_pflags & (PF_L | PF_N | PF_P) or PF_P
            if not self.set_subst_regex(pat, icase):
                return False
        pflags[0] = self.s_pflags
        if not isglobal:
            self.clear_undo_stack()
        return self.search_and_replace(self.first_addr, self.second_addr, self.snum, isglobal)

    def exec_command(self, cmd, prev_status, isglobal):
        pflags = [0]
        cnt = self.extract_addresses(cmd)
        if cnt < 0:
            return ERR
        skip_blanks(cmd)
        c = cmd.ch()
        cmd.i += 1
        if c == "a":
            if not self.get_command_suffix(cmd, pflags):
                return ERR
            if not isglobal:
                self.clear_undo_stack()
            if not self.append_lines(cmd, self.second_addr, False, isglobal):
                return ERR
        elif c == "c":
            if not self.check_addr_range2(cnt) or not self.get_command_suffix(cmd, pflags):
                return ERR
            if not isglobal:
                self.clear_undo_stack()
            if not self.delete_lines(self.first_addr, self.second_addr, isglobal):
                return ERR
            if not self.append_lines(cmd, self.current, self.current >= self.first_addr, isglobal):
                return ERR
        elif c == "d":
            if not self.check_addr_range2(cnt) or not self.get_command_suffix(cmd, pflags):
                return ERR
            if not isglobal:
                self.clear_undo_stack()
            self.delete_lines(self.first_addr, self.second_addr, isglobal)
        elif c in "eE":
            if c == "e" and self.modified and prev_status != EMOD:
                return EMOD
            if self.unexpected_address(cnt) or self.unexpected_command_suffix(cmd.ch()):
                return ERR
            fnp = self.get_filename(cmd, False)
            if fnp is None:
                return ERR
            if self.last:
                self.delete_lines(1, self.last, isglobal)
            self.clear_yank()
            self.clear_undo_stack()
            self.modified = False
            self.isbinary = False
            self.unterminated = None
            if fnp:
                self.def_filename = fnp
            if self.read_file(fnp or self.def_filename, 0, load=True) < 0:
                return ERR
            self.reset_undo_state()
        elif c == "f":
            if self.unexpected_address(cnt) or self.unexpected_command_suffix(cmd.ch()):
                return ERR
            fnp = self.get_filename(cmd, self.trad)
            if fnp is None:
                return ERR
            if fnp:
                self.def_filename = fnp
            self.write(self.def_filename + "\n")
        elif c in "gvGV":
            if isglobal:
                self.set_error("Cannot nest global commands")
                return ERR
            match = c in "gG"
            if not self.check_addr_range(1, self.last, cnt) or not self.build_active_list(cmd, self.first_addr, self.second_addr, match):
                return ERR
            interactive = c in "GV"
            if interactive and not self.get_command_suffix(cmd, pflags):
                return ERR
            st = self.exec_global(cmd, pflags[0], interactive)
            if st != 0:
                return st
        elif c in "hH":
            if self.unexpected_address(cnt) or not self.get_command_suffix(cmd, pflags):
                return ERR
            if c == "H":
                self.verbose = not self.verbose
            if (c == "h" or self.verbose) and self.errmsg:
                self.write(self.errmsg + "\n")
        elif c == "i":
            if not self.get_command_suffix(cmd, pflags):
                return ERR
            if not isglobal:
                self.clear_undo_stack()
            if not self.append_lines(cmd, self.second_addr, True, isglobal):
                return ERR
        elif c == "j":
            if not self.check_addr_range(self.current, self.current + 1, cnt) or not self.get_command_suffix(cmd, pflags):
                return ERR
            if not isglobal:
                self.clear_undo_stack()
            if self.first_addr < self.second_addr:
                self.join_lines(self.first_addr, self.second_addr, isglobal)
        elif c == "k":
            n = cmd.ch()
            cmd.i += 1
            if self.second_addr == 0:
                self.invalid_address()
                return ERR
            if not self.get_command_suffix(cmd, pflags):
                return ERR
            k = ord(n) - ord("a")
            if k < 0 or k >= 26:
                self.set_error("Invalid mark character")
                return ERR
            self.marks[k] = self.search_line_node(self.second_addr)
        elif c in "lnp":
            bit = {"l": PF_L, "n": PF_N, "p": PF_P}[c]
            if not self.check_addr_range2(cnt) or not self.get_command_suffix(cmd, pflags) or not self.print_lines(self.first_addr, self.second_addr, pflags[0] | bit):
                return ERR
            pflags[0] = 0
        elif c == "m":
            if not self.check_addr_range2(cnt):
                return ERR
            addr = self.get_third_addr(cmd)
            if addr is None:
                return ERR
            if self.first_addr <= addr < self.second_addr:
                self.set_error("Invalid destination")
                return ERR
            if not self.get_command_suffix(cmd, pflags):
                return ERR
            if not isglobal:
                self.clear_undo_stack()
            self.move_lines(self.first_addr, self.second_addr, addr, isglobal)
        elif c in "PqQ":
            if self.unexpected_address(cnt) or not self.get_command_suffix(cmd, pflags):
                return ERR
            if c == "P":
                self.prompt_on = not self.prompt_on
            elif c == "q" and self.modified and prev_status != EMOD:
                return EMOD
            else:
                return QUIT
        elif c == "r":
            if self.unexpected_command_suffix(cmd.ch()):
                return ERR
            if cnt == 0:
                self.second_addr = self.last
            fnp = self.get_filename(cmd, False)
            if fnp is None:
                return ERR
            if not self.def_filename:
                self.def_filename = fnp
            if not isglobal:
                self.clear_undo_stack()
            addr = self.read_file(fnp or self.def_filename, self.second_addr)
            if addr < 0:
                return ERR
            if addr:
                self.modified = True
        elif c == "s":
            if not self.command_s(cmd, pflags, cnt, isglobal):
                return ERR
        elif c == "t":
            if not self.check_addr_range2(cnt):
                return ERR
            addr = self.get_third_addr(cmd)
            if addr is None or not self.get_command_suffix(cmd, pflags):
                return ERR
            if not isglobal:
                self.clear_undo_stack()
            self.copy_lines(self.first_addr, self.second_addr, addr)
        elif c == "u":
            if self.unexpected_address(cnt) or not self.get_command_suffix(cmd, pflags) or not self.undo(isglobal):
                return ERR
        elif c in "wW":
            n = cmd.ch()
            if n in "qQ":
                cmd.i += 1
            if self.unexpected_command_suffix(cmd.ch()):
                return ERR
            fnp = self.get_filename(cmd, False)
            if fnp is None:
                return ERR
            if cnt == 0 and self.last == 0:
                self.first_addr = self.second_addr = 0
            elif not self.check_addr_range(1, self.last, cnt):
                return ERR
            if not self.def_filename:
                self.def_filename = fnp
            addr = self.write_file(fnp or self.def_filename, "a" if c == "W" else "w", self.first_addr, self.second_addr)
            if addr < 0:
                return ERR
            if addr == self.last:
                self.modified = False
            elif n == "q" and self.modified and prev_status != EMOD:
                return EMOD
            if n in "qQ":
                return QUIT
        elif c == "x":
            if self.second_addr < 0 or self.second_addr > self.last:
                self.invalid_address()
                return ERR
            if not self.get_command_suffix(cmd, pflags):
                return ERR
            if not isglobal:
                self.clear_undo_stack()
            if not self.put_lines(self.second_addr):
                return ERR
        elif c == "y":
            if not self.check_addr_range2(cnt) or not self.get_command_suffix(cmd, pflags):
                return ERR
            self.yank_lines(self.first_addr, self.second_addr)
        elif c == "z":
            if not self.check_second_addr(self.current + (0 if isglobal else 1), cnt):
                return ERR
            if "0" < cmd.ch() <= "9":
                n = self.parse_int(cmd)
                if n is None:
                    return ERR
                self.window_lines = n
            if not self.get_command_suffix(cmd, pflags) or not self.print_lines(self.second_addr, min(self.last, self.second_addr + self.window_lines - 1), pflags[0]):
                return ERR
            pflags[0] = 0
        elif c == "=":
            if not self.get_command_suffix(cmd, pflags):
                return ERR
            self.write("%d\n" % (self.second_addr if cnt else self.last))
        elif c == "\n":
            if not self.check_second_addr(self.current + (1 if (self.trad or not isglobal) else 0), cnt) or not self.print_lines(self.second_addr, self.second_addr, 0):
                return ERR
        elif c == "#":
            j = cmd.s.find("\n", cmd.i)
            cmd.i = (j + 1) if j >= 0 else len(cmd.s)
        else:
            self.set_error("Unknown command")
            return ERR
        if pflags[0] and not self.print_lines(self.current, self.current, pflags[0]):
            return ERR
        return 0

    def exec_global(self, cmd, pflags, interactive):
        gcmd = None
        if not interactive:
            if self.trad and cmd.s[cmd.i:] == "\n":
                gcmd = "p\n"
            else:
                if not self.get_extended_line(cmd, False):
                    return ERR
                gcmd = cmd.s[cmd.i:]
        self.clear_undo_stack()
        while True:
            lp = self.next_active_node()
            if lp is None:
                break
            self.current = self.get_line_node_addr(lp)
            if self.current < 0:
                return ERR
            if interactive:
                if not self.print_lines(self.current, self.current, pflags):
                    return ERR
                line = self.get_stdin_line()
                if not line:
                    return ERR
                if line == "\n":
                    continue
                if line == "&\n":
                    if gcmd is None:
                        self.set_error("No previous command")
                        return ERR
                else:
                    c2 = Cmd(line)
                    if not self.get_extended_line(c2, False):
                        return ERR
                    gcmd = c2.s[c2.i:]
            sub = Cmd(gcmd)
            while sub.i < len(sub.s):
                st = self.exec_command(sub, 0, True)
                if st != 0:
                    return st
        return 0

    def main_loop(self, initial_error, loose):
        err_status = 0
        status = 0
        if initial_error:
            status = -1
            err_status = 1
        while True:
            if status < 0 and self.verbose:
                self.write(self.errmsg + "\n")
            if self.prompt_on:
                self.write(self.prompt_str)
            line = self.get_stdin_line()
            if not line:
                if not self.modified or status == EMOD:
                    status = QUIT
                else:
                    status = EMOD
                    if not loose:
                        err_status = 2
            else:
                status = self.exec_command(Cmd(line), status, False)
            if status == 0:
                continue
            if status == QUIT:
                return err_status
            self.write("?\n")
            if not loose and err_status == 0:
                err_status = 1
            if status == EMOD:
                self.set_error("Warning: buffer modified")
            if not self.interactive:
                if self.verbose:
                    self.write("script, line %d: %s\n" % (self.linenum, self.errmsg))
                return 1 if status == FATAL else err_status
            if status == FATAL:
                if self.verbose:
                    self.write(self.errmsg + "\n")
                return 1


def trailing_escape(s):
    odd = False
    k = len(s) - 1
    while k >= 0 and s[k] == "\\":
        odd = not odd
        k -= 1
    return odd


def skip_blanks(cmd):
    while cmd.ch().isspace() and cmd.ch() not in "\n\0":
        cmd.i += 1


def parse_char_class(s, p):
    """Return the index of the ']' closing a bracket expression, or -1."""
    if p < len(s) and s[p] == "^":
        p += 1
    if p < len(s) and s[p] == "]":
        p += 1
    while p < len(s) and s[p] != "]" and s[p] != "\n":
        if s[p] == "[" and p + 1 < len(s) and s[p + 1] in ".:=":
            d = s[p + 1]
            p += 2
            c = s[p] if p < len(s) else "\n"
            while not (s[p] == "]" and c == d):
                c = s[p]
                if c == "\n":
                    return -1
                p += 1
        p += 1
    return p if p < len(s) and s[p] == "]" else -1


def main(argv):
    opts = {"E": False, "G": False, "l": False, "p": None, "q": False, "r": False, "s": False, "v": False}
    files = []
    i = 0
    only_files = False
    while i < len(argv):
        a = argv[i]
        # options may come before or after FILE, "--" ends them, and "-" is not one
        if only_files or not a.startswith("-") or a == "-" or len(a) == 1:
            files.append(a)
            i += 1
            continue
        if a == "--":
            only_files = True
            i += 1
            continue
        flags = a[1:]
        k = 0
        while k < len(flags):
            f = flags[k]
            if f == "p":
                rest = flags[k + 1:]
                if rest:
                    opts["p"] = rest
                elif i + 1 < len(argv):
                    i += 1
                    opts["p"] = argv[i]
                else:
                    sys.stderr.write("ed: option '-p' requires an argument\n")
                    return 1
                break
            if f in opts:
                opts[f] = True
            else:
                sys.stderr.write("ed: invalid option -- '%s'\n" % f)
                return 1
            k += 1
        i += 1
    # the matcher in posixre recurses once per repetition, so a long line needs
    # room for that many Python frames, which is not the C stack
    sys.setrecursionlimit(max(sys.getrecursionlimit(), 4_000_000))
    data = sys.stdin.buffer.read().decode("latin-1")
    ed = Ed(data, opts)
    initial_error = False
    code = None
    for arg in files:
        if arg == "-":
            ed.scripted = True
            continue
        if ed.may_access_filename(arg):
            ret = ed.read_file(arg, 0, load=True)
            if ret < 0 and not ed.interactive:
                code = 2
                break
            ed.def_filename = arg
            if ret == -2:
                initial_error = True
        else:
            if not ed.interactive:
                code = 2
                break
            initial_error = True
        break
    if code is None:
        if initial_error:
            ed.write("?\n")
        code = ed.main_loop(initial_error, opts["l"])
    sys.stdout.buffer.write("".join(ed.out).encode("latin-1"))
    sys.stdout.flush()
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
