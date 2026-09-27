import json, os, subprocess, sys, tempfile, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fixtures import FIXTURES
from build import build
ns = {}; exec(open(sys.argv[1]).read(), ns)
cmd = sys.argv[3].split() if len(sys.argv) > 3 else ["find"]
out = []
for fx, args in ns["A"]:
    d = tempfile.mkdtemp()
    now = time.time()
    build(d, FIXTURES[fx], now)
    p = subprocess.run(cmd + args, capture_output=True, cwd=d, env={"LC_ALL": "C", "TZ": "UTC", "PATH": "/usr/local/bin:/usr/bin:/bin"}, timeout=20)
    out.append({"fixture": fx, "args": args, "stdout": p.stdout.decode("latin-1"), "status": p.returncode, "stderr": p.stderr.decode("latin-1")[:200]})
json.dump(out, open(sys.argv[2], "w"))
