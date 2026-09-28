"""check_departures.py OUT: the shipped (unpatched) package against the model, in process.

1. Every departure family: the shipped package's statements differ from the model's on every job.
2. Each trap's silent case: the shipped step the model mirrors is the shipped package's own step
   (T1: the week a line below a week's pay counts toward; T2: the benefit of a week of the partial
   earnings below 1,000 cents, given the manual's AWW and rate).
Authoring only.
"""

import importlib
import json
import random
import sys
from datetime import date, timedelta
from pathlib import Path

import gen

sys.path.insert(0, str(gen.TASK / "environment" / "app" / "src"))
tdbenefit = importlib.import_module("tdbenefit")
payroll = importlib.import_module("tdbenefit.payroll")
partial = importlib.import_module("tdbenefit.partial")


def main(out):
    rng = random.Random(20260927)
    res = {"departure_families": {}, "traps": {}}
    for fam in [f for f in gen.FAMILIES if f.startswith("D")]:
        jobs = [gen.FAMILIES[fam](rng) for _ in range(30)]
        differ = sum(tdbenefit.build_statements(j) != gen.model.statements(j) for j in jobs)
        res["departure_families"][fam] = {"jobs": 30, "shipped_differs": differ}
    # T1: the week a line below a week's pay counts toward
    n = agree = 0
    for _ in range(200):
        job = gen.fam_t1(rng)
        for c in job["claims"]:
            for paid, cents in c["wages"]:
                if cents < gen.WEEKS_PAY:
                    n += 1
                    (week, _c), = payroll.credit_lines([[paid, cents]])
                    agree += week == gen.model.counted_week(paid, cents)
    res["traps"]["T1"] = {"lines_below_a_weeks_pay": n, "shipped_week_equals_model": agree}
    # T2: the benefit of a week below 1,000 cents, with the manual's AWW and rate fed in
    n = agree = 0
    for _ in range(200):
        job = gen.fam_t2(rng)
        for c in job["claims"]:
            s = gen.model.statement(c, job["rates"])
            for week, earned in c["earnings"]:
                if earned < gen.PARTIAL_WEEK:
                    n += 1
                    got = partial.partial_disability([[week, earned]], s["aww"], s["rate"])["tpd"]
                    loss = s["aww"] - earned if earned < s["aww"] else 0
                    agree += got == min(gen.model.cents(gen.Fraction(3, 5) * loss), s["rate"])
    res["traps"]["T2"] = {"weeks_below_1000": n, "shipped_benefit_equals_model": agree}
    ok = all(v["shipped_differs"] == v["jobs"] for v in res["departure_families"].values()) and \
        res["traps"]["T1"]["lines_below_a_weeks_pay"] == res["traps"]["T1"]["shipped_week_equals_model"] and \
        res["traps"]["T2"]["weeks_below_1000"] == res["traps"]["T2"]["shipped_benefit_equals_model"]
    res["verdict"] = "pass" if ok else "FAIL"
    Path(out).write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps(res))


if __name__ == "__main__":
    main(sys.argv[1])
