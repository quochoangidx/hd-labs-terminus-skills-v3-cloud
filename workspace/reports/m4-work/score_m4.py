import json, os, subprocess, sys, tempfile
from collections import defaultdict
exp = json.load(open(sys.argv[1])); res = defaultdict(lambda: [0, 0]); fails = []
for e in exp:
    d = tempfile.mkdtemp(); files = dict(e["files"])
    if e["src"]: files["in.m4"] = e["src"]
    for n, t in files.items(): open(os.path.join(d, n), "w").write(t)
    try:
        p = subprocess.run([sys.executable, "/app/pym4/m4.py"] + e["args"], input=e["stdin"].encode(), capture_output=True, cwd=d, env={"LC_ALL": "C", "PATH": "/usr/local/bin:/usr/bin:/bin"}, timeout=20)
        got = (p.stdout.decode("latin-1"), p.returncode)
    except subprocess.TimeoutExpired:
        got = ("<timeout>", -1)
    ok = got == (e["stdout"], e["status"]); res[e["group"]][0 if ok else 1] += 1
    if not ok: fails.append({"group": e["group"], "src": e["src"], "args": e["args"], "exp": [e["stdout"], e["status"]], "got": list(got)})
for g, (p, f) in sorted(res.items()): print(f"{'PASS' if not f else 'FAIL'} {g}: {p}/{p+f}")
print("groups passed", sum(1 for v in res.values() if not v[1]), "/", len(res), "cases", sum(v[0] for v in res.values()), "/", len(exp))
json.dump(fails, open(os.environ.get("FAILS", "/tmp/fails.json"), "w"), indent=1)
