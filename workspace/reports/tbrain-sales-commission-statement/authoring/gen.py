"""Job generators for tbrain-sales-commission-statement (authoring only, never shipped).

Families: `broad` (trap-free, every departure live), one per departure D1-D7, one per trap TA
(courtesy credits) and TB (trial orders), and `fuzz` (everything mixed, full ranges; used only for
the model-versus-Oracle fuzz, never by the skeleton scorer). Each trap's input appears only in
its own family; `trap_inputs` checks it.
"""

import datetime
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TASK = HERE.parents[2] / "tasks" / "tbrain-sales-commission-statement"
sys.path.insert(0, str(TASK / "solution"))
import model  # noqa: E402

D = datetime.timedelta(days=1)
LOGO = model.NEW_LOGO_CENTS
REV = model.REVERSAL_CENTS


def quarter(rng):
    return f"{rng.randint(2020, 2039)}-Q{rng.randint(1, 4)}"


def day_in(rng, q, where="in"):
    first, last = model.quarter_span(q)
    if where == "in":
        span = (last - first).days
        pick = rng.random()
        if pick < 0.1:
            d = first
        elif pick < 0.2:
            d = last
        else:
            d = first + rng.randint(0, span) * D
    else:
        if rng.random() < 0.5:
            d = first - rng.randint(1, 45) * D
        else:
            d = last + rng.randint(1, 45) * D
    return d.isoformat()


def rep_code(rng, k):
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ0123456789-"
    n = rng.randint(1, 16)
    return (f"{k:02d}" + "".join(rng.choice(alphabet) for _ in range(n)))[:16]


def log_int(rng, lo, hi):
    """An integer spread over the orders of magnitude of [lo, hi]."""
    import math
    v = int(round(math.exp(rng.uniform(math.log(lo), math.log(hi)))))
    return min(max(v, lo), hi)


def plain_order(rng, q, where="in"):
    """An order that is not a customer's first order."""
    return [day_in(rng, q, where), log_int(rng, 100, 10**9), rng.choice([100, 100, rng.randint(1, 100)]), False]


def logo_order(rng, q, where="in", split=None):
    """A new-logo order (first order of 250,000 cents or more)."""
    return [day_in(rng, q, where), log_int(rng, LOGO, 10**9), split or rng.choice([100, rng.randint(1, 100)]), True]


def any_order(rng, q):
    """Any order at all, dated outside the quarter (carries no line either way)."""
    return [day_in(rng, q, "out"), log_int(rng, 100, 10**9), rng.randint(1, 100), rng.random() < 0.3]


def credit(rng, q, amount, age, where="in"):
    raised = day_in(rng, q, where)
    booked = (model.day(raised) - age * D).isoformat()
    return [raised, booked, amount, rng.choice([100, rng.randint(1, 100)])]


def reversal(rng, q, where="in", age=None):
    return credit(rng, q, log_int(rng, REV, 10**9), rng.randint(0, 365) if age is None else age, where)


def any_credit_out(rng, q):
    return credit(rng, q, log_int(rng, 100, 10**9), rng.randint(0, 365), "out")


def base_rep(rng, k, q=None, draw=None, owed=None, carried=None):
    q = q or quarter(rng)
    return {
        "rep": rep_code(rng, k),
        "quarter": q,
        "quota": log_int(rng, 100000, 10**10),
        "draw": rng.choice([0, 0, log_int(rng, 1, 10**7)]) if draw is None else draw,
        "owed": rng.choice([0, log_int(rng, 1, 10**8)]) if owed is None else owed,
        "carried": rng.choice([0, rng.randint(0, 24999)]) if carried is None else carried,
        "orders": [],
        "credits": [],
    }


def trap_free_lists(rng, r, n_orders=None, n_credits=None):
    q = r["quarter"]
    for _ in range(rng.randint(0, 12) if n_orders is None else n_orders):
        pick = rng.random()
        if pick < 0.6:
            r["orders"].append(plain_order(rng, q))
        elif pick < 0.8:
            r["orders"].append(logo_order(rng, q))
        else:
            r["orders"].append(any_order(rng, q))
    for _ in range(rng.randint(0, 5) if n_credits is None else n_credits):
        if rng.random() < 0.7:
            r["credits"].append(reversal(rng, q))
        else:
            r["credits"].append(any_credit_out(rng, q))
    rng.shuffle(r["orders"])
    rng.shuffle(r["credits"])
    return r


def job(reps):
    return {"reps": reps}


