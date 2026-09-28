# Runs each probe through GNU sed 4.9 and a pysed dir; prints both. usage: cmp.py <pysed-dir> <probes.json>
import json, os, subprocess, sys, tempfile
pysed, probes = sys.argv[1], json.load(open(sys.argv[2]))
def run(cmd, p):
    d = tempfile.mkdtemp()
    for n, t in p.get("files", []):
        if t is not None: open(os.path.join(d, n), "w", encoding="latin-1").write(t)
    r = subprocess.run(cmd + p["args"], input=p.get("input", "").encode("latin-1"), capture_output=True, cwd=d,
                       env={"LC_ALL": "C", "PATH": "/usr/bin:/bin"}, timeout=10)
    return r.stdout, r.returncode
for p in probes:
    g = run(["/bin/sed"], p); r = run(["/usr/local/bin/python3", pysed + "/sed.py"], p)
    print("SAME" if g == r else "DIFF", p["id"], p["args"], "gnu=", g, "ref=", r)
