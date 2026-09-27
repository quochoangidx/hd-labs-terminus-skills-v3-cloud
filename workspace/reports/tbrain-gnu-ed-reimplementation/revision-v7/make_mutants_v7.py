"""Wrong paths for the v7 findings kept in scope: each is the reference with one plausible
mistake, written as a patch from the stub the agent starts with."""
import os, shutil, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
TASK = os.path.join(HERE, "../../../tasks/tbrain-gnu-ed-reimplementation")
TOOLS = os.path.join(HERE, "../../../tools")
OUT = os.path.join(HERE, "../wrong-paths")
M = {
 # findings 1 and 17: a stdin reader with a 199-byte line buffer
 "stdin-line-cap-199": [('''        line = self.stdin[self.sin:j + 1]
        self.sin = j + 1''', '''        line = self.stdin[self.sin:j + 1]
        if len(line) > 200:
            j = self.sin + 199 - 1
            line = self.stdin[self.sin:j + 1] + "\\n"
            self.stdin = self.stdin[:j + 1] + "\\n" + self.stdin[j + 1:]
        self.sin = j + 1''')],
 # finding 16: a file reader that splits a line at byte 199
 "file-line-cap-199": [('''            with open(filename, "rb") as f:
                data = f.read().decode("latin-1")''', '''            with open(filename, "rb") as f:
                data = f.read().decode("latin-1")
            data = "\\n".join(l[:199] + ("\\n" + l[199:] if len(l) > 199 else "") for l in data.split("\\n"))''')],
 # finding 2: collating elements and equivalence classes only in basic expressions
 "ere-no-collating": [('''        if c == "[" and self.peek(1) in (":", "=", "."):''', '''        if c == "[" and self.ere and self.peek(1) in ("=", "."):
            raise RegexError("unsupported bracket element")
        if c == "[" and self.peek(1) in (":", "=", "."):''')],
 # finding 3: the count limit checked only on bounded intervals
 "open-interval-unchecked": [('''        if lo > DUP_MAX or (hi is not None and hi > DUP_MAX):''', '''        if hi is not None and (lo > DUP_MAX or hi > DUP_MAX):''')],
 # finding 4: the repeat form refuses p after r
 "repeat-rp-refused": [('''            elif ch == "p":
                if sflags & 2:''', '''            elif ch == "p":
                if sflags & 2 or sflags & 4:''')],
 # finding 18: a buffer capped at 4000 lines
 "line-count-cap-4000": [('''    def copy_lines(self, first, second, addr):
        np = self.search_line_node(first)''', '''    def copy_lines(self, first, second, addr):
        if self.last + second - first + 1 > 4000:
            self.set_error("Too many lines")
            return False
        np = self.search_line_node(first)''')],
 # finding 19: subexpressions nested at most two deep
 "nesting-depth-two": [('''    def group(self):
        self.ngroups += 1''', '''    def group(self):
        self.depth = getattr(self, "depth", 0) + 1
        if self.depth > 2:
            raise RegexError("nesting too deep")
        self.ngroups += 1'''), ('''        self.i += 1 if self.ere else 2
        return ("group", idx, inner)''', '''        self.i += 1 if self.ere else 2
        self.depth -= 1
        return ("group", idx, inner)''')],
 # finding 23: backslash continuation honoured for w and W only, not for e, E, f and r
 "filename-no-continuation": [('''        if cmd.ch() != "\\n":
            if not self.get_extended_line(cmd, True):
                return None
        elif not trad_f''', '''        if cmd.ch() != "\\n":
            if cmd.s[:cmd.i].rstrip(" \\t")[-1:] in "wWq" and not self.get_extended_line(cmd, True):
                return None
        elif not trad_f''')],
 # finding 25: W makes its file the default filename
 "W-sets-default-filename": [('''            if not self.def_filename:
                self.def_filename = fnp
            addr = self.write_file(fnp or self.def_filename, "a" if c == "W" else "w"''', '''            if not self.def_filename or (c == "W" and fnp):
                self.def_filename = fnp
            addr = self.write_file(fnp or self.def_filename, "a" if c == "W" else "w"''')],
 # findings 13 and 14: Unicode case folding (the returned reference)
 "unicode-case-folding": [('''        if self.icase and ch in string.ascii_letters:
            return ("set", frozenset({ch, ch.translate(ASCII_FOLD)}), False)''', '''        if self.icase and ch.isalpha():
            return ("set", frozenset({ch.lower(), ch.upper()}), False)''')],
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
