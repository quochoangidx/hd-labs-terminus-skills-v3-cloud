#!/usr/bin/env python3
"""mkmut.py <task> <outdir> [ids...]: the panel mutants of return 09c61abb v1 (findings 1-7),
built from the task's reference by exact string replacement; writes <outdir>/<id>/app and
<outdir>/<id>.patch (a patch against environment/app, as wrong_path_runner.py applies it)."""
import os, shutil, subprocess, sys, tempfile
task, outdir = sys.argv[1:3]

MUTANTS = {
 # f1: a reader that keeps only the first 64 characters of every input line
 "line-cap-64": [("sed.py", """        if parts and parts[-1] == "":
            parts.pop()
""", """        if parts and parts[-1] == "":
            parts.pop()
        parts = [p[:64] for p in parts]
""")],
 # f2: addr1,+N and addr1,~N read one digit
 "special-range-one-digit": [("sed.py", """                        cmd.a2 = (kind, self.number())
""", """                        cmd.a2 = (kind, int(self.s[self.i]))
                        self.i += 1
""")],
 # f3: interval bounds read one digit
 "interval-one-digit": [("posixre.py", """        while self.peek() and self.peek().isdigit():
            num += self.peek()""", """        if self.peek() and self.peek().isdigit():
            num += self.peek()"""), ("posixre.py", """            while self.peek() and self.peek().isdigit():
                num2 += self.peek()""", """            if self.peek() and self.peek().isdigit():
                num2 += self.peek()""")],
 # f4: a bare q exits 0 even after an unreadable file was reached; q N and Q N keep 2
 "bare-q-clears-status": [("sed.py", """                cmd.arg = self.number() if self.peek() is not None and self.peek().isdigit() else 0
""", """                cmd.arg = self.number() if self.peek() is not None and self.peek().isdigit() else None
"""), ("sed.py", """                elif name == "q":
                    quit_code = cmd.arg
""", """                elif name == "q":
                    quit_code = cmd.arg if cmd.arg is not None else 0
                    if cmd.arg is None:
                        self.inp.status = 0
"""), ("sed.py", """                elif name == "Q":
                    return cmd.arg
""", """                elif name == "Q":
                    return cmd.arg or 0
""")],
 # f5: a BRE $ is an anchor only at the end of the regex or before \\), not before \\|
 "bre-dollar-before-alt-literal": [("posixre.py", """            if self.ere or self.peek() is None or self.at_close() or self.at_alt():""",
  """            if self.ere or self.peek() is None or self.at_close():""")],
 # f6: -n, -E and -s together lose -s
 "nes-together-drops-s": [("sed.py", """    if not scripts:
        if not files:""", """    if quiet and ere and separate:
        separate = False
    if not scripts:
        if not files:""")],
 # f7: ? rejected as the s delimiter
 "question-delimiter-rejected": [("sed.py", """                delim = self.peek()
                self.i += 1
                pat = self.read_delimited(delim)""", """                delim = self.peek()
                if delim == "?":
                    raise Usage("? is not a delimiter")
                self.i += 1
                pat = self.read_delimited(delim)""")],
}
env_app = os.path.join(task, "environment", "app")
ids = sys.argv[3:] or list(MUTANTS)
for mid in ids:
    tmp = tempfile.mkdtemp()
    orig, mut = os.path.join(tmp, "orig", "app"), os.path.join(tmp, "mut", "app")
    shutil.copytree(env_app, orig)
    shutil.copytree(env_app, mut)
    for f in os.listdir(os.path.join(task, "solution", "pysed")):
        shutil.copy(os.path.join(task, "solution", "pysed", f), os.path.join(mut, "pysed", f))
    for fname, old, new in MUTANTS[mid]:
        p = os.path.join(mut, "pysed", fname)
        src = open(p).read()
        assert src.count(old) == 1, (mid, fname, src.count(old))
        open(p, "w").write(src.replace(old, new))
    d = subprocess.run(["git", "diff", "--no-index", "--no-color", "orig/app", "mut/app"], cwd=tmp, capture_output=True, text=True).stdout
    d = d.replace("a/orig/app/", "a/app/").replace("b/mut/app/", "b/app/").replace("a/mut/app/", "a/app/").replace("b/orig/app/", "b/app/")
    os.makedirs(outdir, exist_ok=True)
    open(os.path.join(outdir, mid + ".patch"), "w").write(d)
    shutil.rmtree(os.path.join(outdir, mid), ignore_errors=True)
    shutil.copytree(os.path.join(tmp, "mut"), os.path.join(outdir, mid))
    shutil.rmtree(tmp)
    print("built", mid)
