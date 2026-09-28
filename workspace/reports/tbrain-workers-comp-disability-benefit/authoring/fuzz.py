"""fuzz.py SEED N OUT: model vs the Oracle-patched package, in process, on N generated jobs per family.

Families: every scorer family plus `fuzz` (everything section 1 allows, trap inputs included, at every
scale). Compares whole statements type-strictly; writes a receipt. Authoring only.
"""

import hashlib
import json
import random
import sys
from pathlib import Path

import gen

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "oracle" / "app" / "src"))
import tdbenefit  # noqa: E402  (the Oracle-patched tree)


def same(a, b):
    if type(a) is not type(b):
        return False
    if isinstance(a, dict):
        return list(a) == list(b) and all(same(a[k], b[k]) for k in a)
    if isinstance(a, list):
        return len(a) == len(b) and all(same(x, y) for x, y in zip(a, b))
    return a == b


def main(seed, n, out):
    rng = random.Random(seed)
    fams = dict(gen.FAMILIES, fuzz=gen.fam_fuzz)
    report = {"seed": seed, "per_family": n, "families": {}, "mismatches": []}
    claims = 0
    for fam, fn in fams.items():
        ok = 0
        for k in range(n if fam != "fuzz" else 10 * n):
            job = fn(rng)
            assert not gen.model.within_limits(job), gen.model.within_limits(job)
            exp = gen.model.statements(job)
            got = tdbenefit.build_statements(json.loads(json.dumps(job)))
            claims += len(job["claims"])
            if same(got, exp):
                ok += 1
            elif len(report["mismatches"]) < 5:
                report["mismatches"].append({"family": fam, "job": job, "expected": exp, "got": got})
        report["families"][fam] = {"jobs": n if fam != "fuzz" else 10 * n, "agree": ok}
    report["claims"] = claims
    report["verdict"] = "agree" if not report["mismatches"] else "DISAGREE"
    report["model_sha256"] = hashlib.sha256((gen.TASK / "solution" / "model.py").read_bytes()).hexdigest()
    report["fix_patch_sha256"] = hashlib.sha256((gen.TASK / "solution" / "fix.patch").read_bytes()).hexdigest()
    Path(out).write_text(json.dumps(report, indent=1) + "\n")
    print(report["verdict"], {f: v["agree"] for f, v in report["families"].items()}, "claims", claims)


if __name__ == "__main__":
    main(int(sys.argv[1]), int(sys.argv[2]), sys.argv[3])
