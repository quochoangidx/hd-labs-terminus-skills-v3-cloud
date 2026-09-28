"""fuzz.py SEED N OUT: model (solution/model.py) versus the Oracle-patched package, in process,
over N jobs per family (every scorer family plus the full-range `fuzz` family). Writes a receipt."""

import hashlib
import json
import random
import sys
from pathlib import Path

import gen
import pkgload

HERE = Path(__file__).resolve().parent


def main(seed, n, out):
    oracle = pkgload.load(HERE / "oracle" / "app", "oracle_commission")
    rng = random.Random(seed)
    fams = dict(gen.FAMILIES)
    fams["fuzz"] = gen.fam_fuzz
    fams["corners"] = gen.fam_corners
    per, mismatches, reps, lines = {}, [], 0, {"orders": 0, "credits": 0}
    for fam, fn in fams.items():
        ok = 0
        for i in range(n):
            j = fn(rng)
            probs = gen.model.limit_problems(j)
            assert not probs, (fam, probs)
            exp = gen.model.statements(j)
            got = oracle.build_statements(json.loads(json.dumps(j)))
            reps += len(j["reps"])
            for r in j["reps"]:
                lines["orders"] += len(r["orders"])
                lines["credits"] += len(r["credits"])
            if json.dumps(exp) == json.dumps(got):
                ok += 1
            elif len(mismatches) < 5:
                mismatches.append({"family": fam, "i": i, "job": j, "model": exp, "oracle": got})
        per[fam] = {"jobs": n, "agree": ok}
    res = {
        "check": "model-versus-Oracle fuzz (in process, exact JSON equality, type-strict via json.dumps)",
        "seed": seed,
        "per_family": per,
        "reps": reps,
        "lines": lines,
        "mismatches": mismatches,
        "status": "pass" if not mismatches else "fail",
        "model_sha256": hashlib.sha256((gen.TASK / "solution" / "model.py").read_bytes()).hexdigest(),
        "fix_patch_sha256": hashlib.sha256((gen.TASK / "solution" / "fix.patch").read_bytes()).hexdigest(),
    }
    Path(out).write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps({k: res[k] for k in ("seed", "per_family", "reps", "lines", "status")}, indent=1))


if __name__ == "__main__":
    main(int(sys.argv[1]), int(sys.argv[2]), sys.argv[3])
