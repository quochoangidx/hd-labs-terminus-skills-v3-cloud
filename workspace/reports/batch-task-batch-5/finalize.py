"""Set a task's reference files and targets from the cheapest files seen.

Usage: python3 finalize.py SLUG
Runs best.py's collection, copies best/<inst>.json to solution/<out>/<inst>.json
(compact, sorted as the tool wrote it) and writes targets.json into both
environment/app/<in>/ and tests/ with the same key order as before.
"""
import json, os, shutil, subprocess, sys
slug = sys.argv[1]
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
subprocess.run([sys.executable, os.path.join(HERE, "best.py"), slug], check=True)
CFG = {"tbrain-bottling-line-lot-sizing": ("sites", "plans"), "tbrain-airport-gate-assignment": ("days", "plans"), "tbrain-ward-nurse-rostering": ("wards", "rosters"),
       "tbrain-newspaper-ad-layout": ("editions", "layouts")}
inf, outf = CFG[slug]
task = os.path.join(ROOT, "tasks", slug); auth = os.path.join(ROOT, "reports", slug, "authoring", "best")
costs = json.load(open(os.path.join(auth, "costs.json")))
old = json.load(open(os.path.join(task, "tests", "targets.json")))
new = {k: costs[k] for k in old}
os.makedirs(os.path.join(task, "solution", outf), exist_ok=True)
for k in new:
    shutil.copy(os.path.join(auth, k + ".json"), os.path.join(task, "solution", outf, k + ".json"))
text = json.dumps(new, indent=1) + "\n"
for p in (os.path.join(task, "tests", "targets.json"), os.path.join(task, "environment", "app", inf, "targets.json")):
    open(p, "w").write(text)
print(slug, new)
