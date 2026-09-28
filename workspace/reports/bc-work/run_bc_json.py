import json, subprocess, sys
out = []
for case in json.load(open(sys.argv[1])):
    try:
        p = subprocess.run(["bc"], input=case["input"].encode(), capture_output=True, env={"LC_ALL": "C", "PATH": "/usr/bin:/bin"}, timeout=5)
    except subprocess.TimeoutExpired:
        continue
    out.append({**case, "stdout": p.stdout.decode("latin-1"), "status": p.returncode, "stderr": p.stderr.decode("latin-1")})
json.dump(out, open(sys.argv[2], "w"))
