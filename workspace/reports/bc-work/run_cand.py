import json, subprocess, sys
res = []
for case in json.load(open(sys.argv[1])):
    try:
        p = subprocess.run(["python3", "/app/pybc/bc.py"], input=case["input"].encode(), capture_output=True, env={"LC_ALL": "C", "PATH": "/usr/local/bin:/usr/bin:/bin"}, timeout=20)
        res.append({"stdout": p.stdout.decode("latin-1"), "status": p.returncode})
    except subprocess.TimeoutExpired:
        res.append({"stdout": None, "status": "timeout"})
json.dump(res, sys.stdout)
