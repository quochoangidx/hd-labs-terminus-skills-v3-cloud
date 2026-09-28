"""Fuzz solution/model.py against the Oracle-patched package in-process over every family (authoring only)."""
import json
import random
import sys
from pathlib import Path

import gen
import pkgload

seed = int(sys.argv[1]) if len(sys.argv) > 1 else 20260928
n = int(sys.argv[2]) if len(sys.argv) > 2 else 300
oracle = pkgload.load(Path(__file__).parent / "oracle" / "b" / "src")
rng = random.Random(seed)
res = {"seed": seed, "per_family": n, "families": {}, "mismatches": []}
accounts = 0
for fam, fn in gen.FAMILIES.items():
    ok = 0
    for i in range(n):
        job = fn(rng)
        assert not gen.model.within_limits(job), (fam, gen.model.within_limits(job))
        accounts += len(job["accounts"])
        got = json.loads(json.dumps(oracle.build_statements(job)))
        exp = gen.model.statements(job)
        if got == exp and all(type(a[k]) is type(b[k]) for a, b in zip(got["settlements"], exp["settlements"]) for k in a):
            ok += 1
        elif len(res["mismatches"]) < 5:
            res["mismatches"].append({"family": fam, "job": job, "got": got, "exp": exp})
    res["families"][fam] = f"{ok}/{n}"
res["accounts"] = accounts
res["status"] = "pass" if not res["mismatches"] else "fail"
print(json.dumps({k: v for k, v in res.items() if k != "mismatches"}, indent=1))
out = Path(__file__).resolve().parents[1] / "receipts" / f"fuzz-model-vs-oracle-seed{seed}.json"
out.write_text(json.dumps(res, indent=1) + "\n")
