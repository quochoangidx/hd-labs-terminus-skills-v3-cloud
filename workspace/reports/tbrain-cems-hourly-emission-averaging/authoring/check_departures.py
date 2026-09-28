"""check_departures.py OUT: in-process evidence (authoring only).

1. Per family, model vs shipped / Oracle / every variant (whole report, type-strict): which families fail.
2. Trap silent cases at step level: the shipped functions, fed the procedure's own inputs, give the
   model's value for every T1 hour (neither valid nor lost) and every T2 hour (valid, oxygen >= 190).
"""
import json
import random
import sys
import tempfile
from fractions import Fraction
from pathlib import Path

import fuzz
import gen
import trees
import variants

SEED, PER = 20260927, 4
SHIPPED = gen.TASK / "environment" / "app"


def fams_failed(app, cases):
    pkg = trees.load(app)
    failed = {}
    for fam, job, exp in cases:
        got = json.loads(json.dumps(pkg.build_report(json.loads(json.dumps(job)))))
        if not fuzz.same(got, exp):
            failed[fam] = failed.get(fam, 0) + 1
    return failed


def step_checks(cases):
    shipped = trees.load(SHIPPED)
    corr = sys.modules["cemsqr.correction"]
    sub = sys.modules["cemsqr.substitute"]
    t1 = t1_ok = t2 = t2_ok = 0
    for fam, job, exp in cases:
        ref = job["unit"]["ref_o2"]
        byhour = {}
        for r in job["readings"]:
            byhour.setdefault(r[0][:13], []).append(r)
        rows = {h["hour"]: h for h in exp["hours"]}
        seq = []
        for key, recs in byhour.items():
            op = [r for r in recs if r[1] >= 1]
            if not op:
                continue
            good = [r for r in op if r[5] == "OK"]
            valid = rows[key]["kind"] == "valid"
            # a lost hour's figures are settled by 4.2/4.3: hand them to the shipped step as given
            h = {"operating": True, "valid": valid or not good, "key": key}
            if not valid and not good:
                h["conc"], h["rate"] = rows[key]["nox"], rows[key]["lb"]
            if valid:
                h["conc"], h["rate"] = rows[key]["nox"], rows[key]["lb"]
                o2 = Fraction(sum(r[3] for r in good), len(good))
                if o2 >= 190:
                    nox = Fraction(sum(r[2] for r in good), len(good))
                    t2 += 1
                    t2_ok += corr.corrected(nox, o2, ref) == rows[key]["nox"]
            elif good:
                h["trap"] = True
            seq.append(h)
        sub.fill(seq)
        for h in seq:
            if h.get("trap"):
                t1 += 1
                t1_ok += (h["conc"], h["rate"]) == (rows[h["key"]]["nox"], rows[h["key"]]["lb"])
    return {"T1_hours": t1, "T1_shipped_step_equals_model": t1_ok, "T2_hours": t2, "T2_shipped_step_equals_model": t2_ok}


def main(out):
    rng = random.Random(SEED)
    cases = []
    for fam, fn in gen.FAMILIES.items():
        for _ in range(PER):
            job = fn(rng)
            assert not gen.model.within_limits(job)
            want = {fam} if fam in gen.TRAP_FAMILIES else set()
            assert gen.trap_inputs(job) == want, (fam, gen.trap_inputs(job))
            cases.append((fam, job, gen.model.report(job)))
    res = {"seed": SEED, "per_family": PER, "trees": {}}
    res["trees"]["shipped"] = fams_failed(SHIPPED, cases)
    res["trees"]["oracle"] = fams_failed(variants.ORACLE, cases)
    with tempfile.TemporaryDirectory() as tmp:
        for name in variants.VARIANTS:
            res["trees"][name] = fams_failed(variants.build(name, Path(tmp) / name), cases)
    res["step_checks"] = step_checks([c for c in cases if c[0] in ("T1", "T2")])
    problems = []
    if res["trees"]["oracle"]:
        problems.append("oracle fails")
    for fam in gen.FAMILIES:
        if fam.startswith("D") and fam not in res["trees"]["shipped"]:
            problems.append("shipped passes " + fam)
    for name, failed in res["trees"].items():
        if name[:2] in ("D1", "D2", "D3", "D4", "D5", "D6", "D7", "D8", "D9") and name.split("-")[0] not in failed:
            problems.append(name + " passes its own family")
        if name.startswith("T") and set(failed) != {name[:2]}:
            problems.append(name + " fails " + str(sorted(failed)) + " (want only " + name[:2] + ")")
    sc = res["step_checks"]
    if sc["T1_hours"] == 0 or sc["T1_hours"] != sc["T1_shipped_step_equals_model"]:
        problems.append("T1 step check")
    if sc["T2_hours"] == 0 or sc["T2_hours"] != sc["T2_shipped_step_equals_model"]:
        problems.append("T2 step check")
    res["problems"] = problems
    res["verdict"] = "pass" if not problems else "FAIL"
    Path(out).write_text(json.dumps(res, indent=1) + "\n")
    for k, v in res["trees"].items():
        print(f"{k:42s} fails {sorted(v)}")
    print(sc, res["verdict"], problems)


if __name__ == "__main__":
    main(sys.argv[1])
