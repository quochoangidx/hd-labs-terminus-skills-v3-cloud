"""Production planner used by the site office.

Lot-for-lot: each day, every product with stock short of that day's demand
(including backlog) is filled for exactly the shortfall, on the first of its
lines (in the order its `lines` lists them) with minutes to spare that day,
as many batches as fit. Whatever does not fit is carried as backlog.

Usage: python3 plan_site.py SITE.json PLAN.json
"""

import json
import sys


def plan(site):
    days = site["days"]
    free = {line["id"]: list(line["capacity_minutes"]) for line in site["lines"]}
    stock = {p["id"]: p["initial_stock"] for p in site["products"]}
    runs = []
    for d in range(days):
        for p in site["products"]:
            need = p["demand"][d] - stock[p["id"]]
            for lid, spec in p["lines"].items():
                if need <= 0:
                    break
                room = free[lid][d] - spec["setup_minutes"]
                n = min(need, room // spec["minutes_per_batch"]) if room > 0 else 0
                if n >= 1:
                    runs.append({"day": d, "line": lid, "product": p["id"], "batches": n})
                    free[lid][d] -= spec["setup_minutes"] + n * spec["minutes_per_batch"]
                    stock[p["id"]] += n
                    need -= n
            stock[p["id"]] -= p["demand"][d]
    return {"runs": runs}


if __name__ == "__main__":
    with open(sys.argv[1]) as fh:
        site = json.load(fh)
    with open(sys.argv[2], "w") as fh:
        json.dump(plan(site), fh, indent=1)
