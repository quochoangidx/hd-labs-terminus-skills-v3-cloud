"""Seeded job generator for tbrain-workers-comp-disability-benefit (authoring only, never shipped).

Families: `broad` (trap-free, the governed domain), one per departure D1-D8, one per trap
T1 (a payroll correction below a week's pay on a payday at the edge of the base period) and
T2 (a week of the partial earnings below 1,000 cents), and `fuzz` (everything section 1 allows,
trap inputs included, at every scale).
"""

import importlib.util
from datetime import date, timedelta
from fractions import Fraction
from pathlib import Path

TASK = Path(__file__).resolve().parents[3] / "tasks" / "tbrain-workers-comp-disability-benefit"
_spec = importlib.util.spec_from_file_location("td_model", TASK / "solution" / "model.py")
model = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(model)

D = timedelta(days=1)
W7 = timedelta(days=7)
FIRST, LAST = date(2016, 1, 1), date(2035, 12, 31)
WEEKS_PAY = 2_000
PARTIAL_WEEK = 1_000


def iso(d):
    return d.isoformat()


def sunday(d):
    return d + timedelta(days=6 - d.weekday())


def rand_day(rng, lo, hi):
    return lo + timedelta(days=rng.randint(0, (hi - lo).days))


def base_sundays(injury):
    s = sunday(injury)
    return [s - W7 * k for k in range(13, 0, -1)]  # oldest first


def pay(rng, lo=20_000, hi=250_000, wide=False):
    """A week's wages (always a week's pay: 2,000 cents or more)."""
    if wide and rng.random() < 0.15:
        return rng.choice([WEEKS_PAY, rng.randint(WEEKS_PAY, 5_000), 500_000, rng.randint(400_000, 500_000)])
    return rng.randint(max(lo, WEEKS_PAY), hi)


def correction(rng):
    """A correction line smaller than a week's pay."""
    return rng.choice([1, WEEKS_PAY - 1, rng.randint(1, 99), rng.randint(1, WEEKS_PAY - 1)])


# ---------------------------------------------------------------- wage lines (all on Fridays)

def friday_of(week_sunday):
    return week_sunday - timedelta(days=2)


def weeks_wages(week_sunday, cents):
    """The line paying the week ending week_sunday, on the Friday after it."""
    return [iso(week_sunday + timedelta(days=5)), cents]


def wage_lines(rng, injury, base_paid, *, lo=20_000, hi=250_000, wide=False, before=(1, 12), after=True,
               corrections=0, where="safe"):
    """Wages for the chosen base weeks, some weeks before and after, and correction lines.

    where: 'safe' (the payday's week and the week before are both in or both out of the base period),
    'edge' (the payday in the week of injury or in the first base week), or 'any'.
    """
    base = base_sundays(injury)
    s_inj = sunday(injury)
    lines = [weeks_wages(w, pay(rng, lo, hi, wide)) for w in base_paid]
    earliest = injury - timedelta(days=400)
    w = base[0] - W7
    for _ in range(rng.randint(*before)):
        if w + timedelta(days=5) < earliest:
            break
        if rng.random() < 0.9:
            lines.append(weeks_wages(w, pay(rng, lo, hi, wide)))
        w -= W7
    if after:
        w = s_inj
        while w + timedelta(days=5) <= injury + timedelta(days=30):
            if rng.random() < 0.6:
                lines.append(weeks_wages(w, pay(rng, WEEKS_PAY, hi, wide)))
            w += W7
    for _ in range(corrections):
        lines.append([iso(correction_day(rng, injury, where)), correction(rng)])
    rng.shuffle(lines)
    return lines[:120]


def correction_day(rng, injury, where):
    base = base_sundays(injury)
    s_inj = sunday(injury)
    lo, hi = injury - timedelta(days=400), injury + timedelta(days=30)
    while True:
        if where == "edge":
            d = friday_of(rng.choice([s_inj, base[0]]))
        elif where == "safe":
            r = rng.random()
            if r < 0.6:
                d = friday_of(rng.choice(base[1:]))
            elif r < 0.8:
                d = friday_of(base[0] - W7 * rng.randint(1, 50))
            else:
                d = friday_of(s_inj + W7 * rng.randint(1, 4))
        else:
            d = friday_of(sunday(rand_day(rng, lo, hi)))
        if lo <= d <= hi:
            return d


def is_edge_correction(injury, paid, cents):
    """A line below a week's pay whose payday's week and the week before straddle the base period."""
    if cents >= WEEKS_PAY:
        return False
    d = date.fromisoformat(paid)
    weeks = set(base_sundays(injury))
    return (sunday(d) in weeks) != ((sunday(d) - W7) in weeks)


# ---------------------------------------------------------------- disability and partial weeks

def periods(rng, injury, count=None, max_len=60, one_day=0.1):
    count = count or rng.randint(1, 4)
    out = []
    start = injury + timedelta(days=rng.randint(0, 5))
    for _ in range(count):
        length = 1 if rng.random() < one_day else rng.randint(1, max_len)
        end = start + timedelta(days=length - 1)
        if end > LAST - timedelta(days=800):
            break
        out.append([iso(start), iso(end)])
        start = end + timedelta(days=rng.randint(1, 30) + 1)
    if not out:
        out.append([iso(injury), iso(injury)])
    return out