# ---- families -----------------------------------------------------------------------------

def fam_broad(rng):
    return job([trap_free_lists(rng, base_rep(rng, k)) for k in range(rng.randint(1, 8))])


def fam_D1(rng):
    """Bookings above the quota and above twice the quota; exactly on each edge."""
    reps = []
    for k in range(rng.randint(2, 6)):
        r = base_rep(rng, k, draw=0, owed=0)
        q = rng.randint(100000, 10**8)
        r["quota"] = q
        target = rng.choice([q, 2 * q, rng.randint(q + 1, 2 * q - 1), rng.randint(2 * q + 1, 5 * q)])
        r["orders"].append([day_in(rng, r["quarter"]), target, 100, False])
        trap_free_lists(rng, r, n_orders=rng.randint(0, 3), n_credits=0)
        reps.append(r)
    return job(reps)


def fam_D2(rng):
    """Shared deals: splits below 100 per cent."""
    reps = []
    for k in range(rng.randint(2, 6)):
        r = base_rep(rng, k)
        for _ in range(rng.randint(1, 10)):
            r["orders"].append([day_in(rng, r["quarter"]), log_int(rng, 100, 10**9), rng.randint(1, 99), False])
        reps.append(r)
    return job(reps)


def fam_D3(rng):
    """Bookings inside the first band whose 800-bp share leaves a remainder of half a cent or more."""
    reps = []
    for k in range(rng.randint(2, 6)):
        r = base_rep(rng, k, draw=0, owed=0)
        r["quota"] = 10**10
        v = rng.randint(100, 10**9)
        while (v * 800) % 10000 < 5000:
            v = rng.randint(100, 10**9)
        r["orders"].append([day_in(rng, r["quarter"]), v, 100, False])
        reps.append(r)
    return job(reps)


def fam_D4(rng):
    """Reversals raised in the quarter at ages of 91 to 120 days (plus 120 and 121 exactly)."""
    reps = []
    for k in range(rng.randint(2, 6)):
        r = base_rep(rng, k)
        trap_free_lists(rng, r, n_orders=rng.randint(0, 4), n_credits=0)
        for _ in range(rng.randint(1, 4)):
            r["credits"].append(reversal(rng, r["quarter"], age=rng.choice([91, 120, 121, rng.randint(91, 120)])))
        reps.append(r)
    return job(reps)


