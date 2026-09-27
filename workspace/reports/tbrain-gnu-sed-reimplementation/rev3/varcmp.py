# usage: varcmp.py <cases-dir> <ref-dir> <var-dir>: cases where the variant differs from the reference
import json, os, subprocess, sys, tempfile
cases_dir, ref, var = sys.argv[1:4]
inputs = json.load(open(os.path.join(cases_dir, "inputs.json")))
text = lambda v: inputs[v[1:]] if isinstance(v, str) and v.startswith("@") else v
def run(py, c):
    d = tempfile.mkdtemp()
    for n, t in c.get("files", []):
        if t is not None: open(os.path.join(d, n), "w", encoding="latin-1").write(text(t))
    a = c["opts"] + ([c["script"]] if c.get("script_arg") else ["-e", c["script"]]) + c.get("extra", []) + [n for n, _ in c.get("files", [])]
    p = subprocess.run(["/usr/local/bin/python3", py] + a, input=text(c["input"]).encode("latin-1"), capture_output=True, cwd=d, env={"LC_ALL": "C"}, timeout=20)
    return p.stdout, p.returncode
n = diff = 0
for name in sorted(os.listdir(cases_dir)):
    if name == "inputs.json": continue
    for fam, rows in json.load(open(os.path.join(cases_dir, name))).items():
        for c in rows:
            n += 1
            if run(os.path.join(ref, "sed.py"), c) != run(os.path.join(var, "sed.py"), c):
                diff += 1; print("DIFF", fam, repr(c["opts"]), repr(c["script"])[:70])
print("cases", n, "differ", diff)
