"""fuzz.py OUT: model vs Oracle-patched package on generated jobs across the full ranges, plus the
departure/trap checks on the variant trees (in-process, authoring only)."""

import importlib
import json
import random
import subprocess
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

import gen
import variants

RUNNER = r'''
import json, sys
sys.path.insert(0, sys.argv[1])
from treadcheck import build_summary
out = []
for job in json.load(open(sys.argv[2])):
    try:
        out.append(build_summary(job))
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


def extreme(r):  # whole ranges, traps allowed (model vs Oracle only)
    report = date(2034, 12, 31) if r.random() < 0.5 else date(2016, 1, 1) + timedelta(days=r.randint(1600, 6900))
    gs = [{"gauge": gen.uid(r, "X")[:12], "offset": r.choice([-9, -1, 0, 1, 9, r.randint(-9, 9)])} for _ in range(r.choice([1, 20]))]
    tires = []
    for _ in range(r.choice([1, 50, 300])):
        t = gen.tire(r, gs, report, reads_n=r.choice([2, 30]), new=r.choice([60, 320, r.randint(60, 320)]),
                     retreads=r.randint(0, 4), end_depth=r.choice([None, 0, 19, 50, 51, 400]))
        if not gen.model.within_limits({"report_date": report.isoformat(), "gauges": gs, "tires": [t]}):
            tires.append(t)
    if not tires:
        tires.append(gen.tire(r, gs, report))
    return {"report_date": report.isoformat(), "gauges": gs, "tires": tires}


def main(out):
    rng = random.Random(4242)
    fams = {f: [fn(rng) for _ in range(150)] for f, fn in gen.FAMILIES.items()}
    fams["extreme"] = [e for e in (extreme(rng) for _ in range(40)) if not gen.model.within_limits(e)]
    for js in fams.values():
        for j in js:
            assert not gen.model.within_limits(j), gen.model.within_limits(j)
    trees = variants.build()
    expected = {f: [gen.model.summary(j) for j in js] for f, js in fams.items()}
    failing, res = {}, {}
    for name, app in trees.items():
        res[name] = {f: sum(not same(g, e) for g, e in zip(run_tree(app, js), expected[f])) for f, js in fams.items()}
        failing[name] = sorted(f for f, c in res[name].items() if c)
    def only(name, fam):
        return [f for f in failing[name] if f != "extreme"] == [fam]
    # silent check: on the trap families the shipped package's kept step equals the model's
    sys.path.insert(0, str(trees["shipped"] / "src"))
    sw = importlib.import_module("treadcheck.wear")
    ss = importlib.import_module("treadcheck.status")
    sys.path.pop(0)
    silent = {"T1_tires": 0, "T1_kept": 0, "T2_tires": 0, "T2_kept": 0}
    for j in fams["T1"] + fams["T2"]:
        for e in gen.model.summary(j)["tires"]:
            lim = gen.model.REMOVAL[e["position"]]
            silent["T1_tires"] += 1
            silent["T1_kept"] += sw.km_left(e["latest"], lim, e["rate"]) == e["km_left"]
            silent["T2_tires"] += 1
            silent["T2_kept"] += ss.regroove(e["position"], e["latest"]) == e["regroove"]
    checks = {
        "oracle_matches_model_everywhere": failing["oracle"] == [],
        "shipped_differs_on_every_departure_family": all(f"D{k}" in failing["shipped"] for k in range(1, 9)),
        "shipped_matches_model_on_trap_silent_cases": silent["T1_kept"] == silent["T1_tires"] > 0
        and silent["T2_kept"] == silent["T2_tires"] > 0,
        "each_revert_fails_its_family": all(f"D{k}" in failing[f"revert-D{k}"] for k in range(1, 9)),
        "T1_natural_fix_fails_only_T1": only("T1-halves-up-in-km-left", "T1"),
        "T2_natural_fix_fails_only_T2": only("T2-floor-follows-removal", "T2"),
    }
    n = sum(len(e["tires"]) for es in expected.values() for e in es)
    doc = {"seed": 4242, "jobs_per_family": 150, "extreme_jobs": len(fams["extreme"]), "entries_compared_per_tree": n,
           "mismatching_jobs": res, "failing_families": failing, "silent_check": silent, "checks": checks,
           "status": "pass" if all(checks.values()) else "FAIL"}
    Path(out).write_text(json.dumps(doc, indent=1) + "\n")
    for k, f in failing.items():
        print(f"{k:34s} {f}")
    print(json.dumps(checks), doc["status"], silent, n)


if __name__ == "__main__":
    main(sys.argv[1])