def partial_weeks(rng, pers, aww, count=None, over=0.2, low=0.0):
    """Weeks after the last disability day; `low` is the chance of a week below 1,000 cents."""
    count = rng.randint(0, 6) if count is None else count
    last = date.fromisoformat(pers[-1][1])
    w = sunday(last) + W7
    out = []
    for _ in range(count):
        if w > LAST:
            break
        r = rng.random()
        if r < low:
            earned = rng.choice([0, 0, PARTIAL_WEEK - 1, rng.randint(0, PARTIAL_WEEK - 1)])
        elif r < low + over:
            earned = rng.choice([PARTIAL_WEEK, max(PARTIAL_WEEK, aww), aww + rng.randint(1, 50_000), rng.randint(PARTIAL_WEEK, 500_000)])
        else:
            earned = rng.randint(PARTIAL_WEEK, max(PARTIAL_WEEK, aww - 1))
        out.append([iso(w), min(500_000, earned)])
        w += W7 * rng.randint(1, 3)
    return out


# ---------------------------------------------------------------- rate tables

def open_table():
    """One row that never binds for ordinary wages."""
    return [{"from": "2016-01-01", "max": 400_000, "min": 1_000}]


def table(rng, n=None, first=date(2016, 1, 1)):
    n = n or rng.randint(1, 6)
    dates = sorted({first} | {rand_day(rng, first + D, LAST) for _ in range(n - 1)})
    rows = []
    for d in dates:
        mx = rng.randint(60_000, 200_000) if rng.random() < 0.9 else rng.choice([20_000, 400_000, rng.randint(20_000, 400_000)])
        mn = rng.randint(1_000, min(60_000, mx - 1)) if rng.random() < 0.9 else rng.choice([1_000, mx - 1])
        rows.append({"from": iso(d), "max": mx, "min": mn})
    return rows


def injury_day(rng, lo=date(2017, 2, 10), hi=date(2033, 6, 30)):
    return rand_day(rng, lo, hi)


def claim(cid, injury, lines, pers, earnings_fn=None):
    c = {"claim": cid, "injury": iso(injury), "wages": lines, "disability": pers, "earnings": []}
    if earnings_fn:
        c["earnings"] = earnings_fn(model.average_weekly_wage(c))
    return c


def some_weeks(rng, injury, least=1, most=13):
    return sorted(rng.sample(base_sundays(injury), rng.randint(least, most)))


def cid(rng, i):
    return f"WC{rng.randint(10**5, 10**7)}{chr(65 + i % 26)}"


def simple_claim(rng, i, *, weeks=None, pers=None, earn=False, lo=20_000, hi=250_000, inj=None, corrections=0, where="safe",
                 low=0.0):
    inj = inj or injury_day(rng)
    lines = wage_lines(rng, inj, weeks(inj) if weeks else base_sundays(inj), lo=lo, hi=hi, corrections=corrections, where=where)
    p = pers(inj) if pers else periods(rng, inj)
    fn = (lambda aww: partial_weeks(rng, p, aww, low=low)) if earn else None
    return claim(cid(rng, i), inj, lines, p, fn)


# ---------------------------------------------------------------- families

def fam_broad(rng):
    rates = table(rng)
    first = date.fromisoformat(rates[0]["from"])
    claims = []
    for i in range(rng.randint(1, 6)):
        inj = injury_day(rng, lo=max(first, date(2017, 2, 10)))
        lines = wage_lines(rng, inj, some_weeks(rng, inj, 1, 13), wide=True, corrections=rng.randint(0, 3))
        pers = periods(rng, inj, max_len=rng.choice([10, 40, 120]))
        claims.append(claim(cid(rng, i), inj, lines, pers, lambda aww, p=pers: partial_weeks(rng, p, aww)))
    return {"rates": rates, "claims": claims}


def fam_d1(rng):  # 2.2/3.1 a week's pay counts toward the week before its payday's week
    return {"rates": open_table(), "claims": [simple_claim(rng, i) for i in range(rng.randint(1, 3))]}


def fam_d2(rng):  # 3.3 divided by thirteen whatever the number of weeks paid
    return {"rates": open_table(), "claims": [
        simple_claim(rng, i, weeks=lambda inj: some_weeks(rng, inj, 1, 12)) for i in range(rng.randint(1, 3))]}


def fam_d3(rng):  # 3.4 two thirds, caps far away
    return {"rates": open_table(), "claims": [simple_claim(rng, i, earn=True) for i in range(rng.randint(1, 3))]}


