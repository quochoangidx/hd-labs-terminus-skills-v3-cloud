"""fuzz.py SEED N OUT: model vs the Oracle-patched package, in process, N jobs per family plus 5N fuzz jobs.

Whole reports compared type-strictly. Authoring only.
"""
import hashlib
import json
import random
import sys
from pathlib import Path

import gen
import trees

HERE = Path(__file__).resolve().parent


def same(a, b):
    if type(a) is not type(b):
        return False
    if isinstance(a, dict):
        return list(a) == list(b) and all(same(a[k], b[k]) for k in a)
    if isinstance(a, list):
        return len(a) == len(b) and all(same(x, y) for x, y in zip(a, b))
    return a == b


def main(seed, n, out, app=HERE / "oracle" / "app"):
    pkg = trees.load(app)
    rng = random.Random(seed)
    fams = dict(gen.FAMILIES, fuzz=gen.fam_fuzz)
    rep = {"seed": seed, "tree": str(app), "families": {}, "mismatches": []}
    hours = 0
    for fam, fn in fams.items():
        k = n if fam != "fuzz" else 5 * n
        ok = 0
        for _ in range(k):
            job = fn(rng)
            assert not gen.model.within_limits(job), gen.model.within_limits(job)[:3]
            exp = gen.model.report(job)
            got = json.loads(json.dumps(pkg.build_report(json.loads(json.dumps(job)))))
            hours += len(exp["hours"])
            if same(got, exp):
                ok += 1
            elif len(rep["mismatches"]) < 3:
                diff = [i for i, (g, e) in enumerate(zip(got["hours"], exp["hours"])) if g != e][:3]
                rep["mismatches"].append({"family": fam, "first_hour_diffs": [(got["hours"][i], exp["hours"][i]) for i in diff],
                                          "totals": [(got[x], exp[x]) for x in ("operating_hours", "valid_hours", "nox_tons")]})
        rep["families"][fam] = {"jobs": k, "agree": ok}
    rep["operating_hours_compared"] = hours
    rep["verdict"] = "agree" if not rep["mismatches"] else "DISAGREE"
    task = gen.TASK
    rep["model_sha256"] = hashlib.sha256((task / "solution" / "model.py").read_bytes()).hexdigest()
    fp = task / "solution" / "fix.patch"
    rep["fix_patch_sha256"] = hashlib.sha256(fp.read_bytes()).hexdigest() if fp.exists() else None
    Path(out).write_text(json.dumps(rep, indent=1) + "\n")
    print(rep["verdict"], {f: v["agree"] for f, v in rep["families"].items()}, "hours", hours)


if __name__ == "__main__":
    main(int(sys.argv[1]), int(sys.argv[2]), sys.argv[3])
