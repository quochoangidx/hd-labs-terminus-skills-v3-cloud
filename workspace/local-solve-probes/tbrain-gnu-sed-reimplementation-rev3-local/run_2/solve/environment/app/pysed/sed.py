"""pysed: a GNU sed 4.9 replacement in pure Python.

Usage: python3 /app/pysed/sed.py [OPTION]... {script-only-if-no-other-script} [input-file]...
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from posixre import compile_regex, SIMPLE_ESC  # noqa: E402


class SedError(Exception):
    def __init__(self, msg, status=1):
        Exception.__init__(self, msg)
        self.status = status


def to_str(arg):
    if isinstance(arg, bytes):
        return arg.decode('latin-1')
    return os.fsencode(arg).decode('latin-1')


# ---------------------------------------------------------------------------
# Script compilation

class Addr:
    __slots__ = ('kind', 'num', 'step', 'regex')

    def __init__(self, kind, num=0, step=0, regex=None):
        self.kind = kind   # 'num', 'last', 'step', 're', 'zero', 'plus', 'mod'
        self.num = num
        self.step = step
        self.regex = regex  # (pattern or None for empty) string


class Cmd:
    def __init__(self):
        self.a1 = None
        self.a2 = None
        self.neg = False
        self.name = None
        self.arg = None
        self.range_active = False
        self.range_end = 0
        self.target = None  # for { and branches


class ScriptParser:
    def __init__(self, text, ere):
        self.s = text
        self.i = 0
        self.ere = ere
        self.cmds = []
        self.labels = {}
        self.blocks = []
        self.branches = []

    def peek(self):
        if self.i < len(self.s):
            return self.s[self.i]
        return None

    def getc(self):
        if self.i < len(self.s):
            c = self.s[self.i]
            self.i += 1
            return c
        self.i += 1
        return None

    def skip_ws(self):
        while self.i < len(self.s) and self.s[self.i] in ' \t':
            self.i += 1

    def skip_ws_nl(self):
        while self.i < len(self.s) and self.s[self.i] in ' \t\n;':
            self.i += 1

    def read_delimited(self, delim, regex):
        """Read up to unescaped delim (GNU match_slash)."""
        out = []
        s = self.s
        while True:
            if self.i >= len(s):
                raise SedError('unterminated address regex')
            c = s[self.i]
            self.i += 1
            if c == delim:
                return ''.join(out)
            if c == '\n' and regex and False:
                pass
            if c == '\\':
                if self.i >= len(s):
                    out.append('\\')
                    continue
                c2 = s[self.i]
                self.i += 1
                if c2 == delim:
                    if not regex and c2 == '&':
                        out.append('\\&')
                    elif c2 == 'n' and regex:
                        out.append('\n')
                    else:
                        out.append(c2)
                elif c2 == 'n' and regex:
                    out.append('\n')
                elif c2 == '\n':
                    if regex:
                        out.append('\n')
                    else:
                        out.append('\\\n')
                else:
                    out.append('\\')
                    out.append(c2)
            else:
                out.append(c)

    def read_number(self):
        st = self.i
        while self.i < len(self.s) and self.s[self.i].isdigit():
            self.i += 1
        return int(self.s[st:self.i])

    def parse_regex_addr(self, delim):
        pat = self.read_delimited(delim, True)
        # I / M flags not used; accept and ignore
        while self.peek() in ('I', 'M'):
            self.i += 1
        return Addr('re', regex=pat if pat != '' else None)

    def parse_addr1(self):
        c = self.peek()
        if c is None:
            return None
        if c.isdigit():
            n = self.read_number()
            if self.peek() == '~':
                self.i += 1
                st = self.read_number() if (self.peek() or '').isdigit() else 0
                return Addr('step', num=n, step=st)
            if n == 0:
                return Addr('zero')
            return Addr('num', num=n)
        if c == '$':
            self.i += 1
            return Addr('last')
        if c == '/':
            self.i += 1
            return self.parse_regex_addr('/')
        if c == '\\':
            self.i += 1
            d = self.getc()
            return self.parse_regex_addr(d)
        return None

    def parse_addr2(self):
        self.skip_ws()
        c = self.peek()
        if c is None:
            raise SedError('unexpected ,')
        if c == '+':
            self.i += 1
            return Addr('plus', num=self.read_number())
        if c == '~':
            self.i += 1
            return Addr('mod', num=self.read_number())
        if c.isdigit():
            return Addr('num', num=self.read_number())
        if c == '$':
            self.i += 1
            return Addr('last')
        if c == '/':
            self.i += 1
            return self.parse_regex_addr('/')
        if c == '\\':
            self.i += 1
            d = self.getc()
            return self.parse_regex_addr(d)
        raise SedError('unexpected ,')

    def read_label(self, stop=''):
        self.skip_ws()
        st = self.i
        while self.i < len(self.s) and self.s[self.i] not in '\n; \t' + stop:
            self.i += 1
        return self.s[st:self.i]

    def read_text(self):
        """Text argument for a, i, c."""
        s = self.s
        self.skip_ws()
        raw = []
        if self.i < len(s) and s[self.i] == '\\':
            self.i += 1
            if self.i < len(s) and s[self.i] == '\n':
                self.i += 1
            elif self.i < len(s):
                raw.append(s[self.i])
                self.i += 1
        while self.i < len(s):
            c = s[self.i]
            self.i += 1
            if c == '\n':
                break
            if c == '\\':
                if self.i < len(s):
                    raw.append('\\')
                    raw.append(s[self.i])
                    self.i += 1
                continue
            raw.append(c)
        text = ''.join(raw)
        # process escapes
        out = []
        k = 0
        while k < len(text):
            c = text[k]
            if c == '\\' and k + 1 < len(text):
                n = text[k + 1]
                if n in SIMPLE_ESC:
                    out.append(SIMPLE_ESC[n])
                else:
                    out.append(n)
                k += 2
                continue
            out.append(c)
            k += 1
        return ''.join(out) + '\n'

    def end_of_cmd(self):
        self.skip_ws()
        c = self.peek()
        if c is None:
            return
        if c in ';\n':
            self.i += 1
            return
        if c == '#' or c == '}':
            return
        # be lenient: treat as start of the next command

    def parse(self):
        s = self.s
        while True:
            self.skip_ws_nl()
            if self.i >= len(s):
                break
            c = s[self.i]
            if c == '#':
                while self.i < len(s) and s[self.i] != '\n':
                    self.i += 1
                continue
            cmd = Cmd()
            cmd.a1 = self.parse_addr1()
            if cmd.a1 is not None:
                self.skip_ws()
                if self.peek() == ',':
                    self.i += 1
                    cmd.a2 = self.parse_addr2()
                if cmd.a1.kind == 'zero':
                    if cmd.a2 is None or cmd.a2.kind != 're':
                        raise SedError('invalid usage of line address 0')
                    cmd.range_active = True
            self.skip_ws()
            while self.peek() == '!':
                cmd.neg = True
                self.i += 1
                self.skip_ws()
            name = self.getc()
            if name is None:
                raise SedError('missing command')
            cmd.name = name
            if name == '{':
                self.blocks.append(len(self.cmds))
                self.cmds.append(cmd)
                continue
            elif name == '}':
                if not self.blocks:
                    raise SedError('unexpected }')
                op = self.blocks.pop()
                self.cmds[op].target = len(self.cmds) + 1
                self.cmds.append(cmd)
                self.end_of_cmd()
                continue
            elif name in 'aic':
                cmd.arg = self.read_text()
            elif name == ':':
                lab = self.read_label()
                if not lab:
                    raise SedError('":" lacks a label')
                self.labels[lab] = len(self.cmds)
                self.end_of_cmd()
                continue
            elif name in 'btT':
                cmd.arg = self.read_label('}')
                self.branches.append(cmd)
                self.end_of_cmd()
            elif name in 'qQ':
                self.skip_ws()
                if (self.peek() or '').isdigit():
                    cmd.arg = self.read_number()
                else:
                    cmd.arg = 0
                self.end_of_cmd()
            elif name == 's':
                delim = self.getc()
                if delim is None or delim in '\n\\':
                    raise SedError('unterminated s command')
                pat = self.read_delimited(delim, True)
                rep = self.read_delimited(delim, False)
                gflag = False
                pflag = 0
                num = None
                while True:
                    f = self.peek()
                    if f == 'g':
                        gflag = True
                        self.i += 1
                    elif f == 'p':
                        pflag += 1
                        self.i += 1
                    elif f is not None and f.isdigit():
                        num = self.read_number()
                    elif f in ('i', 'I', 'm', 'M', 'e'):
                        self.i += 1
                    else:
                        break
                cmd.arg = (pat if pat != '' else None, parse_replacement(rep),
                           gflag, pflag, num or 1)
                self.end_of_cmd()
            elif name in 'dDgGhHxnNpPz=lF':
                self.end_of_cmd()
            elif name in 'y':
                delim = self.getc()
                src = self.read_delimited(delim, False)
                dst = self.read_delimited(delim, False)
                cmd.arg = (unescape_y(src), unescape_y(dst))
                self.end_of_cmd()
            else:
                raise SedError('unknown command: `%s\'' % name)
            self.cmds.append(cmd)
        if self.blocks:
            raise SedError('unmatched `{\'')
        for b in self.branches:
            if b.arg == '':
                b.target = len(self.cmds)
            else:
                if b.arg not in self.labels:
                    raise SedError("can't find label for jump to `%s'" % b.arg)
                b.target = self.labels[b.arg]
        return self.cmds


def unescape_y(s):
    out = []
    k = 0
    while k < len(s):
        c = s[k]
        if c == '\\' and k + 1 < len(s):
            n = s[k + 1]
            if n in SIMPLE_ESC:
                out.append(SIMPLE_ESC[n])
            else:
                out.append(n)
            k += 2
            continue
        out.append(c)
        k += 1
    return ''.join(out)


def parse_replacement(rep):
    """Return list of parts: str literal or int group number."""
    parts = []
    lit = []
    k = 0
    while k < len(rep):
        c = rep[k]
        if c == '\\' and k + 1 < len(rep):
            n = rep[k + 1]
            k += 2
            if n.isdigit():
                if lit:
                    parts.append(''.join(lit))
                    lit = []
                parts.append(int(n))
            elif n in SIMPLE_ESC:
                lit.append(SIMPLE_ESC[n])
            elif n == '\n':
                lit.append('\n')
            else:
                lit.append(n)
            continue
        if c == '&':
            if lit:
                parts.append(''.join(lit))
                lit = []
            parts.append(0)
            k += 1
            continue
        lit.append(c)
        k += 1
    if lit:
        parts.append(''.join(lit))
    return parts


# ---------------------------------------------------------------------------
# Input handling

class Input:
    def __init__(self, files, separate):
        self.files = files if files else ['-']
        self.fidx = 0
        self.lines = None  # lines of current file
        self.lpos = 0
        self.separate = separate
        self.bad = False
        self.new_file_flag = False

    def _open(self, name):
        try:
            if name == '-':
                data = sys.stdin.buffer.read()
            else:
                with open(name, 'rb') as f:
                    data = f.read()
        except IsADirectoryError:
            sys.stderr.write("sed: couldn't edit %s: not a regular file\n" % name)
            self.bad = True
            return []
        except OSError as e:
            sys.stderr.write("sed: can't read %s: %s\n" % (name, e.strerror))
            self.bad = True
            return []
        text = data.decode('latin-1')
        if text == '':
            return []
        parts = text.split('\n')
        if parts[-1] == '':
            parts.pop()
        return parts

    def _ensure(self):
        """Make sure current file has a line available if any remains.
        Returns True if a line is available (possibly in a new file)."""
        while True:
            if self.lines is not None and self.lpos < len(self.lines):
                return True
            if self.fidx >= len(self.files):
                return False
            self.lines = self._open(self.files[self.fidx])
            self.fidx += 1
            self.lpos = 0
            self.new_file_flag = True

    def next_line(self):
        if not self._ensure():
            return None
        ln = self.lines[self.lpos]
        self.lpos += 1
        return ln

    def has_more_in_file(self):
        return self.lines is not None and self.lpos < len(self.lines)

    def is_last(self):
        if self.has_more_in_file():
            return False
        if self.separate:
            return True
        # look ahead across files
        while self.fidx < len(self.files):
            self.lines = self._open(self.files[self.fidx])
            self.fidx += 1
            self.lpos = 0
            self.new_file_flag = True
            if self.lines:
                return False
        return True


# ---------------------------------------------------------------------------
# Execution

class Quit(Exception):
    def __init__(self, status):
        Exception.__init__(self)
        self.status = status


class Sed:
    def __init__(self, cmds, nflag, ere, separate, files):
        self.cmds = cmds
        self.nflag = nflag
        self.ere = ere
        self.separate = separate
        self.inp = Input(files, separate)
        self.out = []
        self.hold = ''
        self.ps = ''
        self.lineno = 0
        self.append_q = []
        self.replaced = False
        self.last_regex = None
        self.pending_new_file = False

    def get_regex(self, pat):
        if pat is None:
            if self.last_regex is None:
                raise SedError('no previous regular expression')
            return self.last_regex
        r = compile_regex(pat, self.ere)
        self.last_regex = r
        return r

    def re_match(self, pat, s):
        r = self.get_regex(pat)
        return r.search(s, 0) is not None

    def is_last(self):
        return self.inp.is_last()

    def match_addr(self, a):
        k = a.kind
        if k == 'num':
            return self.lineno == a.num
        if k == 'last':
            return self.is_last()
        if k == 'step':
            if a.step <= 0:
                return self.lineno == a.num
            return self.lineno >= a.num and (self.lineno - a.num) % a.step == 0
        if k == 're':
            return self.re_match(a.regex, self.ps)
        if k == 'zero':
            return False
        return False

    def selected(self, cmd):
        if cmd.a1 is None:
            return True
        if cmd.a2 is None:
            return self.match_addr(cmd.a1)
        l = self.lineno
        if cmd.range_active:
            a2 = cmd.a2
            if a2.kind in ('num', 'plus', 'mod'):
                end = cmd.range_end
                if end <= l:
                    cmd.range_active = False
                return l <= end
            if a2.kind == 'last':
                if self.is_last():
                    cmd.range_active = False
                return True
            if a2.kind == 're':
                if self.re_match(a2.regex, self.ps):
                    cmd.range_active = False
                return True
            # step as addr2 (first~step) not expected; treat as num
            cmd.range_active = False
            return True
        if not self.match_addr(cmd.a1):
            return False
        a2 = cmd.a2
        if a2.kind == 'num':
            if a2.num <= l:
                return True
            cmd.range_end = a2.num
        elif a2.kind == 'plus':
            if a2.num == 0:
                return True
            cmd.range_end = l + a2.num
        elif a2.kind == 'mod':
            if a2.num <= 0:
                return True
            end = -(-l // a2.num) * a2.num
            if end == l:
                return True
            cmd.range_end = end
        elif a2.kind == 'step':
            if a2.num <= l:
                return True
            cmd.range_end = a2.num
            a2.kind = 'num'
        cmd.range_active = True
        return True

    def emit(self, s):
        self.out.append(s)

    def dump_append(self):
        for t in self.append_q:
            self.out.append(t)
        self.append_q = []

    def reset_file(self):
        self.lineno = 0
        for c in self.cmds:
            if c.a2 is not None:
                c.range_active = c.a1 is not None and c.a1.kind == 'zero'

    def read_line(self):
        """Read next input line into a string; handles -s file switch."""
        ln = self.inp.next_line()
        if ln is None:
            return None
        if self.inp.new_file_flag:
            self.inp.new_file_flag = False
            if self.separate:
                self.reset_file()
        self.lineno += 1
        return ln

    def substitute(self, cmd):
        pat, rep, gflag, pflag, num = cmd.arg
        r = self.get_regex(pat)
        s = self.ps
        n = len(s)
        pos = 0
        out = []
        count = 0
        did = False
        prev_end = -1
        while pos <= n:
            m = r.search(s, pos)
            if m is None:
                break
            st, en = m[0], m[1]
            if st == en and st == prev_end:
                # empty match right after previous match: skip a char
                if st < n:
                    out.append(s[st])
                pos = st + 1
                continue
            out.append(s[pos:st])
            count += 1
            if count >= num:
                did = True
                for p in rep:
                    if isinstance(p, int):
                        if p <= r.ngroups:
                            a, b = m[2 * p], m[2 * p + 1]
                            if a is not None and b is not None:
                                out.append(s[a:b])
                    else:
                        out.append(p)
                if not gflag:
                    pos = en
                    prev_end = en
                    break
            else:
                out.append(s[st:en])
            prev_end = en
            if st == en:
                if st < n:
                    out.append(s[st])
                pos = en + 1
            else:
                pos = en
        if not did:
            return
        if pos <= n:
            out.append(s[pos:])
        self.ps = ''.join(out)
        self.replaced = True
        if pflag:
            for _ in range(pflag):
                self.emit(self.ps + '\n')

    def end_cycle_output(self):
        if not self.nflag:
            self.emit(self.ps + '\n')
        self.dump_append()

    def run(self):
        """Returns exit status."""
        cmds = self.cmds
        ncmds = len(cmds)
        restart = False  # D restart without reading
        while True:
            if not restart:
                ln = self.read_line()
                if ln is None:
                    break
                self.ps = ln
                self.replaced = False
            restart = False
            pc = 0
            action = 'end'  # end, delete, restart, quit
            quit_status = 0
            while pc < ncmds:
                cmd = cmds[pc]
                sel = self.selected(cmd)
                if cmd.neg:
                    sel = not sel
                name = cmd.name
                if not sel:
                    if name == '{':
                        pc = cmd.target
                    else:
                        pc += 1
                    continue
                pc += 1
                if name == '{' or name == '}':
                    continue
                if name == 's':
                    self.substitute(cmd)
                elif name == 'p':
                    self.emit(self.ps + '\n')
                elif name == 'd':
                    action = 'delete'
                    break
                elif name == 'D':
                    idx = self.ps.find('\n')
                    if idx < 0:
                        action = 'delete'
                    else:
                        self.ps = self.ps[idx + 1:]
                        action = 'restart'
                    break
                elif name == 'b':
                    pc = cmd.target
                elif name == 't':
                    if self.replaced:
                        self.replaced = False
                        pc = cmd.target
                elif name == 'T':
                    if self.replaced:
                        self.replaced = False
                    else:
                        pc = cmd.target
                elif name == 'h':
                    self.hold = self.ps
                elif name == 'H':
                    self.hold = self.hold + '\n' + self.ps
                elif name == 'g':
                    self.ps = self.hold
                elif name == 'G':
                    self.ps = self.ps + '\n' + self.hold
                elif name == 'x':
                    self.ps, self.hold = self.hold, self.ps
                elif name == 'z':
                    self.ps = ''
                elif name == 'P':
                    idx = self.ps.find('\n')
                    self.emit((self.ps if idx < 0 else self.ps[:idx]) + '\n')
                elif name == '=':
                    self.emit('%d\n' % self.lineno)
                elif name == 'a':
                    self.append_q.append(cmd.arg)
                elif name == 'i':
                    self.emit(cmd.arg)
                elif name == 'c':
                    if not (cmd.a2 is not None and cmd.range_active) or cmd.neg:
                        self.emit(cmd.arg)
                    action = 'delete'
                    break
                elif name == 'n':
                    if self.inp.is_last():
                        action = 'eof'
                        break
                    if not self.nflag:
                        self.emit(self.ps + '\n')
                    self.dump_append()
                    ln = self.read_line()
                    if ln is None:
                        action = 'eof'
                        break
                    self.ps = ln
                    self.replaced = False
                elif name == 'N':
                    if self.inp.is_last():
                        action = 'eof'
                        break
                    self.dump_append()
                    ln = self.read_line()
                    if ln is None:
                        action = 'eof'
                        break
                    self.ps = self.ps + '\n' + ln
                    self.replaced = False
                elif name == 'q':
                    self.end_cycle_output()
                    return cmd.arg
                elif name == 'Q':
                    return cmd.arg
                elif name == 'y':
                    src, dst = cmd.arg
                    tbl = dict(zip(src, dst))
                    self.ps = ''.join(tbl.get(ch, ch) for ch in self.ps)
                elif name == 'l':
                    self.emit(self.ps + '$\n')
                elif name == 'F':
                    self.emit('-\n')
            if action == 'end' or action == 'eof':
                self.end_cycle_output()
            elif action == 'delete':
                self.dump_append()
            elif action == 'restart':
                restart = True
        return 2 if self.inp.bad else 0


def usage_error(msg):
    sys.stderr.write('sed: %s\n' % msg)
    return 1


def main(argv):
    argv = [to_str(a) for a in argv]
    nflag = False
    ere = False
    separate = False
    scripts = []
    files = []
    i = 0
    only_files = False
    while i < len(argv):
        a = argv[i]
        i += 1
        if only_files or a == '-' or not a.startswith('-'):
            files.append(a)
            continue
        if a == '--':
            only_files = True
            continue
        if a.startswith('--'):
            if a in ('--quiet', '--silent'):
                nflag = True
            elif a in ('--regexp-extended',):
                ere = True
            elif a == '--separate':
                separate = True
            elif a.startswith('--expression='):
                scripts.append(a[len('--expression='):])
            elif a == '--expression':
                if i >= len(argv):
                    return usage_error('option requires an argument')
                scripts.append(argv[i])
                i += 1
            elif a == '--posix' or a == '--debug' or a == '--sandbox':
                pass
            else:
                return usage_error('unknown option -- %s' % a)
            continue
        j = 1
        while j < len(a):
            c = a[j]
            j += 1
            if c == 'n':
                nflag = True
            elif c in 'Er':
                ere = True
            elif c == 's':
                separate = True
            elif c == 'u' or c == 'z' and False:
                pass
            elif c == 'e':
                if j < len(a):
                    scripts.append(a[j:])
                else:
                    if i >= len(argv):
                        return usage_error('option requires an argument -- e')
                    scripts.append(argv[i])
                    i += 1
                break
            else:
                return usage_error('invalid option -- %s' % c)
    if not scripts:
        if not files:
            return usage_error('no script specified')
        scripts.append(files.pop(0))
    script = '\n'.join(scripts)
    if script.startswith('#n') and (len(script) == 2 or script[2] == '\n'):
        nflag = True
    try:
        cmds = ScriptParser(script, ere).parse()
    except SedError as e:
        sys.stderr.write('sed: -e expression #1: %s\n' % e)
        return 1
    sed = Sed(cmds, nflag, ere, separate, files)
    status = 0
    try:
        status = sed.run()
    except SedError as e:
        sys.stderr.write('sed: %s\n' % e)
        status = 4
    except RecursionError:
        status = 4
    data = ''.join(sed.out).encode('latin-1')
    try:
        sys.stdout.buffer.write(data)
        sys.stdout.buffer.flush()
    except BrokenPipeError:
        pass
    return status


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
