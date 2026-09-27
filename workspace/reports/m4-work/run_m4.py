import json, os, subprocess, sys, tempfile
cases = json.load(open(sys.argv[1])); cmd = sys.argv[3:] or ["m4"]
out = []
for cse in cases:
    d = tempfile.mkdtemp()
    files = dict(cse["files"])
    if cse["src"]: files["in.m4"] = cse["src"]
    for n, t in files.items(): open(os.path.join(d, n), "w").write(t)
    try:
        p = subprocess.run(cmd + cse["args"], input=cse["stdin"].encode(), capture_output=True, cwd=d, env={"LC_ALL": "C", "PATH": "/usr/local/bin:/usr/bin:/bin"}, timeout=10)
        r = {"stdout": p.stdout.decode("latin-1"), "status": p.returncode, "stderr": p.stderr.decode("latin-1")[:200]}
    except subprocess.TimeoutExpired:
        r = {"stdout": "<timeout>", "status": -1, "stderr": ""}
    out.append(dict(cse, **r))
json.dump(out, open(sys.argv[2], "w"))
