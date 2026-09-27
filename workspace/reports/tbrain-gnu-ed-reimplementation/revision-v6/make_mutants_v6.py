"""Wrong paths for the v6 findings kept in scope: each is the reference with one plausible
mistake, written as a patch from the stub the agent starts with."""
import os, shutil, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
TASK = os.path.join(HERE, "../../../tasks/tbrain-gnu-ed-reimplementation")
TOOLS = os.path.join(HERE, "../../../tools")
OUT = os.path.join(HERE, "../wrong-paths")
M = {
 # finding 11
 "addressed-undo-accepted": [('''        elif c == "u":
            if self.unexpected_address(cnt) or not self.get_command_suffix''', '''        elif c == "u":
            if not self.get_command_suffix''')],
 # finding 12
 "zero-lower-bound-rejected": [('''        lo = int(num) if num else 0
        hi = lo''', '''        lo = int(num) if num else 0
        if num and lo == 0:
            raise RegexError("bad interval")
        hi = lo''')],
 # finding 13
 "append-suffix-ignored": [('''        if c == "a":
            if not self.get_command_suffix(cmd, pflags):
                return ERR''', '''        if c == "a":
            if not self.get_command_suffix(cmd, pflags):
                return ERR
            pflags[0] = 0''')],
 # finding 14
 "tab-separator-rejected": [('''    def unexpected_command_suffix(self, ch):
        if not ch.isspace():''', '''    def unexpected_command_suffix(self, ch):
        if ch not in " \\n":''')],
 # finding 15
 "join-keeps-mark": [('''        buf = ""
        while bp is not ep:''', '''        buf = ""
        kept = [k for k, m in enumerate(self.marks) if m is bp]
        while bp is not ep:'''), ('''        self.put_sbuf_line(buf + "\\n")
        self.push_undo(UADD, self.current, self.current)
        self.modified = True
        return True''', '''        self.put_sbuf_line(buf + "\\n")
        self.push_undo(UADD, self.current, self.current)
        for k in kept:
            self.marks[k] = self.search_line_node(self.current)
        self.modified = True
        return True''')],
 # finding 17
 "open-s-prints-first-line": [('''            if cmd.ch() == "\\n":
                self.s_pflags = PF_P
            else:''', '''            self.open_end = cmd.ch() == "\\n"
            if cmd.ch() == "\\n":
                self.s_pflags = PF_P
            else:'''), ('''        pflags[0] = self.s_pflags
        if not isglobal:
            self.clear_undo_stack()
        return self.search_and_replace(self.first_addr, self.second_addr, self.snum, isglobal)''', '''        pflags[0] = self.s_pflags
        if not isglobal:
            self.clear_undo_stack()
        ok = self.search_and_replace(self.first_addr, self.second_addr, self.snum, isglobal)
        if ok and not isglobal and not sflags and self.open_end and self.first_addr < self.current:
            pflags[0] = 0
            self.write(self.search_line_node(self.first_addr).text)
        return ok''')],
 # finding 18
 "repeat-form-accepts-n": [('''            elif ch == "r":
                if sflags & 4:''', '''            elif ch == "n" and cmd.s[cmd.i + 1:cmd.i + 2] == "\\n" and not sflags & 2:
                sflags |= 2
                cmd.i += 1
            elif ch == "r":
                if sflags & 4:''')],
 # finding 21
 "E-count-ignores-s": [('''            if self.read_file(fnp or self.def_filename, 0, load=True) < 0:
                return ERR
            self.reset_undo_state()''', '''            quiet = self.scripted
            if c == "E":
                self.scripted = False
            got = self.read_file(fnp or self.def_filename, 0, load=True)
            self.scripted = quiet
            if got < 0:
                return ERR
            self.reset_undo_state()''')],
 # finding 3 (disputed; pinned)
 "leading-hyphen-starts-range": [('''            first = False
            kind, value = self.bracket_item()''', '''            if first and c == "-" and self.peek(1) not in ("]", None):
                self.i += 1
                first = False
                hi_kind, hi_value = self.bracket_item()
                if hi_kind == "char" and ord(hi_value) >= ord("-"):
                    for k in range(ord("-"), ord(hi_value) + 1):
                        chars.add(chr(k))
                    continue
                chars.add("-")
                if hi_kind == "char":
                    chars.add(hi_value)
                else:
                    chars |= hi_value
                continue
            first = False
            kind, value = self.bracket_item()''')],
 # finding 4 (disputed; errata 18)
 "global-s-without-match-fails": [('''        if not match_found and not isglobal:''', '''        if not match_found:''')],
 # finding 28 (the route the returned launcher missed)
 "fork-exec-helper-delegation": [('''def main(argv):
''', '''def main(argv):
    if "-E" in argv:
        import _posixsubprocess
        r, w = os.pipe()
        pid = _posixsubprocess.fork_exec(
            [b"/bin/true"], [b"/bin/true"], True, (w,), None, None, -1, -1, -1, -1, -1, -1,
            r, w, False, False, -1, None, None, None, -1, None, False)
        os.waitpid(pid, 0)
''')],
}
for mid, patches in M.items():
    root = os.path.join(HERE, "work", "mut", mid)
    shutil.rmtree(root, ignore_errors=True)
    d = os.path.join(root, "app")
    shutil.copytree(os.path.join(TASK, "environment/app"), d)
    for f in ("ed.py", "posixre.py"):
        shutil.copy(os.path.join(TASK, "solution/pyed", f), os.path.join(d, "pyed", f))
    for a, b in patches:
        hit = False
        for f in ("ed.py", "posixre.py"):
            p = os.path.join(d, "pyed", f); s = open(p).read()
            if a in s:
                assert s.count(a) == 1, (mid, a[:40])
                open(p, "w").write(s.replace(a, b, 1)); hit = True; break
        assert hit, (mid, a[:50])
    subprocess.run([sys.executable, os.path.join(TOOLS, "mkpatch.py"), os.path.join(TASK, "environment/app"), d,
                    os.path.join(OUT, f"{mid}.patch"), "app/"], check=True)
print("ok", list(M))
