import json, os, subprocess, sys, tempfile
cases = json.load(open(sys.argv[1])); cmd = sys.argv[3:] or ["ed"]
out = []
for cse in cases:
    d = tempfile.mkdtemp(); sd = tempfile.mkdtemp()
    for n, t in cse["files"].items(): open(os.path.join(d, n), "w").write(t)
    sp = os.path.join(sd, "script"); open(sp, "w").write(cse["script"])
    env = {"LC_ALL": "C", "PATH": "/usr/local/bin:/usr/bin:/bin", "HOME": sd}
    try:
        if cse["stdin"] == "file":
            with open(sp, "rb") as f:
                p = subprocess.run(cmd + cse["args"], stdin=f, capture_output=True, cwd=d, env=env, timeout=10)
        else:
            p = subprocess.run(cmd + cse["args"], input=cse["script"].encode(), capture_output=True, cwd=d, env=env, timeout=10)
        files = {}
        for n in sorted(os.listdir(d)):
            fp = os.path.join(d, n)
            files[n] = open(fp, "rb").read().decode("latin-1") if os.path.isfile(fp) else "<dir>"
        r = {"stdout": p.stdout.decode("latin-1"), "status": p.returncode, "stderr": p.stderr.decode("latin-1")[:200], "after": files}
    except subprocess.TimeoutExpired:
        r = {"stdout": "<timeout>", "status": -1, "stderr": "", "after": {}}
    out.append(dict(cse, **r))
json.dump(out, open(sys.argv[2], "w"))
