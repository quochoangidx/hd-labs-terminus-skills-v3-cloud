import os, shutil, subprocess, sys
TASK = "../../../tasks/tbrain-gnu-ed-reimplementation"
M = {
 "loose-exit-ignored": [('''                return 1 if status == FATAL else err_status''', '''                return 1''')],
 "pipe-stops-on-error": [('''            self.interactive = not stat.S_ISREG(os.fstat(0).st_mode)''', '''            self.interactive = False''')],
 "semicolon-keeps-current": [('''                    if ch == ";":
                        self.current = self.second_addr''', '''                    pass''')],
 "undo-not-undoable": [('''        us.reverse()''', '''        us.reverse()
        self.ustack = []''')],
 "leftmost-first-regex": [('''            if best is None or end > best[0]:
                best = (end, caps)''', '''            if best is None:
                best = (end, caps)''')],
 "global-keeps-touched-lines": [('''        if isglobal:
            self.unset_active_nodes(p.next, n)''', '''        pass''')],
 "eof-quits-quietly": [('''                if not self.modified or status == EMOD:
                    status = QUIT''', '''                if True:
                    status = QUIT''')],
 "delegate-to-system-ed": [('''def main(argv):
''', '''def main(argv):
    if "-E" in argv:
        os.execv("/usr/bin/ed", ["ed"] + argv)
''')],
 "w-for-W": [('''"a" if c == "W" else "w"''', '''"w"''')],
}
for mid, patches in M.items():
    d = os.path.join("mut", mid, "app")
    shutil.rmtree(os.path.join("mut", mid), ignore_errors=True)
    shutil.copytree(os.path.join(TASK, "environment/app"), d)
    for f in ("ed.py", "posixre.py"):
        shutil.copy(os.path.join(TASK, "solution/pyed", f), os.path.join(d, "pyed", f))
    for a, b in patches:
        hit = False
        for f in ("ed.py", "posixre.py"):
            p = os.path.join(d, "pyed", f); s = open(p).read()
            if a in s:
                open(p, "w").write(s.replace(a, b, 1)); hit = True; break
        assert hit, (mid, a[:50])
    subprocess.run([sys.executable, "../../../tools/mkpatch.py", os.path.join(TASK, "environment/app"), d, f"../wrong-paths/{mid}.patch", "app/"], check=True)
print("ok", list(M))
