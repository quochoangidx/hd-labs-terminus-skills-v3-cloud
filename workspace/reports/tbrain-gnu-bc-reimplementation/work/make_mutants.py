"""Build the bc wrong-path mutant trees (environment/app + a mutated reference) and their patches."""
import os, shutil, subprocess, sys
W = "/Users/quochoangdev/HDTechLS/hd-labs-terminus-skills-v3/workspace"
T = W + "/tasks/tbrain-gnu-bc-reimplementation"
R = W + "/reports/tbrain-gnu-bc-reimplementation"
OUT = sys.argv[1]
REF = open(T + "/solution/pybc/bc.py").read()
M = {
 "product-full-scale": [("    ps = min(full, max(scale, a.scale, b.scale))", "    ps = full")],
 "leading-zero-printed": [('            if n.n_len > 1 or d[0] != "0":\n                for k in range(n.n_len):', '            if True:\n                for k in range(n.n_len):')],
 "column-per-number": [("        oc = self.out_char\n        obase = self.obase", "        self.col = 0\n        oc = self.out_char\n        obase = self.obase")],
 "constants-at-block-start": [('''    def run(self, code):
        stack = []''', '''    def run(self, code):
        self.block_ibase = self.ibase
        stack = []'''), ('''                    base = self.ibase if func is None else frames[-1][2]''', '''                    base = self.block_ibase if func is None else frames[-1][2]''')],
 "unary-minus-below-power": [('''        if k == "-":
            self.advance()
            f = self.unary()''', '''        if k == "-":
            self.advance()
            f = self.expression(8)''')],
 "error-ends-program": [('''        except RTError as e:
            sys.stderr.write("Runtime error: %s\\n" % e)''', '''        except RTError as e:
            sys.stderr.write("Runtime error: %s\\n" % e)
            raise Quit()''')],
 "sqrt-scale-ignores-argument": [("    rscale = max(scale, n.scale)\n    point5", "    rscale = scale\n    point5")],
 "print-leaves-last": [('''                    self.store_var("last", v)''', '''                    pass''')],
 "for-header-prints": [('''            if flags & EX_VOID:
                raise SyntaxErr("first expression is void")
            self.gen("p")''', '''            if flags & EX_VOID:
                raise SyntaxErr("first expression is void")
            self.gen("W")''')],
 "array-values-aliased": [("                        self.arrays.setdefault(pname, []).append([dict(src[0]), False])", "                        self.arrays.setdefault(pname, []).append([src[0], False])")],
 "delegate-to-system-bc": [('''    text.append(sys.stdin.buffer.read().decode("latin-1"))''', '''    text.append(sys.stdin.buffer.read().decode("latin-1"))
    if "obase" in "".join(text):
        import subprocess
        sys.stdout.buffer.write(subprocess.run(["/usr/bin/bc"] + argv, input="".join(text).encode("latin-1"), capture_output=True).stdout)
        return 0''')],
}
for name, reps in M.items():
    d = os.path.join(OUT, name)
    shutil.rmtree(d, ignore_errors=True)
    shutil.copytree(T + "/environment/app", d)
    s = REF
    for a, b in reps:
        assert s.count(a) == 1, (name, a[:70])
        s = s.replace(a, b)
    open(d + "/pybc/bc.py", "w").write(s)
    subprocess.run([sys.executable, W + "/tools/mkpatch.py", T + "/environment/app", d, R + "/wrong-paths/%s.patch" % name, "app/"], check=True)
print(sorted(M))
