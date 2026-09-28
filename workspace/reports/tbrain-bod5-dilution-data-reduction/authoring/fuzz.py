"""Fuzz solution/model.py against a package tree (in-process). Usage: fuzz.py APP_DIR SEED PER_FAMILY OUT.json"""
import importlib, json, sys, collections
from pathlib import Path
import gen

def load_pkg(app):
    for k in [k for k in sys.modules if k == "bodcalc" or k.startswith("bodcalc.")]:
        del sys.modules[k]
    sys.path.insert(0, str(Path(app) / "src"))
    try:
        return importlib.import_module("bodcalc")
    finally:
        sys.path.pop(0)

def same(g, e):
    if type(g) is not type(e):
        return False
    if isinstance(e, dict):
        return list(g) == list(e) and all(same(g[k], e[k]) for k in e)
    if isinstance(e, list):
        return len(g) == len(e) and all(same(a, b) for a, b in zip(g, e))
    if isinstance(e, float):
        return abs(g - e) <= 1e-9 * max(1.0, abs(e))
    return g == e

def run(app, seed, per):
    pkg = load_pkg(app)
    stats = collections.defaultdict(lambda: [0, 0])
    first = {}
    for fam, b in gen.batches(seed, per):
        exp = gen.model.report(b)
        try:
            got = json.loads(json.dumps(pkg.reduce_batch(json.loads(json.dumps(b)))))
            ok = same(got, exp)
        except Exception as ex:
            ok, got = False, repr(ex)
        stats[fam][0] += ok
        stats[fam][1] += 1
        if not ok and fam not in first:
            first[fam] = {"batch": b["batch"]}
    return {k: {"agree": v[0], "total": v[1]} for k, v in stats.items()}, first

if __name__ == "__main__":
    app, seed, per, out = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
    stats, first = run(app, seed, per)
    rec = {"app": app, "seed": seed, "per_family": per, "families": stats, "first_disagreement": first,
           "all_agree": all(v["agree"] == v["total"] for v in stats.values())}
    Path(out).write_text(json.dumps(rec, indent=1))
    print(json.dumps(rec["families"]), rec["all_agree"])
