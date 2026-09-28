"""fuzz.py OUT: model vs Oracle-patched package on generated jobs across the full ranges, plus the
departure/trap checks on the variant trees (in-process, authoring only)."""

import json
import random
import subprocess
import sys
import tempfile
from pathlib import Path

import gen
import variants

RUNNER = r'''
import json, sys
sys.path.insert(0, sys.argv[1])
from waterbill import build_bills
jobs = json.load(open(sys.argv[2]))
out = []
for job in jobs:
    try:
        out.append(build_bills(job))
    except Exception as e:
        out.append({"error": repr(e)})
json.dump(out, open(sys.argv[3], "w"))
'''


def run_tree(app, jobs):
    with tempfile.TemporaryDirectory() as tmp:
        jp, op, rp = Path(tmp, "j.json"), Path(tmp, "o.json"), Path(tmp, "r.py")
        jp.write_text(json.dumps(jobs)); rp.write_text(RUNNER)
        subprocess.run([sys.executable, "-I", "-S", str(rp), str(app / "src"), str(jp), str(op)], check=True)
        return json.loads(op.read_text())


def same(a, b):
    if type(a) is not type(b):
        return False
    if isinstance(a, dict):
        return list(a) == list(b) and all(same(a[k], b[k]) for k in a)
    if isinstance(a, list):
        return len(a) == len(b) and all(same(x, y) for x, y in zip(a, b))
    return a == b


def main(out):
    rng = random.Random(4242)
    fams = {f: [fn(rng) for _ in range(150)] for f, fn in gen.FAMILIES.items()}
    def extreme(r):  # whole ranges, traps allowed (model vs Oracle only)
        first = gen.first_day(r).replace(year=2015 + r.randint(0, 5))
        sched = gen.schedule(r, first, n=12, span_days=r.choice([60, 400, 3000]))
        accts = [gen.account(r, first, units=r.randint(1, 8), n=r.choice([2, 40]),
                             gaps=lambda q: q.choice([1, 2, 19, 20, 30, 61, 62]),
                             use=lambda q: q.choice([0, 1, 49, 50, 150, q.randint(0, 2_000_000)]), est=0.4)
                 for _ in range(r.choice([1, 5, 200]))]
        return {"schedule": sched, "accounts": accts}
    fams["extreme"] = [extreme(rng) for _ in range(12)]
    for f, js in fams.items():
        for j in js:
            assert not gen.model.within_limits(j)
    trees = variants.build()
    expected = {f: [gen.model.bills(j) for j in js] for f, js in fams.items()}
    res = {}
    for name, app in trees.items():
        res[name] = {}
        for f, js in fams.items():
            got = run_tree(app, js)
            res[name][f] = sum(not same(g, e) for g, e in zip(got, expected[f]))
    n_bills = sum(len(e["bills"]) for es in expected.values() for e in es)
    failing = {n: sorted(f for f, c in r.items() if c) for n, r in res.items()}
    checks = {
        "oracle_matches_model_everywhere": failing["oracle"] == [],
        "shipped_differs_on_every_departure_family": all(f"D{k}" in failing["shipped"] for k in range(1, 8)),
        "shipped_matches_model_on_trap_silent_cases": True,  # see silent_check below
        "each_revert_fails_its_family": all(f"D{k}" in failing[f"revert-D{k}"] for k in range(1, 8)),
        "T1_natural_fix_fails_only_T1": [f for f in failing["T1-scale-every-span"] if f != "extreme"] == ["T1"],
        "T2_natural_fix_fails_only_T2": [f for f in failing["T2-cap-every-account"] if f != "extreme"] == ["T2"],
        "T2_exclusion_reading_fails_T2": "T2" in failing["T2-no-sewer-for-multi-unit"],
    }
    # silent check: on trap families, the shipped package's kept figure equals the model's
    silent = {"T1_widths_kept": 0, "T1_spans": 0, "T2_volume_kept": 0, "T2_spans": 0}
    import importlib
    sys.path.insert(0, str(trees["shipped"] / "src"))
    shipped_tiers = importlib.import_module("waterbill.tiers")
    sys.path.pop(0)
    for j in fams["T1"]:
        for a in j["accounts"]:
            for sp in gen.model.spans(a):
                if sp["days"] < 20:
                    for r, _ in gen.model.rows_under(j["schedule"], sp):
                        silent["T1_spans"] += 1
                        silent["T1_widths_kept"] += shipped_tiers.block_widths(r, sp["days"]) == gen.model.widths_for(r, sp["days"])
    shipped_t2 = run_tree(trees["shipped"], fams["T2"])
    for g, e in zip(shipped_t2, expected["T2"]):
        for gb, eb in zip(g["bills"], e["bills"]):
            silent["T2_spans"] += 1
            silent["T2_volume_kept"] += gb["sewer_volume"] == eb["sewer_volume"]
    checks["shipped_matches_model_on_trap_silent_cases"] = (silent["T2_volume_kept"] == silent["T2_spans"] > 0
        and silent["T1_widths_kept"] == silent["T1_spans"] > 0)
    doc = {"seed": 4242, "jobs_per_family": 150, "bills_compared_per_tree": n_bills, "mismatching_jobs": res,
           "failing_families": failing, "silent_check": silent, "checks": checks,
           "status": "pass" if all(checks.values()) else "FAIL"}
    Path(out).write_text(json.dumps(doc, indent=1) + "\n")
    for n, f in failing.items():
        print(f"{n:28s} {f}")
    print(json.dumps(checks), doc["status"])


if __name__ == "__main__":
    main(sys.argv[1])
