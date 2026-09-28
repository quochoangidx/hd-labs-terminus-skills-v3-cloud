import json, os, subprocess, sys, tempfile
from collections import defaultdict
exp = json.load(open(sys.argv[1])); res = defaultdict(lambda: [0, 0]); fails = []
for e in exp:
    d = tempfile.mkdtemp(); sd = tempfile.mkdtemp()
    for n, t in e["files"].items(): open(os.path.join(d, n), "w").write(t)
    sp = os.path.join(sd, "script"); open(sp, "w").write(e["script"])
    env = {"LC_ALL": "C", "PATH": "/usr/local/bin:/usr/bin:/bin", "HOME": sd}
    cmd = [sys.executable, "/app/pyed/ed.py"] + e["args"]
    try:
        if e["stdin"] == "file":
            with open(sp, "rb") as f: p = subprocess.run(cmd, stdin=f, capture_output=True, cwd=d, env=env, timeout=20)
        else:
            p = subprocess.run(cmd, input=e["script"].encode(), capture_output=True, cwd=d, env=env, timeout=20)
        files = {}
        for n in sorted(os.listdir(d)):
            fp = os.path.join(d, n); files[n] = open(fp, "rb").read().decode("latin-1") if os.path.isfile(fp) else "<dir>"
        got = (p.stdout.decode("latin-1"), p.returncode == 0, files)
    except subprocess.TimeoutExpired:
        got = ("<timeout>", None, {})
    ok = got == (e["stdout"], e["status"] == 0, e["after"]); res[e["group"]][0 if ok else 1] += 1
    if not ok: fails.append({"group": e["group"], "args": e["args"], "stdin": e["stdin"], "script": e["script"], "files": e["files"], "exp": [e["stdout"], e["status"], e["after"]], "got": list(got)})
for g, (p, f) in sorted(res.items()): print(f"{'PASS' if not f else 'FAIL'} {g}: {p}/{p+f}")
print("groups passed", sum(1 for v in res.values() if not v[1]), "/", len(res), "cases", sum(v[0] for v in res.values()), "/", len(exp))
json.dump(fails, open(os.environ.get("FAILS", "/tmp/fails.json"), "w"), indent=1)
