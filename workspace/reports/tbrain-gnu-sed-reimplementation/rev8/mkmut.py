#!/usr/bin/env python3
"""mkmut.py <task> <outdir>: build the rev8 wrong paths from the task's reference.
Each is a set of exact string replacements on solution/pysed; writes <outdir>/<id>/app and
<outdir>/<id>.patch (a patch against environment/app, as wrong_path_runner.py applies it)."""
import os, shutil, subprocess, sys, tempfile
task, outdir = sys.argv[1:3]

MUTANTS = {
 "long-line-chunked-reader": [("sed.py", """        if parts and parts[-1] == "":
            parts.pop()
""", """        if parts and parts[-1] == "":
            parts.pop()
        # a readline(1024) reader: a longer physical line comes back in chunks
        parts = [p[k:k + 1024] for p in parts for k in range(0, max(len(p), 1), 1024)]
""")],
 "plus-offset-one-digit": [("sed.py", """                        cmd.a2 = (kind, self.number())
""", """                        if kind == "plus":
                            cmd.a2 = (kind, int(self.s[self.i]))
                            self.i += 1
                        else:
                            cmd.a2 = (kind, self.number())
""")],
 "interval-bounds-one-digit": [("posixre.py", """        while self.peek() and self.peek().isdigit():
            num += self.peek()""", """        if self.peek() and self.peek().isdigit():
            num += self.peek()"""), ("posixre.py", """            while self.peek() and self.peek().isdigit():
                num2 += self.peek()""", """            if self.peek() and self.peek().isdigit():
                num2 += self.peek()""")],
 "cntrl-without-del": [("posixre.py", """"cntrl": "".join(chr(i) for i in range(32)) + "\\x7f",""", """"cntrl": "".join(chr(i) for i in range(32)),""")],
 "s-backslash-delimiter-rejected": [("sed.py", """                delim = self.peek()
                self.i += 1
                pat = self.read_delimited(delim)""", """                delim = self.peek()
                if delim == "\\\\":
                    raise Usage("backslash is kept for escapes")
                self.i += 1
                pat = self.read_delimited(delim)""")],
 "empty-regex-bound-at-parse-time": [("sed.py", """        if src == "":
            return None  # the empty regex: the last regex used
        return Regex(conv_escapes(src, True), self.ere)""", """        if src == "":
            return getattr(self, "prev_regex", None)  # the regex written before it
        self.prev_regex = Regex(conv_escapes(src, True), self.ere)
        return self.prev_regex""")],
 "leading-hyphen-starts-range": [("posixre.py", """                lo = "\\n"
            if self.peek() == "-" and self.peek(1) not in ("]", None):""", """                lo = "\\n"
            if c == "-" and self.peek() not in ("]", None) and len(chars) == 0:
                hi = self.peek()
                self.i += 1
                chars.update(chr(k) for k in range(ord("-"), ord(hi) + 1))
                continue
            if self.peek() == "-" and self.peek(1) not in ("]", None):""")],
 "readds-site-packages": [("sed.py", """import sys
""", """import sys
if "-s" in sys.argv:
    sys.path.append("/usr/local/lib/python3.13/site-packages")
    import pytest  # noqa: F401  (a package that only the verifier image has)
""")],
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
