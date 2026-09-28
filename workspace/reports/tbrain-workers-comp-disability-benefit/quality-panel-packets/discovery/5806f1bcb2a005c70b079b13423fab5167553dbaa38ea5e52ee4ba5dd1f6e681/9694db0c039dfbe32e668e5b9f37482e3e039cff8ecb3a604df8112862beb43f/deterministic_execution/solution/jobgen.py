"""Graded jobs for the verifier, one list of jobs per family (authoring side; never run by the verifier).

Every job is drawn from a seeded generator (SEED below) or built by hand, keeps within manual section 1,
and carries only the inputs its family declares in TRAP_INPUTS: "correction" (a wage line below a week's
pay, 2,000 cents, paid on the payday in the week of injury or in the first base week, where the week it
counts toward decides whether it is in the base period) and "low_week" (a week of the partial earnings
below 1,000 cents). solution/seal.py writes them, with the statements solution/model.py works out, into
tests/expected/.
"""

import random
from datetime import date, timedelta

import model

SEED = 20260927
D = timedelta(days=1)
W7 = timedelta(days=7)
LAST = date(2035, 12, 31)
WEEKS_PAY = 2_000
PARTIAL_WEEK = 1_000
TRAP_INPUTS = {
    "corrections": {"correction"},
    "differential-corrections": {"correction"},
    "low_partial_weeks": {"low_week"},
    "differential-low_partial_weeks": {"low_week"},
}


def iso(d):
    return d.isoformat()


def sunday(d):
    return d + timedelta(days=6 - d.weekday())


def base_sundays(injury):
    s = sunday(injury)
    return [s - W7 * k for k in range(13, 0, -1)]


def payday_line(week_sunday, cents):
    """The line paying the week that ends on week_sunday, on the Friday after it."""
    return [iso(week_sunday + timedelta(days=5)), cents]


def payday_in(week_sunday):
    """The Friday inside the payroll week that ends on week_sunday."""
    return week_sunday - timedelta(days=2)


def is_edge_correction(injury, paid, cents):
    if cents >= WEEKS_PAY:
        return False
    d = date.fromisoformat(paid)
    weeks = set(base_sundays(injury))
    return (sunday(d) in weeks) != ((sunday(d) - W7) in weeks)


def trap_inputs(job):
    out = set()
    for c in job["claims"]:
        inj = date.fromisoformat(c["injury"])
        if any(is_edge_correction(inj, p, a) for p, a in c["wages"]):
            out.add("correction")
        if any(e < PARTIAL_WEEK for _w, e in c["earnings"]):
            out.add("low_week")
    return out


class Gen:
    def __init__(self, seed):
        self.rng = random.Random(seed)
        self.n = 0

    def cid(self):
        self.n += 1
        return f"WC-{self.rng.randint(10**6, 10**7 - 1)}-{self.n:03d}"

    def day(self, lo, hi):
        return lo + timedelta(days=self.rng.randint(0, (hi - lo).days))

    def injury(self, lo=date(2017, 3, 1), hi=date(2033, 6, 30), weekday=None):
        d = self.day(lo, hi)
        if weekday is not None:
            d += timedelta(days=(weekday - d.weekday()) % 7)
        return d

    def pay(self, lo=20_000, hi=250_000):
        return self.rng.randint(lo, hi)

    def wages(self, injury, weeks=None, lo=20_000, hi=250_000, before=1, after=False, corrections=(), safe_corrections=0):
        """Weekly wages for the base weeks given (all thirteen by default), `before` weeks before the base period,
        the paydays after it up to 30 days past the injury, and correction lines."""
        base = base_sundays(injury)
        weeks = sorted(self.rng.sample(base, self.rng.randint(6, 13))) if weeks is None else weeks
        lines = [payday_line(w, self.pay(lo, hi)) for w in weeks]
        w = base[0]
        for _ in range(before):
            w -= W7
            if w + timedelta(days=5) >= injury - timedelta(days=400):
                lines.append(payday_line(w, self.pay(lo, hi)))
        if after:
            w = sunday(injury)
            while w + timedelta(days=5) <= injury + timedelta(days=30):
                lines.append(payday_line(w, self.pay(WEEKS_PAY, hi)))
                w += W7
        for paid, cents in corrections:
            lines.append([iso(paid), cents])
        for _ in range(safe_corrections):
            lines.append([iso(payday_in(self.rng.choice(base[1:]))), self.rng.randint(1, WEEKS_PAY - 1)])
        self.rng.shuffle(lines)
        return lines

    def periods(self, injury, lengths, gap=(1, 20), start=None):
        out = []
        first = injury + D * (self.rng.randint(0, 3) if start is None else start)
        for n in lengths:
            last = first + D * (n - 1)
            out.append([iso(first), iso(last)])
            first = last + D * (self.rng.randint(*gap) + 1)
        return out

    def claim(self, injury, wages, periods, earnings=()):
        return {"claim": self.cid(), "injury": iso(injury), "wages": wages, "disability": periods, "earnings": list(earnings)}

    def partial(self, periods, earned):
        """Weeks after the last disability day earning the amounts given."""
        w = sunday(date.fromisoformat(periods[-1][1])) + W7
        out = []
        for e in earned:
            out.append([iso(w), e])
            w += W7 * self.rng.randint(1, 2)
        return out


