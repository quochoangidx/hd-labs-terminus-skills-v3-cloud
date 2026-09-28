import json, subprocess, sys, os
exp = json.load(open(sys.argv[1])); app = os.path.abspath(sys.argv[2]); here = os.path.dirname(os.path.abspath(__file__))
r = subprocess.run(["docker", "run", "--rm", "--network", "none", "-v", f"{app}:/app:ro", "-v", f"{here}/run_cand.py:/rc.py:ro", "-v", f"{os.path.abspath(sys.argv[1])}:/c.json:ro", "pybc-task", "python3", "/rc.py", "/c.json"], capture_output=True, text=True)
got = json.loads(r.stdout)
bad = [(e, g) for e, g in zip(exp, got) if e["stdout"] != g["stdout"] or e["status"] != g["status"]]
print(f"{len(exp) - len(bad)}/{len(exp)} match")
for e, g in bad[:int(sys.argv[3]) if len(sys.argv) > 3 else 15]:
    print("  ", repr(e["input"][:70]), "| want", repr(e["stdout"][:70]), e["status"], "| got", repr((g["stdout"] or "")[:70]), g["status"])
