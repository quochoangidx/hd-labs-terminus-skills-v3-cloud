"""check_departures.py OUT: the shipped package differs from the model on every departure family,
and on each trap's silent case its line equals the model's line (in process)."""

import json
import random
import sys
from pathlib import Path

import gen
import pkgload

TASK = gen.TASK


def main(out):
    shipped = pkgload.load(TASK / "environment" / "app", "shipped_commission")
    from shipped_commission import bonus as sbonus, clawback as sclaw  # noqa: E402
    rng = random.Random(4242)
    fam_result = {}
    for fam, fn in gen.FAMILIES.items():
        differ = 0
        n = 60
        for _ in range(n):
            j = fn(rng)
            if json.dumps(shipped.build_statements(j)) != json.dumps(gen.model.statements(j)):
                differ += 1
        fam_result[fam] = {"jobs": n, "shipped_differs_from_model": differ}
    # Silent case TA: every credit note below 50,000 cents raised in the quarter, any age 0-365.
    ta = {"lines": 0, "mismatch": 0, "nonzero": 0}
    for _ in range(20000):
        q = gen.quarter(rng)
        c = gen.credit(rng, q, rng.randint(100, 49999), rng.randint(0, 365))
        got = sclaw.clawback_lines([c], q)
        exp = [gen.model.clawback_line(*c)]
        ta["lines"] += 1
        ta["mismatch"] += got != exp
        ta["nonzero"] += exp[0] != 0
    # Silent case TB: every first order below 250,000 cents counting toward the quarter.
    tb = {"lines": 0, "mismatch": 0, "nonzero": 0}
    for _ in range(20000):
        v, split = rng.randint(100, 249999), rng.randint(1, 100)
        got = sbonus.bonus_lines([(v, split, True)])
        exp = [gen.model.bonus_line(v, split)]
        tb["lines"] += 1
        tb["mismatch"] += got != exp
        tb["nonzero"] += exp[0] != 0
    departures_ok = all(fam_result[f]["shipped_differs_from_model"] > 0 for f in fam_result if f.startswith("D"))
    res = {
        "check": "shipped package vs solution/model.py",
        "families": fam_result,
        "silent_TA_courtesy_credit_lines": ta,
        "silent_TB_trial_order_lines": tb,
        "status": "pass" if departures_ok and ta["mismatch"] == 0 and tb["mismatch"] == 0 else "fail",
    }
    Path(out).write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main(sys.argv[1])
