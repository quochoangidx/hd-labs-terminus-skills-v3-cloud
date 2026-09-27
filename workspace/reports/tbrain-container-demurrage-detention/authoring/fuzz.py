"""fuzz.py SEED N OUT_JSON: model (solution/model.py) vs the Oracle-patched package, in process.

The Oracle tree is authoring/oracle/app (shipped package + solution/fix.patch). Jobs are drawn over the
whole of tariff rules 1.4 with trap inputs allowed, plus capacity jobs. Comparison is type-strict.
"""

import importlib
import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import jobs  # noqa: E402


def load_pkg(root):
    for name in [m for m in sys.modules if m == "ddbill" or m.startswith("ddbill.")]:
        del sys.modules[name]
    sys.path.insert(0, str(root))
    try:
        return importlib.import_module("ddbill")
    finally:
        sys.path.pop(0)


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
    oracle = load_pkg(HERE / "oracle" / "app" / "src")
    stats = {"jobs": 0, "containers": 0, "mismatches": 0, "t1_jobs": 0, "t2_jobs": 0, "capacity_jobs": 0,
             "running_stages": 0, "ended_stages": 0, "half_cent_discounts": 0}
    first_bad = None
    for i in range(n):
        if i % 50 == 49:
            job = jobs.broad_job(rng, n_containers=300, n_contracts=20, trap_free=False)
            stats["capacity_jobs"] += 1
        else:
            job = jobs.broad_job(rng, trap_free=False)
        jobs.within_limits(job)
        exp = jobs.model.report(json.loads(json.dumps(job)))
        got = json.loads(json.dumps(oracle.build_statement(json.loads(json.dumps(job)))))
        stats["jobs"] += 1
        stats["containers"] += len(job["containers"])
        stats["t1_jobs"] += jobs.model.carries_running_discount_edge(job)
        stats["t2_jobs"] += jobs.model.carries_pre_sheet_start(job)
        for row in exp["containers"]:
            for st in (row["terminal"], row["merchant"]):
                if st:
                    stats["running_stages" if st["status"] == "running" else "ended_stages"] += 1
            pct = job["contracts"][[c for c in job["containers"] if c["id"] == row["id"]][0]["contract"]]["discount_percent"]
            stats["half_cent_discounts"] += (row["amount"] * pct) % 100 == 50
        if not same(got, exp):
            stats["mismatches"] += 1
            if first_bad is None:
                first_bad = {"index": i, "job": job}
    result = {"seed": seed, "n": n, "stats": stats, "status": "pass" if stats["mismatches"] == 0 else "fail",
              "first_mismatch": first_bad}
    Path(out).write_text(json.dumps(result, indent=1) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k != "first_mismatch"}))


if __name__ == "__main__":
    main(int(sys.argv[1]), int(sys.argv[2]), sys.argv[3])
