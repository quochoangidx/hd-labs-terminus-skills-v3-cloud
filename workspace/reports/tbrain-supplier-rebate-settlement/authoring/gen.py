"""Seeded job families for tbrain-supplier-rebate-settlement (authoring only, never shipped).

Families: `broad` (trap-free, whole ranges), one per departure D1-D7, one per trap TA, TB, TC.
A trap's input (see trap_inputs) appears only in its own family.
"""

import datetime
import importlib.util
import string
import sys
from pathlib import Path

TASK = Path(__file__).resolve().parents[4] / "workspace" / "tasks" / "tbrain-supplier-rebate-settlement"
_spec = importlib.util.spec_from_file_location("rebate_model", TASK / "solution" / "model.py")
model = importlib.util.module_from_spec(_spec)
sys.modules["rebate_model"] = model
_spec.loader.exec_module(model)

D = datetime.timedelta


def iso(d):
    return d.isoformat()


def quarter(rng):
    return f"{rng.randint(2020, 2039)}-Q{rng.randint(1, 4)}"


def code(rng, used):
    while True:
        n = rng.randint(1, 16)
        c = "".join(rng.choice(string.ascii_uppercase + string.digits + "-") for _ in range(n))
        if c not in used:
            used.add(c)
            return c


def span(q):
    return model.quarter_span(q)


def any_day(rng, q, inside=None):
    first, last = span(q)
    if inside is True:
        return first + D(rng.randint(0, (last - first).days))
    lo, hi = first - D(45), last + D(45)
    return lo + D(rng.randint(0, (hi - lo).days))


def mid_day(rng, q):
    """A day at least 5 days from either quarter edge, inside the quarter."""
    first, last = span(q)
    return first + D(rng.randint(5, (last - first).days - 5))


def tiers(rng, n=None):
    n = n or rng.randint(1, 12)
    th = sorted(rng.sample(range(1, 400), n - 1))
    rows = [{"from": 0, "bp": rng.randint(0, 1500)}]
    scale = rng.choice([10000, 50000, 200000])
    for t in th:
        rows.append({"from": t * scale, "bp": rng.randint(0, 1500)})
    return rows


def carton(rng, q, inside=True):
    d = mid_day(rng, q) if inside else any_day(rng, q)
    return [iso(d), rng.randint(12, 5000), rng.randint(100, 1000000 if rng.random() < 0.2 else 20000)]


def small_mid(rng, q):
    return [iso(mid_day(rng, q)), rng.randint(1, 11), rng.randint(100, 20000)]


def ret(rng, q):
    return [iso(any_day(rng, q)), rng.randint(1, 300), rng.randint(100, 20000)]


def drop(rng, q):
    old = rng.randint(400, 1000000)
    new = rng.randint(1, old - 250)
    return [iso(any_day(rng, q)), old, new, rng.randint(100, 50000)]


def contract(rng, q):
    cost = rng.randint(200, 1000000)
    price = rng.randint(1, cost - 100)
    return [iso(any_day(rng, q)), rng.randint(1, 5000), cost, price]


def out_adjustment(rng, q):
    """A tidy-up notice outside the quarter (no trap input)."""
    first, last = span(q)
    d = first - D(rng.randint(1, 45)) if rng.random() < 0.5 else last + D(rng.randint(1, 45))
    old = rng.randint(300, 100000)
    return [iso(d), old, old - rng.randint(1, 249), rng.randint(100, 50000)]


def account(rng, used, q=None, **kw):
    q = q or quarter(rng)
    acc = {"account": code(rng, used), "quarter": q, "prior": 0,
           "purchases": [carton(rng, q, inside=rng.random() < 0.7) for _ in range(rng.randint(0, 12))]
           + [small_mid(rng, q) for _ in range(rng.randint(0, 3))],
           "returns": [ret(rng, q) for _ in range(rng.randint(0, 4))],
           "notices": [drop(rng, q) for _ in range(rng.randint(0, 3))] + [out_adjustment(rng, q) for _ in range(rng.randint(0, 1))],
           "sales": [contract(rng, q) for _ in range(rng.randint(0, 4))]}
    # carton lines of the broad draw must not create a small-line boundary case (they are 12+)
    acc["prior"] = rng.choice([0, rng.randint(1, 10**8), rng.randint(1, 10**11)])
    acc.update(kw)
    for k in ("purchases", "returns", "notices", "sales"):
        rng.shuffle(acc[k])
    return acc


def job(rng, accounts, t=None):
    return {"tiers": t or tiers(rng), "accounts": accounts}