def fam_D5(rng):
    """New-logo orders where the rep's share is below 10,000 cents."""
    reps = []
    for k in range(rng.randint(2, 6)):
        r = base_rep(rng, k)
        for _ in range(rng.randint(1, 4)):
            v = rng.randint(LOGO, 10**6)
            split = rng.randint(1, max(1, (9999 * 100) // v))
            r["orders"].append([day_in(rng, r["quarter"]), v, split, True])
        reps.append(r)
    return job(reps)


def fam_D6(rng):
    """Reps with no draw whose due lands from 10,000 to 24,999 cents, on 25,000, and around."""
    reps = []
    for k in range(rng.randint(2, 6)):
        r = base_rep(rng, k, draw=0, owed=0)
        r["quota"] = 10**10
        b = rng.randint(0, 250000)
        if b:
            r["orders"].append([day_in(rng, r["quarter"]), max(100, b), 100, False])
        c = model.commission(max(100, b) if b else 0, r["quota"])
        want = rng.choice([25000, 24999, 10000, rng.randint(10000, 24999), rng.randint(10000, 24999)])
        r["carried"] = min(24999, max(0, want - c))
        reps.append(r)
    return job(reps)


def fam_D7(rng):
    """Reps with a draw and an owed balance whose total is above the draw."""
    reps = []
    for k in range(rng.randint(2, 6)):
        r = base_rep(rng, k)
        r["quota"] = 10**10
        v = rng.randint(1000000, 50000000)
        r["orders"].append([day_in(rng, r["quarter"]), v, 100, False])
        total = model.commission(v, r["quota"])
        r["draw"] = rng.randint(1, total)
        r["owed"] = rng.choice([rng.randint(total - r["draw"] + 1, 10**8), rng.randint(1, 10**8)])
        reps.append(r)
    return job(reps)


def fam_TA(rng):
    """Credit notes below 50,000 cents raised in the quarter, at ages across 0-365 days."""
    reps = []
    for k in range(rng.randint(2, 6)):
        r = base_rep(rng, k)
        trap_free_lists(rng, r, n_orders=rng.randint(0, 4), n_credits=rng.randint(0, 2))
        for _ in range(rng.randint(2, 6)):
            age = rng.choice([rng.randint(0, 90), rng.randint(0, 90), 90, 91, rng.randint(91, 120), 120,
                              rng.randint(121, 365)])
            amount = rng.choice([rng.randint(100, 49999), rng.randint(20000, 49999), 49999])
            r["credits"].append(credit(rng, r["quarter"], amount, age))
        rng.shuffle(r["credits"])
        reps.append(r)
    return job(reps)


def fam_TB(rng):
    """First orders below 250,000 cents in the quarter, rep shares across the 10,000 and 25,000 marks."""
    reps = []
    for k in range(rng.randint(2, 6)):
        r = base_rep(rng, k)
        trap_free_lists(rng, r, n_orders=rng.randint(0, 4), n_credits=rng.randint(0, 2))
        for _ in range(rng.randint(2, 6)):
            band = rng.choice(["low", "mid", "mid", "high", "edge"])
            if band == "low":
                v, split = rng.randint(100, 249999), 100
                v = min(v, 9999)
            elif band == "mid":
                v, split = rng.randint(10000, 24999), 100
            elif band == "high":
                v, split = rng.randint(25000, 249999), rng.choice([100, rng.randint(40, 100)])
            else:
                v, split = rng.choice([10000, 24999, 25000, 249999, 9999]), 100
            r["orders"].append([day_in(rng, r["quarter"]), v, split, True])
        rng.shuffle(r["orders"])
        reps.append(r)
    return job(reps)


def fam_fuzz(rng):
    """Everything mixed across the full ranges (model-versus-Oracle fuzz only)."""
    reps = []
    for k in range(rng.randint(1, 10)):
        r = base_rep(rng, k)
        q = r["quarter"]
        for _ in range(rng.randint(0, 30)):
            where = "in" if rng.random() < 0.8 else "out"
            r["orders"].append([day_in(rng, q, where), log_int(rng, 100, 10**9), rng.randint(1, 100),
                                rng.random() < 0.4])
        for _ in range(rng.randint(0, 12)):
            where = "in" if rng.random() < 0.8 else "out"
            r["credits"].append(credit(rng, q, log_int(rng, 100, 10**9), rng.randint(0, 365), where))
        reps.append(r)
    return job(reps)


FAMILIES = {
    "broad": fam_broad,
    "D1": fam_D1,
    "D2": fam_D2,
    "D3": fam_D3,
    "D4": fam_D4,
    "D5": fam_D5,
    "D6": fam_D6,
    "D7": fam_D7,
    "TA": fam_TA,
    "TB": fam_TB,
}
TRAP_FAMILIES = {"TA", "TB"}


def trap_inputs(j):
    """Which trap inputs the job carries: TA (a credit note below 50,000 cents raised in the rep's
    quarter) and TB (a first order below 250,000 cents counting toward the rep's quarter)."""
    found = set()
    for r in j["reps"]:
        q = r["quarter"]
        for raised, _booked, amount, _split in r["credits"]:
            if model.in_span(raised, q) and amount < REV:
                found.add("TA")
        for booked, value, _split, first in r["orders"]:
            if first and model.in_span(booked, q) and value < LOGO:
                found.add("TB")
    return found


def fam_corners(rng):
    """Section 1 limits: 60 reps, 300 orders and 100 credit notes, every field at an end."""
    reps = []
    for k in range(60):
        q = rng.choice(["2020-Q1", "2039-Q4", quarter(rng)])
        r = {
            "rep": (f"{k:02d}" + "Z" * 14)[: rng.choice([2, 16])],
            "quarter": q,
            "quota": rng.choice([100000, 10**10]),
            "draw": rng.choice([0, 1, 10**7]),
            "owed": rng.choice([0, 1, 10**8]),
            "carried": rng.choice([0, 24999]),
            "orders": [],
            "credits": [],
        }
        for _ in range(rng.choice([0, 300])):
            r["orders"].append([day_in(rng, q, rng.choice(["in", "in", "out"])), rng.choice([100, 10**9, 249999, 250000]),
                                rng.choice([1, 100]), rng.random() < 0.5])
        for _ in range(rng.choice([0, 100])):
            r["credits"].append(credit(rng, q, rng.choice([100, 10**9, 49999, 50000]), rng.choice([0, 90, 91, 120, 121, 365]),
                                       rng.choice(["in", "in", "out"])))
        reps.append(r)
    return job(reps)