def fam_d4(rng):  # 2.4/3.4 the row in force on the date of injury
    inj = injury_day(rng, lo=date(2018, 1, 1), hi=date(2030, 12, 31))
    rows = [
        {"from": iso(inj - timedelta(days=rng.randint(0, 300))), "max": rng.randint(60_000, 90_000), "min": rng.randint(30_000, 40_000)},
        {"from": iso(inj + timedelta(days=rng.randint(1, 200))), "max": rng.randint(110_000, 160_000), "min": rng.randint(45_000, 58_000)},
    ]
    if rng.random() < 0.5:
        rows.insert(0, {"from": iso(inj - timedelta(days=rng.randint(400, 700))), "max": 50_000, "min": 20_000})
    claims = [simple_claim(rng, 0, inj=inj, lo=200_000, hi=250_000), simple_claim(rng, 1, inj=inj, lo=62_000, hi=66_000)]
    return {"rates": rows, "claims": claims}


def fam_d5(rng):  # 3.5 an average weekly wage below the minimum is the rate
    mn = rng.randint(30_000, 60_000)
    rates = [{"from": "2016-01-01", "max": 300_000, "min": mn}]
    return {"rates": rates, "claims": [simple_claim(rng, i, lo=max(WEEKS_PAY, mn // 3), hi=mn - 1, earn=True)
                                       for i in range(rng.randint(1, 3))]}


def fam_d6(rng):  # 2.5 both ends of a period count
    return {"rates": open_table(), "claims": [
        simple_claim(rng, i, pers=lambda inj: periods(rng, inj, count=rng.randint(1, 5), max_len=9, one_day=0.4))
        for i in range(rng.randint(1, 3))]}


def fam_d7(rng):  # 2.6 three waiting days: disability of four to thirteen days (never retroactive)
    def pers(inj):
        n = rng.randint(4, 13)
        return [[iso(inj + D), iso(inj + D * n)]]
    return {"rates": open_table(), "claims": [simple_claim(rng, i, pers=pers) for i in range(rng.randint(1, 3))]}


def fam_d8(rng):  # 4.3/1.1 total-disability amount rounded to the nearest cent
    rates = open_table()
    claims = []
    while len(claims) < 3:
        c = simple_claim(rng, len(claims), pers=lambda inj: periods(rng, inj, count=2, max_len=30))
        s = model.statement(c, rates)
        if (s["rate"] * s["ttd_days"]) % 7 >= 4:
            claims.append(c)
    return {"rates": rates, "claims": claims}


def fam_t1(rng):  # trap T1: a correction below a week's pay on a payday at the edge of the base period
    return {"rates": open_table(), "claims": [simple_claim(rng, i, corrections=rng.randint(1, 2), where="edge")
                                              for i in range(rng.randint(1, 3))]}


def fam_t2(rng):  # trap T2: weeks of the partial earnings below 1,000 cents (beside ordinary ones)
    while True:
        job = {"rates": open_table(), "claims": [simple_claim(rng, i, earn=True, low=0.6) for i in range(rng.randint(1, 3))]}
        if "T2" in trap_inputs(job):
            return job


def fam_fuzz(rng):
    """Everything section 1 allows, trap inputs included, at every scale."""
    big = rng.random() < 0.08
    rates = table(rng, n=40 if big and rng.random() < 0.5 else None)
    first = date.fromisoformat(rates[0]["from"])
    claims = []
    for i in range(200 if big else rng.randint(1, 5)):
        inj = injury_day(rng, lo=max(first, date(2017, 2, 10)))
        if rng.random() < 0.03:
            lines = []
        else:
            lines = wage_lines(rng, inj, some_weeks(rng, inj, 0 if rng.random() < 0.05 else 1, 13), wide=True,
                               before=(0, 45), corrections=rng.randint(0, 60 if big else 6), where=rng.choice(["edge", "safe", "any"]))
        pers = periods(rng, inj, count=12 if big else None, max_len=rng.choice([3, 14, 60, 399]), one_day=0.2)
        claims.append(claim(f"C{i}-{rng.randint(0, 10**6)}", inj, lines, pers,
                            lambda aww, p=pers: partial_weeks(rng, p, aww, count=104 if big else None, over=0.3, low=0.3)))
    return {"rates": rates, "claims": claims}


FAMILIES = {
    "broad": fam_broad, "D1": fam_d1, "D2": fam_d2, "D3": fam_d3, "D4": fam_d4, "D5": fam_d5, "D6": fam_d6,
    "D7": fam_d7, "D8": fam_d8, "T1": fam_t1, "T2": fam_t2,
}
TRAP_FAMILIES = {"T1", "T2"}


def trap_inputs(job):
    """Which trap inputs a job carries: T1 = a line below a week's pay straddling the base period's edge,
    T2 = a week of the partial earnings below 1,000 cents whose benefit 60 and 66 2/3 per cent tell apart."""
    out = set()
    for c in job["claims"]:
        inj = date.fromisoformat(c["injury"])
        if any(is_edge_correction(inj, p, a) for p, a in c["wages"]):
            out.add("T1")
        if c["earnings"]:
            s = model.statement(c, job["rates"])
            aww, rate = s["aww"], s["rate"]
            for _w, e in c["earnings"]:
                if e < PARTIAL_WEEK:
                    loss = aww - e if e < aww else 0
                    if min(model.cents(Fraction(3, 5) * loss), rate) != min(model.cents(Fraction(2, 3) * loss), rate):
                        out.add("T2")
    return out
