# usage (inside pyfind-task with candidate app at /app): python3 score_find.py battery.py exp.json
import json, os, subprocess, sys, tempfile, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fixtures import FIXTURES
from build import build
exp = json.load(open(sys.argv[2]))
ns = {}; exec(open(sys.argv[1]).read(), ns)
bad = 0; fails = []
for e in exp:
    d = tempfile.mkdtemp(); build(d, FIXTURES[e["fixture"]], time.time())
    try:
        p = subprocess.run([sys.executable, "/app/pyfind/find.py"] + e["args"], capture_output=True, cwd=d, env={"LC_ALL": "C", "TZ": "UTC", "PATH": "/usr/local/bin:/usr/bin:/bin"}, timeout=20)
        got = (p.stdout.decode("latin-1"), p.returncode)
    except subprocess.TimeoutExpired:
        got = ("<timeout>", -1)
    if got != (e["stdout"], e["status"]):
        bad += 1; fails.append({"fixture": e["fixture"], "args": e["args"], "exp": [e["stdout"], e["status"]], "got": list(got)})
print(f"{len(exp)-bad}/{len(exp)} pass")
json.dump(fails, open(os.environ.get("FAILS", "/tmp/fails.json"), "w"), indent=1)