# ---- families ----

def fam_broad(rng):
    used = set()
    return job(rng, [account(rng, used) for _ in range(rng.randint(1, 8))])


def fam_D1(rng):  # carton shipments near both quarter edges
    used, accs = set(), []
    for _ in range(rng.randint(1, 4)):
        q = quarter(rng)
        first, last = span(q)
        lines = []
        for _ in range(rng.randint(1, 6)):
            d = rng.choice([first - D(rng.randint(1, 4)), last - D(rng.randint(0, 3)), first + D(rng.randint(0, 3))])
            lines.append([iso(d), rng.randint(12, 5000), rng.randint(100, 20000)])
        accs.append(account(rng, used, q=q, purchases=lines + [carton(rng, q)]))
    return job(rng, accs)


def fam_D2(rng):  # returns large enough that gross and net reach different tiers
    used, accs = set(), []
    t = [{"from": 0, "bp": 100}, {"from": 1000000, "bp": 300}, {"from": 5000000, "bp": 700}]
    for _ in range(rng.randint(1, 4)):
        q = quarter(rng)
        d = mid_day(rng, q)
        buy = [[iso(d), 500, rng.randint(2000, 2400)]]                  # 1.0M-1.2M
        back = [[iso(mid_day(rng, q)), rng.randint(260, 300), 1000]]
        accs.append(account(rng, used, q=q, purchases=buy, returns=back, notices=[], sales=[]))
    return job(rng, accs, t)


def fam_D3(rng):  # net purchases exactly on a threshold
    used, accs = set(), []
    t = tiers(rng, rng.randint(2, 6))
    for _ in range(rng.randint(1, 4)):
        q = quarter(rng)
        target = rng.choice(t[1:])["from"] if len(t) > 1 else 0
        lines = [[iso(mid_day(rng, q)), 100, 100]]  # 10,000 cents
        rest = target - 10000
        units, price = 5000, 0
        for u in range(5000, 11, -1):
            if rest % u == 0 and 100 <= rest // u <= 10**6:
                units, price = u, rest // u
                break
        if price:
            lines.append([iso(mid_day(rng, q)), units, price])
            accs.append(account(rng, used, q=q, purchases=lines, returns=[], notices=[], sales=[]))
    if not accs:
        return fam_D3(rng)
    return job(rng, accs, t)


def fam_D4(rng):  # returns in the quarter
    used = set()
    accs = []
    for _ in range(rng.randint(1, 4)):
        q = quarter(rng)
        accs.append(account(rng, used, q=q, returns=[[iso(any_day(rng, q, inside=True)), rng.randint(1, 5000),
                                                         rng.randint(100, 20000)] for _ in range(rng.randint(1, 5))]))
    return job(rng, accs)


