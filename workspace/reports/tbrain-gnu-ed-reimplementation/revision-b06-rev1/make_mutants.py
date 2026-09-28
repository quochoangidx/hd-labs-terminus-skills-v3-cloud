"""Wrong paths for this revision's findings: the repaired reference with one plausible
mistake each, written as a patch from the stub the agent starts with."""
import os, shutil, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
WS = os.path.join(HERE, "../../..")
TASK = os.path.join(WS, "tasks/tbrain-gnu-ed-reimplementation")
RETURNED = os.path.join(WS, "returned/tbrain-gnu-ed-reimplementation")
TOOLS = os.path.join(WS, "tools")
M = {
 # finding 1: the returned reference, whose bounded-run memo is shared across starts even with a back-reference
 "backref-run-memo-shared": "RETURNED_POSIXRE",
 # finding 5: open-ended repeats stop after 64
 "open-repeat-cap-64": [('''            sub, lo, hi = node[1], node[2], node[3]
''', '''            sub, lo, hi = node[1], node[2], node[3]
            if hi is None:
                hi = max(lo, 64)
''')],
 # finding 6: f is refused inside a global command list
 "global-f-refused": [('''        elif c == "f":
''', '''        elif c == "f" and isglobal:
            self.set_error("Unknown command")
            return ERR
        elif c == "f":
''')],
 # finding 6's class: e, E, W, Q and # are refused inside a global command list
 "global-file-commands-refused": [('''        skip_blanks(cmd)
        c = cmd.ch()
        cmd.i += 1
        if c == "a":''', '''        skip_blanks(cmd)
        c = cmd.ch()
        cmd.i += 1
        if isglobal and c in "eEWQ#":
            self.set_error("Unknown command")
            return ERR
        if c == "a":''')],
 # finding 7: a g or v nested inside v runs instead of failing
 "v-allows-nested-global": [('''        elif c in "gvGV":
            if isglobal:''', '''        elif c in "gvGV":
            if isglobal and not getattr(self, "in_v", False):'''), ('''            match = c in "gG"
''', '''            match = c in "gG"
            self.in_v = not match
''')],
 # finding 8: the extended parser checks only the lower bound against 32767
 "ere-upper-bound-unchecked": [('''        if lo > DUP_MAX or (hi is not None and hi > DUP_MAX):''', '''        if lo > DUP_MAX or (hi is not None and hi > DUP_MAX and not self.ere):''')],
 # finding 10: only the marks a, b and x are accepted
 "marks-a-b-x-only": [('''            k = ord(n) - ord("a")
            if k < 0 or k >= 26:''', '''            k = ord(n) - ord("a")
            if k < 0 or k >= 26 or n not in "abx":'''), ('''        k = ord(c) - ord("a")
        if k < 0 or k >= 26:''', '''        k = ord(c) - ord("a")
        if k < 0 or k >= 26 or c not in "abx":''')],
 # finding 12: a decimal address above 33 is refused
 "line-number-cap-33": [('''                n = self.parse_int(cmd)
                if n is None:
                    return -1
                if first:''', '''                n = self.parse_int(cmd)
                if n is None or n > 33:
                    self.invalid_address()
                    return -1
                if first:''')],
 # finding 13: a numeric offset larger than two is refused
 "offset-magnitude-2": [('''                if cmd.ch(1).isdigit():
                    n = self.parse_int(cmd)
                    if n is None:
                        return -1''', '''                if cmd.ch(1).isdigit():
                    n = self.parse_int(cmd)
                    if n is None or abs(n) > 2:
                        self.invalid_address()
                        return -1''')],
 # finding 14: four bare signs in a row are refused
 "bare-signs-max-3": [('''                else:
                    cmd.i += 1
                    self.second_addr += 1 if ch == "+" else -1''', '''                else:
                    if cmd.s[cmd.i:cmd.i + 4] in ("++++", "----"):
                        self.invalid_address()
                        return -1
                    cmd.i += 1
                    self.second_addr += 1 if ch == "+" else -1''')],
 # finding 5's class: an s count above 64 is refused
 "s-count-cap-64": [('''                if rep or n is None or n <= 0:''', '''                if rep or n is None or n <= 0 or n > 64:''')],
}
out = os.path.join(HERE, "wrong-paths")
os.makedirs(out, exist_ok=True)
for mid, patches in M.items():
    root = os.path.join(HERE, "work", "mut", mid)
    shutil.rmtree(root, ignore_errors=True)
    d = os.path.join(root, "app")
    shutil.copytree(os.path.join(TASK, "environment/app"), d)
    for f in ("ed.py", "posixre.py"):
        shutil.copy(os.path.join(TASK, "solution/pyed", f), os.path.join(d, "pyed", f))
    if patches == "RETURNED_POSIXRE":
        shutil.copy(os.path.join(RETURNED, "solution/pyed/posixre.py"), os.path.join(d, "pyed/posixre.py"))
        patches = []
    for a, b in patches:
        hit = False
        for f in ("ed.py", "posixre.py"):
            p = os.path.join(d, "pyed", f); s = open(p).read()
            if a in s:
                assert s.count(a) == 1, (mid, a[:40])
                open(p, "w").write(s.replace(a, b, 1)); hit = True; break
        assert hit, (mid, a[:50])
    subprocess.run([sys.executable, os.path.join(TOOLS, "mkpatch.py"), os.path.join(TASK, "environment/app"), d,
                    os.path.join(out, f"{mid}.patch"), "app/"], check=True)
print("ok", list(M))
