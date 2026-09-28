import json, os, subprocess, sys, tempfile
cases = json.load(open(sys.argv[1])); cmd = sys.argv[3:]
fails = []
for i, c in enumerate(cases):
    d = tempfile.mkdtemp()
    for n, t in c["files"].items(): open(os.path.join(d, n), "w", encoding="latin-1").write(t)
    try:
        p = subprocess.run(cmd + c["args"], input=c["stdin"].encode("latin-1"), capture_output=True, cwd=d, env={"LC_ALL": "C", "PATH": "/usr/bin:/bin"}, timeout=20)
        got = (p.stdout.decode("latin-1"), p.returncode)
    except subprocess.TimeoutExpired:
        got = ("<timeout>", -1)
    if got != (c["stdout"], c["status"]):
        fails.append({"i": i, "args": c["args"], "stdin": c["stdin"], "files": c["files"], "exp": [c["stdout"], c["status"]], "got": list(got), "err": p.stderr.decode()[-300:] if 'p' in dir() else ""})
json.dump(fails, open(sys.argv[2], "w"))
print(len(cases) - len(fails), "/", len(cases))
