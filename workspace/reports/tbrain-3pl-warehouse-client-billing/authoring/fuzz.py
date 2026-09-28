"""fuzz.py SEED N OUT_JSON: model (solution/model.py) vs the Oracle-patched package, in process (3PL billing).

The Oracle tree is authoring/oracle/app (shipped package + solution/fix.patch). Jobs are drawn over the
whole of billing schedule 1.4 with trap inputs allowed, plus capacity jobs. Comparison is type-strict.
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
    for name in [m for m in sys.modules if m == "stockbill" or m.startswith("stockbill.")]:
        del sys.modules[name]
    sys.path.insert(0, str(root))
    try:
        return importlib.import_module("stockbill")
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
    stats = {"jobs": 0, "lots": 0, "mismatches": 0, "t1_jobs": 0, "t2_jobs": 0, "capacity_jobs": 0,
             "minimum_fee_lots": 0, "no_billed_week_lots": 0, "half_cent_surcharges": 0, "billed_weeks": 0, "return_entries": 0, "zero_entries": 0}
    first_bad = None
    for i in range(n):
        if i % 50 == 49:
            job = jobs.broad_job(rng, n_lots=300, n_clients=20, trap_free=False)
            stats["capacity_jobs"] += 1
        else:
            job = jobs.broad_job(rng, trap_free=False)
        jobs.within_limits(job)
        exp = jobs.model.report(json.loads(json.dumps(job)))
        got = json.loads(json.dumps(oracle.build_statement(json.loads(json.dumps(job)))))
        stats["jobs"] += 1
        stats["lots"] += len(job["lots"])
        stats["t1_jobs"] += jobs.model.carries_return_on_a_week_start(job)
        stats["return_entries"] += sum(x["pallets"] < 0 for lot in job["lots"] for x in lot["dispatches"])
        stats["zero_entries"] += sum(x["pallets"] == 0 for lot in job["lots"] for x in lot["dispatches"])
        stats["t2_jobs"] += jobs.model.carries_empty_arrival_in_period(job)
        for row in exp["lots"]:
            c = job["clients"][row["client"]]
            stats["minimum_fee_lots"] += row["storage_weeks"] > 0 and row["storage"] == c["minimum"]
            stats["no_billed_week_lots"] += row["storage_weeks"] == 0
            stats["billed_weeks"] += row["storage_weeks"]
            stats["half_cent_surcharges"] += (row["storage"] * c["surcharge_percent"]) % 100 == 50
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
