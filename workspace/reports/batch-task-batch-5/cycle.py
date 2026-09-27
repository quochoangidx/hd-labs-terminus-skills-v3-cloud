"""Iterated annealing: repeated short anneals, each restarted from the best
solution so far with a random starting-temperature scale. A second search
family for target setting (the tools' own single long anneal is the first).

Usage: python3 cycle.py SLUG INSTANCE TOTAL_SECONDS CYCLE_SECONDS SEED OUTDIR
Runs from reports/SLUG/authoring (imports its tool), starts from best/INSTANCE.json.
"""
import json, os, random, sys, time
slug, inst, total, cyc, seed, outdir = sys.argv[1], sys.argv[2], float(sys.argv[3]), float(sys.argv[4]), int(sys.argv[5]), sys.argv[6]
here = os.path.dirname(os.path.abspath(__file__))
auth = os.path.join(here, "..", slug, "authoring")
sys.path.insert(0, auth)
task_tests = os.path.join(here, "..", "..", "tasks", slug, "environment", "app")
rng = random.Random(seed)
if "airport" in slug:
    import search as tool
    data = json.load(open(os.path.join(task_tests, "days", inst + ".json")))
    prob = tool.S(data)
    def run(start, secs, s):
        best, at, _ = tool.search(prob, secs, s, start)
        return best, tool.to_plan(prob, at)
elif "nurse" in slug:
    import sa_roster as tool
    data = json.load(open(os.path.join(task_tests, "wards", inst + ".json")))
    prob = tool.P(data)
    def run(start, secs, s):
        best, rows, _ = tool.search(prob, secs, s, start)
        if best is None:
            return None, None
        return best, {"roster": {x["id"]: "".join(r) for x, r in zip(prob.nurses, rows)}}
else:
    import lns_layout as tool
    data = json.load(open(os.path.join(task_tests, "editions", inst + ".json")))
    prob = tool.E(data)
    def run(start, secs, s):
        best, pages, _ = tool.search(prob, secs, s, start)
        return best, tool.to_layout(prob, pages)
cur = json.load(open(os.path.join(auth, "best", inst + ".json")))
from importlib import import_module
chk = import_module({"search": "check_plan", "sa_roster": "check_roster", "lns_layout": "check_layout"}[tool.__name__])
best = chk.evaluate(data, cur)
os.makedirs(outdir, exist_ok=True)
t0 = time.time(); k = 0
log = open(os.path.join(outdir, f"{inst}.c{seed}.log"), "a")
print(f"start {best}", file=log, flush=True)
while time.time() - t0 < total:
    tool.TSCALE = rng.choice([0.15, 0.3, 0.5, 0.8, 1.2])
    secs = min(cyc, total - (time.time() - t0))
    if secs < 10:
        break
    c, sol = run(cur, secs, rng.randrange(10**9))
    k += 1
    if c is not None and c <= best:
        assert chk.evaluate(data, sol) == c
        if c < best:
            json.dump(sol, open(os.path.join(outdir, f"{inst}.c{seed}.json"), "w"))
        best, cur = c, sol
    print(f"cycle {k} tscale {tool.TSCALE} got {c} best {best}", file=log, flush=True)
print(inst, best, file=log, flush=True)
