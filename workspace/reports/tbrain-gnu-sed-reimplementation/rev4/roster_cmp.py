# Runs every roster case (tests/cases) through GNU sed and each pysed dir given; writes per-case results.
# usage: roster_cmp.py <cases-dir> <out.json> name=dir ...
import json, os, subprocess, sys, tempfile
cases_dir, out = sys.argv[1], sys.argv[2]
impls = dict(a.split("=", 1) for a in sys.argv[3:])
inputs = json.load(open(os.path.join(cases_dir, "inputs.json")))
text = lambda v: inputs[v[1:]] if isinstance(v, str) and v.startswith("@") else v
def args(c):
    return c["opts"] + ([c["script"]] if c.get("script_arg") else ["-e", c["script"]]) + c.get("extra", []) + [n for n, _ in c.get("files", [])]
def run(cmd, c):
    d = tempfile.mkdtemp()
    for n, t in c.get("files", []):
        if t is not None: open(os.path.join(d, n), "w", encoding="latin-1").write(text(t))
    try:
        p = subprocess.run(cmd + args(c), input=text(c["input"]).encode("latin-1"), capture_output=True, cwd=d,
                           env={"LC_ALL": "C", "PATH": "/usr/local/bin:/usr/bin:/bin"}, timeout=10)
        return [p.stdout.decode("latin-1"), p.returncode]
    except subprocess.TimeoutExpired:
        return [None, "timeout"]
res = []
for name in sorted(os.listdir(cases_dir)):
    if name == "inputs.json" or not name.endswith(".json"): continue
    for fam, rows in json.load(open(os.path.join(cases_dir, name))).items():
        for i, c in enumerate(rows):
            g = run(["/bin/sed"], c)
            row = {"file": name, "family": fam, "idx": i, "script": c["script"], "opts": c["opts"], "gnu": g}
            for k, d in impls.items():
                row[k] = run(["/usr/local/bin/python3", d + "/sed.py"], c)
            res.append(row)
json.dump(res, open(out, "w"), indent=0)
for k in impls:
    bad = [r for r in res if r[k] != r["gnu"]]
    print(k, "differs on", len(bad))
    for r in bad[:40]: print("   ", r["family"], r["idx"], repr(r["script"])[:90])