def fam_D5(rng):  # growth of 110 per cent or more over a positive prior
    used, accs = set(), []
    for _ in range(rng.randint(1, 4)):
        a = account(rng, used, returns=[])
        net = model.account(a, [{"from": 0, "bp": 0}])["net"]
        if net <= 0:
            a["purchases"].append(carton(rng, a["quarter"]))
            net = model.account(a, [{"from": 0, "bp": 0}])["net"]
        a["prior"] = rng.randint(max(1, net * 100 // 300), net * 100 // 110)
        accs.append(a)
    return job(rng, accs)


def fam_D6(rng):  # settlements between 5,000 and 24,999 cents
    used, accs = set(), []
    t = [{"from": 0, "bp": 100}]
    for _ in range(rng.randint(1, 5)):
        q = quarter(rng)
        cents = rng.randint(500000, 2499900)   # 1% gives 5,000-24,999
        accs.append(account(rng, used, q=q, prior=0, returns=[], notices=[], sales=[],
                            purchases=[[iso(mid_day(rng, q)), 100, cents // 100]]))
    return job(rng, accs, t)


def fam_D7(rng):  # rebates with a fractional cent, exact halves included
    used, accs = set(), []
    t = [{"from": 0, "bp": rng.choice([1, 3, 7, 50, 125, 333])}]
    for _ in range(rng.randint(1, 5)):
        q = quarter(rng)
        accs.append(account(rng, used, q=q, returns=[], notices=[], sales=[], prior=0,
                            purchases=[[iso(mid_day(rng, q)), rng.randint(12, 999), rng.randint(101, 9999)]]))
    return job(rng, accs, t)


def fam_TA(rng):  # tidy-up notices (not price drops) in the quarter
    used, accs = set(), []
    for _ in range(rng.randint(1, 4)):
        q = quarter(rng)
        notes = []
        for _ in range(rng.randint(1, 4)):
            cut = rng.randint(1, 249)
            band = rng.choice([(1, 4999), (5000, 24999), (5000, 24999), (25000, 10**9)])
            lo, hi = max(100, -(-band[0] // cut)), min(50000, band[1] // cut)
            on_hand = rng.randint(lo, hi) if lo <= hi else rng.randint(100, 50000)
            old = rng.randint(cut + 1, 100000)
            notes.append([iso(any_day(rng, q, inside=True)), old, old - cut, on_hand])
        notes.append(drop(rng, q))
        accs.append(account(rng, used, q=q, notices=notes))
    return job(rng, accs)


def fam_TB(rng):  # price-match sales (not contract sales) in the quarter
    used, accs = set(), []
    for _ in range(rng.randint(1, 4)):
        q = quarter(rng)
        sales = []
        for _ in range(rng.randint(1, 4)):
            below = rng.choice([rng.randint(25, 39), rng.randint(1, 99)])
            cost = rng.randint(max(200, below + 1), 100000)
            sales.append([iso(any_day(rng, q, inside=True)), rng.randint(1, 5000), cost, cost - below])
        sales.append(contract(rng, q))
        accs.append(account(rng, used, q=q, sales=sales))
    return job(rng, accs)


def fam_TC(rng):  # loose-unit lines invoiced in the last four days before a quarter edge
    used, accs = set(), []
    for _ in range(rng.randint(1, 4)):
        q = quarter(rng)
        first, last = span(q)
        lines = []
        for _ in range(rng.randint(1, 4)):
            d = rng.choice([first - D(rng.randint(1, 4)), last - D(rng.randint(0, 3))])
            lines.append([iso(d), rng.randint(1, 11), rng.randint(100, 1000000)])
        accs.append(account(rng, used, q=q, purchases=lines + [carton(rng, q)]))
    return job(rng, accs)


def fam_limits(rng):  # section 1 ends: 100 accounts, 12 rows, 400 lines, 1e11 thresholds and priors
    used = set()
    th = sorted(rng.sample(range(1, 10**11), 10)) + [10**11]
    t = [{"from": 0, "bp": 1500}] + [{"from": x, "bp": rng.randint(0, 1500)} for x in th]
    accs = []
    for k in range(100 if rng.random() < 0.3 else 3):
        q = rng.choice(["2020-Q1", "2039-Q4", quarter(rng)])
        first, last = span(q)
        a = account(rng, used, q=q)
        a["account"] = ("Z" * 16 if k == 0 else a["account"])
        if k < 3:
            a["purchases"] = [[iso(rng.choice([first - D(45), last + D(45), mid_day(rng, q)])), rng.choice([12, 5000]),
                               rng.choice([100, 10**6])] for _ in range(400)]
            a["returns"] = [[iso(rng.choice([first, last, first - D(45)])), rng.choice([1, 5000]), rng.choice([100, 10**6])] for _ in range(100)]
            a["notices"] = [[iso(rng.choice([first, last])), 10**6, rng.choice([1, 10**6 - 250]), rng.choice([100, 50000])] for _ in range(50)]
            a["sales"] = [[iso(rng.choice([first, last])), rng.choice([1, 5000]), 10**6, rng.choice([1, 10**6 - 100])] for _ in range(200)]
            a["prior"] = rng.choice([10**11, 1, 0])
        accs.append(a)
    return job(rng, accs, t)


FAMILIES = {"broad": fam_broad, "limits": fam_limits, "D1": fam_D1, "D2": fam_D2, "D3": fam_D3, "D4": fam_D4, "D5": fam_D5,
            "D6": fam_D6, "D7": fam_D7, "TA": fam_TA, "TB": fam_TB, "TC": fam_TC}
TRAP_FAMILIES = {"TA", "TB", "TC"}


def trap_inputs(job):
    """Which trap inputs a job carries."""
    found = set()
    for a in job["accounts"]:
        first, last = span(a["quarter"])
        inq = lambda d: first <= d <= last  # noqa: E731
        for inv, u, _c in a["purchases"]:
            d = model.day(inv)
            if u < 12 and inq(d) != inq(d + D(4)):
                found.add("TC")
        for e, o, n, _h in a["notices"]:
            if inq(model.day(e)) and o - n < 250:
                found.add("TA")
        for s, _u, c, p in a["sales"]:
            if inq(model.day(s)) and c - p < 100:
                found.add("TB")
    return found
