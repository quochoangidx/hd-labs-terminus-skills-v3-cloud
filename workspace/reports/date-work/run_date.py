import json, os, subprocess, sys, tempfile
cases = json.load(open(sys.argv[1])); cmd = sys.argv[3:] or ["date"]
out = []
for cse in cases:
    d = tempfile.mkdtemp()
    for n, t in cse["files"].items(): open(os.path.join(d, n), "w").write(t)
    try:
        p = subprocess.run(cmd + cse["args"], capture_output=True, cwd=d, env={"LC_ALL": "C", "TZ": "UTC0", "PATH": "/usr/local/bin:/usr/bin:/bin"}, timeout=20)
        r = {"stdout": p.stdout.decode("latin-1"), "status": p.returncode, "stderr": p.stderr.decode("latin-1")[:160]}
    except subprocess.TimeoutExpired:
        r = {"stdout": "<timeout>", "status": -1, "stderr": ""}
    out.append(dict(cse, **r))
json.dump(out, open(sys.argv[2], "w"))
