import os, shutil, subprocess, sys
TASK = "../../../tasks/tbrain-gnu-dc-reimplementation"
M = {
 "mul-full-scale": [("    ps = min(full, max(scale, a.scale, b.scale))", "    ps = full")],
 "empty-register-l-nothing": [("        if not st:\n            return True, ZERO()", "        if not st:\n            return False, None")],
 "q-one-level": [("            self.unwind_depth = 1\n            self.unwind_noexit = False\n            return QUIT", "            self.unwind_depth = 0\n            self.unwind_noexit = False\n            return QUIT")],
 "no-line-split": [("        lm = self.line_max\n", "        lm = 0\n")],
 "hex-lowercase": [('REF_STR = "0123456789ABCDEF"', 'REF_STR = "0123456789abcdef"')],
 "Z-counts-leading-zeros": [("    while 1 < i and d[k] == \"0\":\n        i -= 1\n        k += 1\n    return i", "    return i")],
 "negcmp-ignored": [("            if peekc in (\"<\", \"=\", \">\"):\n                return NEGCMP", "            if peekc in (\"<\", \"=\", \">\"):\n                return OKAY")],
 "delegate-to-system-dc": [("def main(argv):\n", "def main(argv):\n    if \"-f\" in argv:\n        os.execv(\"/usr/bin/dc\", [\"dc\"] + argv)\n")],
}
for mid, patches in M.items():
    d = os.path.join("mut", mid, "app")
    shutil.rmtree(os.path.join("mut", mid), ignore_errors=True)
    shutil.copytree(os.path.join(TASK, "environment/app"), d)
    shutil.copy(os.path.join(TASK, "solution/pydc/dc.py"), os.path.join(d, "pydc", "dc.py"))
    p = os.path.join(d, "pydc", "dc.py"); s = open(p).read()
    for a, b in patches:
        assert a in s, (mid, a[:50]); s = s.replace(a, b, 1)
    open(p, "w").write(s)
    subprocess.run([sys.executable, "../../../tools/mkpatch.py", os.path.join(TASK, "environment/app"), d, f"../wrong-paths/{mid}.patch", "app/"], check=True)
print("ok", list(M))