OPEN = [{"from": "2016-01-01", "max": 400_000, "min": 1_000}]


def job(rates, claims):
    return {"rates": rates, "claims": claims}


def families():
    g = Gen(SEED)
    fam = {}

    # 2.2/3.1: a week's pay counts toward the week before its payday's; injuries on every day of the week,
    # the payday in the week of injury paying the last base week, wages varying week to week.
    jobs = []
    for weekday in range(7):
        inj = g.injury(weekday=weekday)
        jobs.append(job(OPEN, [g.claim(inj, g.wages(inj, lo=30_000, hi=240_000, before=2, after=True), g.periods(inj, [20]))]))
    fam["weeks_pay"] = [job(OPEN, jobs[k]["claims"] + jobs[k + 1]["claims"]) for k in (0, 2, 4)] + [jobs[6]]

    # 2.2: a line of exactly 2,000 cents is a week's pay (on the edge paydays); lines of 1,999 only inside the base period
    claims = []
    # (each claim holds one edge line of 2,000 cents, so the two edges never cancel)
    for weekday, edge in ((0, "last"), (4, "first"), (6, "last"), (2, "first")):
        inj = g.injury(weekday=weekday)
        base = base_sundays(inj)
        wages = g.wages(inj, weeks=base[1:], before=0, after=False)
        wages += [payday_line(sunday(inj) - W7 if edge == "last" else base[0] - W7, 2_000), [iso(payday_in(base[5])), 1_999]]
        claims.append(g.claim(inj, wages, g.periods(inj, [9])))
    fam["weeks_pay_threshold"] = [job(OPEN, claims)]

    # 2.1/2.3: the base period is the thirteen weeks before the week of injury: injury on a Monday, a Friday
    # payday, a Sunday; wages outside the base period much larger than inside
    claims = []
    for weekday in (0, 4, 5, 6):
        inj = g.injury(weekday=weekday)
        wages = g.wages(inj, lo=40_000, hi=60_000, before=0, after=False)
        base = base_sundays(inj)
        wages += [payday_line(base[0] - W7, 480_000), payday_line(sunday(inj), 470_000), payday_line(sunday(inj) + W7, 460_000)]
        claims.append(g.claim(inj, wages, g.periods(inj, [15])))
    fam["base_period"] = [job(OPEN, claims)]

    # 3.3: the base-period wages over thirteen, whatever the number of weeks paid (1, 5, 9, 12, 13), with two lines on a payday
    claims = []
    for k in (1, 5, 9, 12, 13):
        inj = g.injury()
        base = base_sundays(inj)
        weeks = sorted(g.rng.sample(base, k))
        wages = g.wages(inj, weeks=weeks, before=2)
        wages.append(payday_line(weeks[-1], g.pay()))
        claims.append(g.claim(inj, wages, g.periods(inj, [10, 6])))
    fam["average_weekly_wage"] = [job(OPEN, claims[:3]), job(OPEN, claims[3:])]

    # 3.3: no wage line counts toward the base period (no lines at all; lines only outside it): nought
    inj, inj2 = g.injury(), g.injury()
    per = g.periods(inj, [16])
    fam["no_base_wages"] = [job([{"from": "2016-01-01", "max": 150_000, "min": 30_000}], [
        g.claim(inj, [], per, g.partial(per, [1_000, 50_000])),
        g.claim(inj2, g.wages(inj2, weeks=[], before=3), g.periods(inj2, [5])),
    ])]

    # 3.4: two thirds of the AWW, the caps far away; partial weeks of 1,000 cents or more at two thirds of the loss
    claims = []
    for _ in range(4):
        inj = g.injury()
        per = g.periods(inj, [g.rng.randint(20, 60)])
        c = g.claim(inj, g.wages(inj), per)
        aww = model.average_weekly_wage(c)
        c["earnings"] = g.partial(per, [g.rng.randint(PARTIAL_WEEK, max(PARTIAL_WEEK, aww - 1)) for _ in range(3)])
        claims.append(c)
    fam["rate_two_thirds"] = [job(OPEN, claims)]

    # 2.4/3.4: the row in force on the date of injury: the day before a row takes effect, the day it does, a
    # later day; the maximum binding and the minimum binding
    jobs = []
    for offset in (-1, 0, 45):
        change = g.injury(lo=date(2019, 1, 1), hi=date(2031, 1, 1))
        rows = [{"from": iso(change - D * 700), "max": 50_000, "min": 20_000},
                {"from": iso(change - D * 300), "max": 80_000, "min": 38_000},
                {"from": iso(change), "max": 130_000, "min": 52_000},
                {"from": iso(change + D * 400), "max": 170_000, "min": 60_000}]
        inj = change + D * offset
        hi = g.claim(inj, g.wages(inj, lo=240_000, hi=250_000), g.periods(inj, [21]))
        lo = g.claim(inj, g.wages(inj, lo=62_000, hi=64_000), g.periods(inj, [21]))
        jobs.append(job(rows, [hi, lo]))
    fam["row_in_force"] = jobs

    # 3.4: the maximum and the minimum bound two thirds of the AWW (at, above and below each)
    rows = [{"from": "2016-01-01", "max": 100_000, "min": 40_000}]
    claims = []
    for weekly in (150_000, 150_001, 149_998, 60_000, 60_002, 59_999):  # 2/3 of it at, above, below 100,000 / 40,000
        inj = g.injury()
        base = base_sundays(inj)
        wages = [payday_line(w, weekly) for w in base]
        claims.append(g.claim(inj, wages, g.periods(inj, [30])))
    fam["rate_bounds"] = [job(rows, claims)]

    # 3.5: an AWW below the minimum is the rate; at the minimum it is not; partial weeks for such a worker
    rows = [{"from": "2016-01-01", "max": 200_000, "min": 45_000}]
    claims = []
    for weekly in (44_999, 45_000, 30_000, 2_000):
        inj = g.injury()
        per = g.periods(inj, [18])
        wages = [payday_line(w, weekly) for w in base_sundays(inj)]
        c = g.claim(inj, wages, per)
        c["earnings"] = g.partial(per, [PARTIAL_WEEK, max(PARTIAL_WEEK, weekly // 2)])
        claims.append(c)
    fam["low_wage_rate"] = [job(rows, claims)]

    # 2.5: both ends of every period: one-day periods, a period of 399 days, twelve periods
    claims = []
    inj = g.injury(hi=date(2031, 1, 1))
    claims.append(g.claim(inj, g.wages(inj), g.periods(inj, [1])))
    inj = g.injury(hi=date(2031, 1, 1))
    claims.append(g.claim(inj, g.wages(inj), g.periods(inj, [1, 1, 2, 1])))
    inj = g.injury(hi=date(2031, 1, 1))
    claims.append(g.claim(inj, g.wages(inj), g.periods(inj, [399])))
    inj = g.injury(hi=date(2031, 1, 1))
    claims.append(g.claim(inj, g.wages(inj), g.periods(inj, [g.rng.randint(1, 30) for _ in range(12)])))
    fam["disability_days"] = [job(OPEN, claims)]

    # 2.6: the waiting period is three days: claims of 1, 2, 3, 4 and 13 disability days
    claims = []
    for lengths in ([1], [2], [1, 2], [4], [6, 7]):
        inj = g.injury()
        claims.append(g.claim(inj, g.wages(inj), g.periods(inj, lengths)))
    fam["waiting_period"] = [job(OPEN, claims)]

    # 4.1: retroactive from fourteen disability days: 13, 14 (in one period and over three), 15
    claims = []
    for lengths in ([13], [14], [5, 4, 5], [15]):
        inj = g.injury()
        claims.append(g.claim(inj, g.wages(inj), g.periods(inj, lengths)))
    fam["retroactive_days"] = [job(OPEN, claims)]

    # 4.3/1.1: rate x paid days / 7 to the nearest cent: remainders 1..6 sevenths
    claims = []
    want = [1, 2, 3, 4, 5, 6]
    while want:
        inj = g.injury()
        c = g.claim(inj, g.wages(inj), g.periods(inj, [g.rng.randint(15, 60)]))
        s = model.statement(c, OPEN)
        r = (s["rate"] * s["ttd_days"]) % 7
        if r in want:
            want.remove(r)
            claims.append(c)
    fam["ttd_rounding"] = [job(OPEN, claims)]

    # 5.1: a week of partial disability pays two thirds of its wage loss, no more than the weekly rate
    rows = [{"from": "2016-01-01", "max": 70_000, "min": 10_000}]
    claims = []
    for _ in range(3):
        inj = g.injury()
        per = g.periods(inj, [g.rng.randint(15, 40)])
        c = g.claim(inj, g.wages(inj, lo=150_000, hi=240_000), per)
        c["earnings"] = g.partial(per, [PARTIAL_WEEK, g.rng.randint(1_000, 40_000), g.rng.randint(90_000, 140_000)])
        # and an uncapped week whose two thirds of loss ends in two thirds of a cent (rounds up)
        aww = model.average_weekly_wage(c)
        c["earnings"].append([iso(date.fromisoformat(c["earnings"][-1][0]) + W7), aww - 30_001])
        claims.append(c)
    fam["partial_benefit"] = [job(rows, claims)]

    # 2.8: a week of exactly 1,000 cents is a week of partial disability (caps far away)
    claims = []
    for _ in range(3):
        inj = g.injury()
        per = g.periods(inj, [10])
        c = g.claim(inj, g.wages(inj, lo=30_000, hi=90_000), per)
        c["earnings"] = g.partial(per, [PARTIAL_WEEK, PARTIAL_WEEK, 1_001])
        claims.append(c)
    fam["partial_week_threshold"] = [job(OPEN, claims)]

    # 2.7: a week earning the AWW or more has no wage loss
    claims = []
    for _ in range(3):
        inj = g.injury()
        per = g.periods(inj, [12])
        c = g.claim(inj, g.wages(inj, lo=20_000, hi=80_000), per)
        aww = model.average_weekly_wage(c)
        c["earnings"] = g.partial(per, [aww, aww - 1, aww + 1, 500_000])
        claims.append(c)
    fam["no_wage_loss"] = [job(OPEN, claims)]

    # T1: a correction below a week's pay on the payday of the week of injury (before and after the injury) or of
    # the first base week counts toward its payday's week (today's step); full base periods, open table
    claims = []
    for weekday, where, cents in ((0, "injury", 1), (2, "injury", 1_999), (4, "injury", 750), (6, "first", 1_999),
                                  (3, "first", 13), (1, "first", 26), (5, "both", 1_200)):
        inj = g.injury(weekday=weekday)
        base = base_sundays(inj)
        corr = []
        if where in ("injury", "both"):
            corr.append((payday_in(sunday(inj)), cents))
        if where in ("first", "both"):
            corr.append((payday_in(base[0]), cents))
        claims.append(g.claim(inj, g.wages(inj, after=True, corrections=corr), g.periods(inj, [20])))
    fam["corrections"] = [job(OPEN, claims[:3]), job(OPEN, claims[3:])]

    # T2: weeks of the partial earnings below 1,000 cents (0, 1, 500, 999) beside weeks of partial disability;
    # the cap does not bind (open table), so 60 per cent and two thirds differ
    claims = []
    for earned in ([0, 30_000], [1, 999], [500, 0, 2_000], [999]):
        inj = g.injury()
        per = g.periods(inj, [g.rng.randint(15, 40)])
        c = g.claim(inj, g.wages(inj, lo=40_000, hi=200_000), per)
        c["earnings"] = g.partial(per, earned)
        claims.append(c)
    fam["low_partial_weeks"] = [job(OPEN, claims[:2]), job(OPEN, claims[2:])]

    # 6.1/README: statements in job order, claim numbers as given (one character, twenty-four, non-ASCII, quotes)
    claims = []
    for name in ("Z", "0" * 24, "WCé-ñ事故", 'A "q" \\ b', " sp ", "a", "B"):
        inj = g.injury()
        c = g.claim(inj, g.wages(inj), g.periods(inj, [g.rng.randint(1, 30)]))
        c["claim"] = name
        claims.append(c)
    fam["statement_order"] = [job(OPEN, claims)]

    fam["limits_claims"], fam["limits_job"] = limits(g)
    fam["generated"] = [generated(g) for _ in range(2)]
    return fam


def limits(g):
    """Section 1 ends: 200 claims, 40 rows, 120 wage lines, 12 periods, 104 partial weeks, 1 and 500,000 cents,
    dates at 2016-01-01 and 2035-12-31, a 399-day period, row figures at their ends."""
    rows = [{"from": "2016-01-01", "max": 400_000, "min": 1_000}]
    d = date(2016, 1, 1)
    for k in range(39):
        d += D * g.rng.randint(60, 180)
        mx = [20_000, 400_000, g.rng.randint(20_000, 400_000)][k % 3]
        mn = [1_000, mx - 1, g.rng.randint(1_000, mx - 1)][k % 3]
        rows.append({"from": iso(d), "max": mx, "min": mn})
    rows[-1]["from"] = "2035-12-31"
    assert all(date.fromisoformat(rows[i]["from"]) < date.fromisoformat(rows[i + 1]["from"]) for i in range(39))
    claims = []
    # (120 wage lines, twelve periods of 400 days and 104 partial weeks: the second job below)
    # a wage line paid on 2016-01-01 (a Friday) and lines of 1 cent inside the base period; twelve periods ending on 2035-12-31
    inj = date(2016, 2, 3)
    base = base_sundays(inj)
    wages = g.wages(inj, weeks=[w for w in base if w + D * 5 >= date(2016, 1, 1)], before=0) + [["2016-01-01", 1]]
    wages += [[iso(payday_in(base[-2])), 1]]
    claims.append(g.claim(inj, wages, g.periods(inj, [1] * 11 + [3])))
    inj = date(2035, 1, 10)
    per = g.periods(inj, [10] * 11, start=0)
    per.append([iso(date.fromisoformat(per[-1][1]) + D * 2), "2035-12-31"])
    claims.append(g.claim(inj, g.wages(inj), per))
    # a line paid exactly 400 days before the injury (a Saturday injury), and one exactly 30 days after it (a
    # Wednesday injury); periods one day apart; a partial week beginning the day after the last disability day
    inj = g.injury(lo=date(2018, 1, 1), hi=date(2030, 1, 1), weekday=5)
    claims.append(g.claim(inj, g.wages(inj, before=0, after=False) + [[iso(inj - D * 400), g.pay()]], g.periods(inj, [3, 5], gap=(0, 0))))
    inj = g.injury(lo=date(2018, 1, 1), hi=date(2030, 1, 1), weekday=2)
    last = inj + D * ((6 - inj.weekday()) % 7)  # a Sunday
    per = [[iso(inj), iso(last)]]
    c = g.claim(inj, g.wages(inj, after=False) + [[iso(inj + D * 30), g.pay()]], per)
    c["earnings"] = [[iso(last + W7), 1_000], [iso(last + W7 * 2), 500_000]]
    claims.append(c)
    # an injury on the day the first row takes effect (2016-01-01), with no wage lines yet
    claims.append(g.claim(date(2016, 1, 1), [], [["2016-01-01", "2016-01-01"]]))
    big = [job(rows, claims)]
    # the tops of the derived sums: rate at the 400,000 maximum over twelve periods of 400 days, 104 partial weeks
    inj = date(2016, 4, 6)
    base = base_sundays(inj)
    wages = [payday_line(base[k % 13], 500_000) for k in range(120)]
    per = []
    first = inj
    for _ in range(12):
        per.append([iso(first), iso(first + D * 399)])
        first += D * 401
    c = g.claim(inj, wages, per)
    c["earnings"] = g.partial(per, [500_000 if k % 2 else PARTIAL_WEEK for k in range(104)])
    big.append(job([{"from": "2016-01-01", "max": 400_000, "min": 1_000}], [c]))
    # ten small claims against the 40-row table (one week's pay, one period); the verifier repeats them under
    # fresh claim numbers to make one job of 200 claims
    many = []
    for k in range(10):
        inj = g.injury(lo=date(2017, 3, 1), hi=date(2033, 1, 1))
        wk = base_sundays(inj)[g.rng.randint(0, 12)]
        many.append({"claim": f"L{k:03d}", "injury": iso(inj), "wages": [payday_line(wk, g.pay(WEEKS_PAY, 500_000))],
                     "disability": [[iso(inj), iso(inj + D * g.rng.randint(0, 20))]], "earnings": []})
    return big, [job(rows, many)]


def generated(g):
    """A seeded trap-free job over the governed domain."""
    rng = g.rng
    n = rng.randint(1, 6)
    dates = sorted({date(2016, 1, 1)} | {g.day(date(2016, 1, 2), date(2034, 1, 1)) for _ in range(n - 1)})
    rows = []
    for d in dates:
        mx = rng.randint(60_000, 200_000)
        rows.append({"from": iso(d), "max": mx, "min": rng.randint(1_000, min(60_000, mx - 1))})
    claims = []
    for _ in range(rng.randint(2, 4)):
        inj = g.injury()
        weeks = sorted(rng.sample(base_sundays(inj), rng.randint(1, 13)))
        per = g.periods(inj, [rng.randint(1, 60) for _ in range(rng.randint(1, 4))])
        c = g.claim(inj, g.wages(inj, weeks=weeks, lo=WEEKS_PAY, hi=300_000, before=rng.randint(0, 3), after=rng.random() < 0.5,
                                 safe_corrections=rng.randint(0, 3)), per)
        aww = model.average_weekly_wage(c)
        c["earnings"] = g.partial(per, [rng.choice([PARTIAL_WEEK, rng.randint(PARTIAL_WEEK, max(PARTIAL_WEEK, aww + 20_000))])
                                        for _ in range(rng.randint(0, 5))])
        claims.append(c)
    return job(rows, claims)


def differential_pairs():
    """Pairs of jobs for the shipped differential.

    corrections: b adds to a one correction below a week's pay on an edge payday (the week of injury's, where
    today's step leaves it out of the base period; or the first base week's, moved in b from a mid-period
    payday, where today's step keeps it in): the shipped package gives both the same AWW, and so must the candidate.
    low_partial_weeks: a and b differ in one week of the partial earnings, earning 0 in a and 995 in b, the cap
    not binding: the shipped package's partial amounts differ by 60 per cent of 995 (597 cents), and so must the
    candidate's.
    """
    g = Gen(SEED + 1)
    pairs = {"corrections": [], "low_partial_weeks": []}
    for weekday in (4,):
        inj = g.injury(weekday=weekday)
        base = base_sundays(inj)
        wages = g.wages(inj, weeks=base, lo=30_000, hi=200_000, after=True)
        per = g.periods(inj, [20])
        a = g.claim(inj, wages + [[iso(payday_in(base[4])), 1_500]], per)
        b = dict(a, wages=wages + [[iso(payday_in(base[4])), 1_500], [iso(payday_in(sunday(inj))), 1_999]])
        pairs["corrections"].append((job(OPEN, [a]), job(OPEN, [b])))
        a2 = g.claim(inj, wages + [[iso(payday_in(base[6])), 777]], per)
        b2 = dict(a2, wages=wages + [[iso(payday_in(base[0])), 777]])
        pairs["corrections"].append((job(OPEN, [a2]), job(OPEN, [b2])))
    for _ in range(2):
        inj = g.injury()
        per = g.periods(inj, [30])
        a = g.claim(inj, g.wages(inj, lo=60_000, hi=200_000), per)
        weeks = g.partial(per, [g.rng.randint(PARTIAL_WEEK, 20_000), 0])
        a["earnings"] = weeks
        b = dict(a, earnings=[weeks[0], [weeks[1][0], 995]])
        pairs["low_partial_weeks"].append((job(OPEN, [a]), job(OPEN, [b])))
    return pairs
