"""Find the cheapest valid solution file per instance among authoring rounds.

Usage: python3 best.py SLUG  -> prints instance cost path, and copies to authoring/best/<inst>.json
"""
import glob, json, os, shutil, sys, importlib.util
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CFG = {
    "tbrain-bottling-line-lot-sizing": ("check_plan", "sites", ["dorset", "kent", "fife", "tyne"], "load_plan"),
    "tbrain-airport-gate-assignment": ("check_plan", "days", ["day-1", "day-2", "day-3", "day-4"], "load_plan"),
    "tbrain-ward-nurse-rostering": ("check_roster", "wards", ["ash", "birch", "cedar", "dale"], "load_roster"),
    "tbrain-newspaper-ad-layout": ("check_layout", "editions", ["mon", "wed", "fri", "sat"], "load_layout"),
}
slug = sys.argv[1]
mod, folder, insts, loader = CFG[slug]
task = os.path.join(ROOT, "tasks", slug)
spec = importlib.util.spec_from_file_location(mod, os.path.join(task, "tests", mod + ".py"))
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
auth = os.path.join(ROOT, "reports", slug, "authoring")
os.makedirs(os.path.join(auth, "best"), exist_ok=True)
out = {}
for inst in insts:
    inp = json.load(open(os.path.join(task, "environment", "app", folder, inst + ".json")))
    cands = glob.glob(os.path.join(auth, "**", inst + "*.json"), recursive=True)
    cands += glob.glob(os.path.join(ROOT, "local-solve-probes", slug + "*", "**", inst + ".json"), recursive=True)
    best = None
    for c in cands:
        if os.path.basename(c).startswith("p-") or os.sep + "old-small" + os.sep in c:
            continue
        try:
            cost = m.evaluate(inp, getattr(m, loader)(c))
        except Exception:
            continue
        if best is None or cost < best[0]:
            best = (cost, c)
    if best:
        dst = os.path.join(auth, "best", inst + ".json")
        if os.path.abspath(best[1]) != os.path.abspath(dst):
            shutil.copy(best[1], dst)
        out[inst] = best[0]
        print(inst, best[0], os.path.relpath(best[1], auth))
json.dump(out, open(os.path.join(auth, "best", "costs.json"), "w"), indent=1)
