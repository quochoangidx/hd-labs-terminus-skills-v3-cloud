"""check_departures.py [SEED] [PER]: shipped, Oracle and natural over-repairs vs the model, per family (in-process, no Docker).

Writes ../receipts/departure-trap-checks.json. Expected shape:
  Oracle passes every family; shipped fails every departure family and is right at each trap's figure;
  each natural over-repair fails its own trap family only.
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import compare
import jobgen
import variants

HERE = Path(__file__).resolve().parent
SEED = int(sys.argv[1]) if len(sys.argv) > 1 else 20260927
PER = int(sys.argv[2]) if len(sys.argv) > 2 else 12


def run(src, plates):
    proc = subprocess.run([sys.executable, "-I", str(HERE / "runpkg.py"), str(src)],
                          input="".join(json.dumps(p) + "\n" for p in plates), capture_output=True, text=True, check=True)
    return [json.loads(line) for line in proc.stdout.splitlines()]


def main():
    cases = jobgen.cases(SEED, PER)
    plates = [p for _f, p in cases]
    expected = [jobgen.model.report(p) for p in plates]
    trees = {"shipped": HERE / "shipped" / "app", "oracle": HERE / "patched" / "app"}
    trees.update(variants.build())
    out = {"seed": SEED, "per_family": PER,
           "model_sha256": hashlib.sha256((jobgen.TASK / "solution" / "model.py").read_bytes()).hexdigest(),
           "trees": {}}
    for name, app in trees.items():
        got = run(app / "src", plates)
        fams = {}
        for (fam, _p), g, e in zip(cases, got, expected):
            d = fams.setdefault(fam, {"passed": 0, "total": 0, "sample_diff": None})
            d["total"] += 1
            if compare.same(g, e):
                d["passed"] += 1
            elif d["sample_diff"] is None:
                d["sample_diff"] = g.get("__error__") or compare.diff_paths(g, e)[:4]
        failed = sorted(f for f, d in fams.items() if d["passed"] != d["total"])
        out["trees"][name] = {"failed_families": failed, "families": fams}
        print(f"{name:26s} failed: {failed}")
    # trap-site checks: the shipped package is already right at each trap's figure
    t1 = [(p, e) for (f, p), e in zip(cases, expected) if f == "T1"]
    t2 = [(p, e) for (f, p), e in zip(cases, expected) if f == "T2"]
    s1 = run(trees["shipped"] / "src", [p for p, _ in t1])
    s2 = run(trees["shipped"] / "src", [p for p, _ in t2])
    out["trap_site_checks"] = {
        "T1_factor_shipped_equals_model": all(compare.same([x["factor"] for x in g["genes"]], [x["factor"] for x in e["genes"]]) for g, (_p, e) in zip(s1, t1)),
        "T1_whole_report_shipped_equals_model": all(compare.same(g, e) for g, (_p, e) in zip(s1, t1)),
        "T2_contaminated_shipped_equals_model": all(compare.same([x["contaminated"] for x in g["genes"]], [x["contaminated"] for x in e["genes"]]) for g, (_p, e) in zip(s2, t2)),
        "T2_whole_report_shipped_equals_model": all(compare.same(g, e) for g, (_p, e) in zip(s2, t2)),
    }
    print(json.dumps(out["trap_site_checks"]))
    dst = HERE.parent / "receipts" / "departure-trap-checks.json"
    dst.parent.mkdir(exist_ok=True)
    dst.write_text(json.dumps(out, indent=1, default=str) + "\n")


if __name__ == "__main__":
    main()
