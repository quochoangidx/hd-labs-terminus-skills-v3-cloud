#!/usr/bin/env python3
"""runcases.py CASES.json INPUTS.json OUT.json [REF_DIR]: run every case through /bin/sed and
(optionally) python3 REF_DIR/sed.py the way tests/test_outputs.py does (fresh dir, LC_ALL=C,
files written latin-1, a null file text = named but absent). Runs inside the task image."""
import json, os, shutil, subprocess, sys, tempfile
cases_path, inputs_path, out_path = sys.argv[1:4]
ref = os.path.abspath(sys.argv[4]) if len(sys.argv) > 4 else None
inputs = json.load(open(inputs_path))
text = lambda v: inputs[v[1:]] if isinstance(v, str) and v.startswith("@") else v
data = json.load(open(cases_path))
ENV = {"LC_ALL": "C", "PATH": "/usr/local/bin:/usr/bin:/bin", "HOME": "/nonexistent"}
def args(c):
    names = [n for n, _ in c.get("files", [])]
    script = [c["script"]] if c.get("script_arg") else ["-e", c["script"]]
    return c["opts"] + script + c.get("extra", []) + names
def run(cmd, c, path):
    try:
        p = subprocess.run(cmd + args(c), input=text(c["input"]).encode("latin-1"), capture_output=True, cwd=path, env=ENV, timeout=5)
        return p.stdout.decode("latin-1"), p.returncode
    except subprocess.TimeoutExpired:
        return None, "timeout"
res = {}
for fam, rows in data.items():
    res[fam] = []
    for c in rows:
        path = tempfile.mkdtemp()
        for n, t in c.get("files", []):
            if t is not None:
                open(os.path.join(path, n), "w", encoding="latin-1").write(text(t))
        g = run(["/bin/sed"], c, path)
        r = run(["python3", os.path.join(ref, "sed.py")], c, path) if ref else None
        shutil.rmtree(path)
        res[fam].append({"case": c, "gnu": g, "ref": r})
json.dump(res, open(out_path, "w"))
