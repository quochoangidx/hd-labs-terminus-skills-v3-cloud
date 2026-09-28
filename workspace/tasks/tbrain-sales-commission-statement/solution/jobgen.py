"""Seeded graded jobs for the commission verifier, one family per rule and per case left to today's code.

Used only by solution/seal.py. Every job keeps within plan section 1 (model.limit_problems), and an input
the plan leaves to today's code (see trap_inputs) appears only in the family named for it.
"""

import datetime
import random

import model

SEED = 20260928
D = datetime.timedelta
REV = model.REVERSAL_CENTS
LOGO = model.NEW_LOGO_CENTS
TRAP_INPUTS = {
    "courtesy_credits": {"courtesy_credit"},
    "trial_orders": {"trial_order"},
}


def iso(d):
    return d.isoformat()


def span(q):
    return model.quarter_span(q)


def quarter(rng):
    return f"{rng.randint(2020, 2039)}-Q{rng.randint(1, 4)}"


def inside(rng, q):
    first, last = span(q)
    return first + D(rng.randint(0, (last - first).days))


def outside(rng, q):
    first, last = span(q)
    return first - D(rng.randint(1, 45)) if rng.random() < 0.5 else last + D(rng.randint(1, 45))


def window(rng, q):
    first, last = span(q)
    lo = first - D(45)
    return lo + D(rng.randint(0, (last + D(45) - lo).days))


def log_int(rng, lo, hi):
    import math
    v = int(round(math.exp(rng.uniform(math.log(lo), math.log(hi)))))
    return min(max(v, lo), hi)


class Codes:
    def __init__(self, rng):
        self.rng, self.used = rng, set()

    def __call__(self):
        while True:
            c = "".join(self.rng.choice("ABCDEFGHJKLMNPQRSTUVWXYZ0123456789-") for _ in range(self.rng.randint(1, 16)))
            if c not in self.used:
                self.used.add(c)
                return c


def order(rng, q, value=None, split=None, first=False, where="in"):
    """An order; a first order dated in the quarter is always a new-logo order unless value says otherwise."""
    d = inside(rng, q) if where == "in" else outside(rng, q) if where == "out" else window(rng, q)
    if value is None:
        value = log_int(rng, LOGO if first else 100, 10**9)
    return [iso(d), value, split if split is not None else rng.choice([100, rng.randint(1, 100)]), first]


def credit(rng, q, amount=None, age=None, split=None, where="in"):
    """A credit note; one raised in the quarter is a reversal unless amount says otherwise."""
    d = inside(rng, q) if where == "in" else outside(rng, q) if where == "out" else window(rng, q)
    if amount is None:
        amount = log_int(rng, REV, 10**9)
    age = rng.randint(0, 365) if age is None else age
    return [iso(d), iso(d - D(age)), amount, split if split is not None else rng.choice([100, rng.randint(1, 100)])]


def rep(rng, code, q=None, **kw):
    q = q or quarter(rng)
    r = {
        "rep": code(),
        "quarter": q,
        "quota": log_int(rng, 100000, 10**10),
        "draw": rng.choice([0, 0, log_int(rng, 1, 10**7)]),
        "owed": rng.choice([0, log_int(rng, 1, 10**8)]),
        "carried": rng.choice([0, rng.randint(0, 24999)]),
        "orders": [],
        "credits": [],
    }
    r.update(kw)
    return r


def busy(rng, code, q=None, **kw):
    """A trap-free rep with a mix of every governed input."""
    r = rep(rng, code, q, **kw)
    q = r["quarter"]
    for _ in range(rng.randint(0, 10)):
        pick = rng.random()
        if pick < 0.55:
            r["orders"].append(order(rng, q))
        elif pick < 0.75:
            r["orders"].append(order(rng, q, first=True))
        else:
            r["orders"].append(order(rng, q, value=log_int(rng, 100, 10**9), first=rng.random() < 0.4, where="out"))
    for _ in range(rng.randint(0, 4)):
        if rng.random() < 0.7:
            r["credits"].append(credit(rng, q))
        else:
            r["credits"].append(credit(rng, q, amount=log_int(rng, 100, 10**9), where="out"))
    rng.shuffle(r["orders"])
    rng.shuffle(r["credits"])
    return r


def job(reps):
    return {"reps": reps}


def fam(n, maker):
    rng = random.Random(f"{SEED}:{maker.__name__}")
    return [maker(rng) for _ in range(n)]


# ---- 3. bookings ------------------------------------------------------------------------------

def split_bookings(rng):
    """Shared deals: splits of 1 to 99 per cent, shares landing on half a cent among them."""
    code, reps = Codes(rng), []
    for _ in range(4):
        r = rep(rng, code, draw=0, owed=0, carried=0)
        q = r["quarter"]
        for _ in range(rng.randint(2, 8)):
            r["orders"].append(order(rng, q, value=log_int(rng, 100, 10**9), split=rng.randint(1, 99)))
        r["orders"].append(order(rng, q, value=2 * rng.randint(50, 5 * 10**8) + 1, split=50))  # a half cent, goes up
        r["orders"].append(order(rng, q, value=rng.choice([150, 250, 1050]), split=rng.choice([1, 3, 5, 7, 9])))
        rng.shuffle(r["orders"])
        reps.append(r)
    return job(reps)


def quarter_edges(rng):
    """Orders on the first and last day of the quarter count; the day before and the day after do not."""
    code, reps = Codes(rng), []
    for q in (quarter(rng), quarter(rng), "2039-Q4", "2020-Q1"):
        first, last = span(q)
        r = rep(rng, code, q, draw=0, owed=0, carried=0)
        for d in (first, last, first - D(1), last + D(1), first - D(45), last + D(45)):
            r["orders"].append([iso(d), log_int(rng, 100, 10**9), rng.choice([100, rng.randint(1, 100)]), False])
        r["orders"].append([iso(rng.choice([first, last])), log_int(rng, LOGO, 10**9), 100, True])
        r["orders"].append([iso(rng.choice([first - D(1), last + D(1)])), log_int(rng, 100, 10**9), 100, True])
        rng.shuffle(r["orders"])
        reps.append(r)
    return job(reps)


# ---- 4. commission ----------------------------------------------------------------------------

def bands(rng):
    """Bookings inside each band: up to the quota, between the quota and twice it, and far above."""
    code, reps = Codes(rng), []
    for target in ("low", "mid", "top", "top", "far"):
        q_ = rng.randint(100000, 10**8)
        b = {"low": rng.randint(1, q_), "mid": rng.randint(q_ + 1, 2 * q_ - 1),
             "top": rng.randint(2 * q_ + 1, 4 * q_), "far": 9 * q_}[target]
        r = rep(rng, code, quota=q_, draw=0, owed=0, carried=0)
        parts = sorted(rng.sample(range(1, b), 2)) if b > 3 else []
        values = [y - x for x, y in zip([0] + parts, parts + [b])] if parts else [b]
        for v in values:
            if v >= 100:
                r["orders"].append(order(rng, r["quarter"], value=v, split=100))
        reps.append(r)
    return job(reps)


def band_edges(rng):
    """Bookings exactly on the quota, a cent either side, exactly on twice the quota and a cent either side."""
    code, reps = Codes(rng), []
    q_ = rng.randint(100000, 10**8)
    for b in (q_, q_ - 1, q_ + 1, 2 * q_, 2 * q_ - 1, 2 * q_ + 1):
        r = rep(rng, code, quota=q_, draw=0, owed=0, carried=0)
        r["orders"].append(order(rng, r["quarter"], value=b, split=100))
        reps.append(r)
    r = rep(rng, code, quota=10**10, draw=0, owed=0, carried=0)
    r["orders"] = [order(rng, r["quarter"], value=10**9, split=100) for _ in range(10)]  # exactly on a 10^10 quota
    reps.append(r)
    return job(reps)


def band_rounding(rng):
    """Each band's commission rounds on its own: remainders above and below half a cent in every band."""
    code, reps = Codes(rng), []
    for _ in range(6):
        q_ = rng.randint(100000, 10**7)
        while (q_ * 800) % 10000 < 5000:
            q_ += 1
        mid = rng.randint(1, q_ - 1)
        top = rng.randint(1, q_)
        r = rep(rng, code, quota=q_, draw=0, owed=0, carried=0)
        r["orders"].append(order(rng, r["quarter"], value=q_ + mid + (q_ - mid) * rng.choice([0, 1]) + top * rng.choice([0, 1]), split=100))
        reps.append(r)
    return job(reps)


# ---- 5. clawback ------------------------------------------------------------------------------

def reversal_window(rng):
    """Reversals raised in the quarter at ages 0 to 365: clawed back up to 120 days, not after."""
    code, reps = Codes(rng), []
    for _ in range(4):
        r = rep(rng, code, draw=0, owed=0, carried=rng.randint(0, 24999))
        q = r["quarter"]
        r["orders"].append(order(rng, q, value=log_int(rng, 10**7, 10**9)))
        for age in (rng.randint(0, 90), rng.randint(91, 120), rng.randint(91, 120), rng.randint(121, 365), 365, 0):
            r["credits"].append(credit(rng, q, age=age))
        r["credits"].append(credit(rng, q, amount=log_int(rng, 100, 10**9), where="out"))
        rng.shuffle(r["credits"])
        reps.append(r)
    return job(reps)


def reversal_age_edge(rng):
    """Reversals at ages of exactly 120 and 121 days, on the quarter's first and last days."""
    code, reps = Codes(rng), []
    for q in (quarter(rng), "2024-Q1"):
        first, last = span(q)
        r = rep(rng, code, q, quota=10**10, draw=0, owed=0, carried=0)
        r["orders"].append(order(rng, q, value=10**9, split=100))
        for d, age in ((first, 120), (last, 121), (last, 120), (first, 121)):
            r["credits"].append([iso(d), iso(d - D(age)), log_int(rng, REV, 10**8), rng.choice([100, rng.randint(1, 100)])])
        reps.append(r)
    return job(reps)


def reversal_threshold(rng):
    """Credit notes of exactly 50,000 cents raised at ages 91 to 120 days are reversals and are clawed back."""
    code, reps = Codes(rng), []
    for split in (100, 50, 1, 37):
        r = rep(rng, code, quota=10**10, draw=0, owed=0, carried=0)
        q = r["quarter"]
        r["orders"].append(order(rng, q, value=10**8, split=100))
        r["credits"].append(credit(rng, q, amount=REV, age=rng.randint(91, 120), split=split))
        r["credits"].append(credit(rng, q, amount=REV, age=rng.randint(0, 90), split=split))
        reps.append(r)
    return job(reps)


def clawback_quarter(rng):
    """Credit notes raised the day before or after the quarter carry no line; on its first and last days they do."""
    code, reps = Codes(rng), []
    for q in (quarter(rng), quarter(rng)):
        first, last = span(q)
        r = rep(rng, code, q, quota=10**10, draw=0, owed=0, carried=0)
        r["orders"].append(order(rng, q, value=10**9, split=100))
        for d in (first, last, first - D(1), last + D(1)):
            r["credits"].append([iso(d), iso(d - D(rng.randint(0, 120))), log_int(rng, REV, 10**8), 100])
        r["credits"].append([iso(first - D(1)), iso(first - D(30)), rng.randint(100, REV - 1), 100])  # small, outside
        reps.append(r)
    return job(reps)


def courtesy_credits(rng):  # left to today's code
    """Credit notes below 50,000 cents raised in the quarter, at ages across 0-365 days, amounts across the range."""
    code, reps = Codes(rng), []
    for _ in range(3):
        r = rep(rng, code, quota=10**10, draw=0, owed=0, carried=0)
        q = r["quarter"]
        r["orders"].append(order(rng, q, value=10**9, split=100))
        for age in (rng.randint(0, 89), 90, 91, rng.randint(92, 119), 120, rng.randint(121, 365)):
            r["credits"].append(credit(rng, q, amount=rng.choice([rng.randint(100, 49999), 49999, rng.randint(20000, 49999)]),
                                       age=age, split=rng.choice([100, rng.randint(1, 100)])))
        r["credits"].append(credit(rng, q, amount=100, age=rng.randint(0, 90), split=1))
        r["credits"].append(credit(rng, q, age=rng.randint(0, 120)))  # a reversal beside them
        rng.shuffle(r["credits"])
        reps.append(r)
    return job(reps)


# ---- 6. new-logo bonus ------------------------------------------------------------------------

def new_logo(rng):
    """New-logo orders earn 300 bp of the rep's share, small splits (shares below 10,000 cents) included;
    orders that are not first orders earn none."""
    code, reps = Codes(rng), []
    for _ in range(4):
        r = rep(rng, code, quota=10**10, draw=0, owed=0, carried=0)
        q = r["quarter"]
        for _ in range(3):
            v = rng.randint(LOGO, 10**6)
            r["orders"].append(order(rng, q, value=v, split=rng.randint(1, max(1, 999900 // v)), first=True))
        r["orders"].append(order(rng, q, value=log_int(rng, LOGO, 10**9), split=100, first=True))
        r["orders"].append(order(rng, q, value=log_int(rng, 100, 10**9), first=False))
        r["orders"].append(order(rng, q, value=250050, split=100, first=True))  # 7,501.5 goes up
        rng.shuffle(r["orders"])
        reps.append(r)
    return job(reps)


def new_logo_threshold(rng):
    """A first order of exactly 250,000 cents is a new-logo order, whatever the split."""
    code, reps = Codes(rng), []
    for split in (1, 2, 3, 100):
        r = rep(rng, code, quota=10**10, draw=0, owed=0, carried=0)
        r["orders"].append(order(rng, r["quarter"], value=LOGO, split=split, first=True))
        reps.append(r)
    return job(reps)


def trial_orders(rng):  # left to today's code
    """First orders below 250,000 cents in the quarter, rep shares below 10,000, from 10,000 to 24,999 and above."""
    code, reps = Codes(rng), []
    for _ in range(3):
        r = rep(rng, code, quota=10**10, draw=0, owed=0, carried=0)
        q = r["quarter"]
        for v, split in ((rng.randint(100, 9999), 100), (rng.randint(10000, 24999), 100), (rng.randint(25000, LOGO - 1), 100),
                         (rng.choice([10000, 24999, 25000, LOGO - 1]), 100), (rng.randint(20000, LOGO - 1), rng.randint(1, 99)),
                         (100, 1)):
            r["orders"].append(order(rng, q, value=v, split=split, first=True))
        r["orders"].append(order(rng, q, value=log_int(rng, LOGO, 10**8), split=100, first=True))  # a new-logo order beside them
        r["orders"].append(order(rng, q, value=log_int(rng, 100, 10**9), first=False))
        rng.shuffle(r["orders"])
        reps.append(r)
    return job(reps)


# ---- 7. draw and payment ----------------------------------------------------------------------

def _paying(rng, code, commission_cents, **kw):
    """A rep whose only input is a non-first order worth the given commission in the first band (quota 10^10)."""
    assert commission_cents == 0 or commission_cents >= 8, commission_cents
    r = rep(rng, code, quota=10**10, **kw)
    v = commission_cents * 10000 // 800
    while model.commission(v, 10**10) != commission_cents:
        v += 1
    if v:
        r["orders"].append(order(rng, r["quarter"], value=v, split=100))
    return r


def draw_shortfall(rng):
    """A total below the draw: the draw is paid and the shortfall is added to what the rep owes."""
    code, reps = Codes(rng), []
    for _ in range(4):
        draw = rng.randint(100000, 10**7)
        reps.append(_paying(rng, code, rng.choice([0, rng.randint(8, draw - 1)]), draw=draw, owed=rng.choice([0, rng.randint(1, 10**8)]),
                            carried=rng.randint(0, 24999)))
    return job(reps)


def draw_edge(rng):
    """A total exactly on the draw, a cent under and a cent over, with and without an owed balance."""
    code, reps = Codes(rng), []
    for delta, owed in ((0, 0), (0, 5 * 10**7), (-1, 12345), (1, 10**8), (1, 0)):
        draw = rng.randint(100000, 10**7)
        carried = rng.randint(0, 24999)
        r = _paying(rng, code, draw + delta - carried, draw=draw, owed=owed, carried=carried)
        assert model.statement(r)["total"] == draw + delta
        reps.append(r)
    return job(reps)


def negative_total(rng):
    """Clawback heavier than everything else: totals below nought, with a draw of nought and above."""
    code, reps = Codes(rng), []
    for draw in (0, 0, rng.randint(1, 10**7), 10**7):
        r = rep(rng, code, quota=10**10, draw=draw, owed=rng.choice([0, rng.randint(1, 10**8)]), carried=rng.randint(0, 24999))
        q = r["quarter"]
        r["orders"].append(order(rng, q, value=rng.randint(100, 10**6), split=100))
        r["credits"].append(credit(rng, q, amount=log_int(rng, 10**7, 10**9), age=rng.randint(0, 120), split=100))
        reps.append(r)
    return job(reps)


def recovery(rng):
    """A draw and an owed balance: recovery comes only out of the part of the total above the draw."""
    code, reps = Codes(rng), []
    for _ in range(5):
        c = rng.randint(200000, 4 * 10**6)
        draw = rng.randint(1, c - 1)
        owed = rng.choice([rng.randint(c - draw + 1, 10**8), rng.randint(1, c - draw), c - draw])
        reps.append(_paying(rng, code, c, draw=draw, owed=owed, carried=0))
    return job(reps)


def minimum_payment(rng):
    """A rep with no draw: dues of 25,000 cents and more are paid, smaller dues carried (10,000 to 24,999 among them)."""
    code, reps = Codes(rng), []
    for want in (rng.randint(10000, 24999), rng.randint(10000, 24999), rng.randint(0, 9999), rng.randint(25001, 60000),
                 rng.randint(10000, 24999)):
        carried = want if want < 8 else rng.randint(0, min(want - 8, 24999))
        r = _paying(rng, code, want - carried, draw=0, owed=0, carried=carried)
        reps.append(r)
    r = _paying(rng, code, 30000, draw=0, owed=rng.randint(5001, 20000), carried=0)  # recovery takes the due below the minimum
    reps.append(r)
    r = _paying(rng, code, 12000, draw=rng.randint(1, 12000), owed=0, carried=0)  # a rep on a draw is paid a small due
    reps.append(r)
    reps.append(_paying(rng, code, 30000, draw=0, owed=0, carried=rng.randint(1, 99)))  # a carried amount of a few cents
    reps.append(_paying(rng, code, 24990, draw=0, owed=0, carried=rng.randint(10, 99)))
    return job(reps)


def minimum_edge(rng):
    """Dues of exactly 24,999 and 25,000 cents, and an empty rep whose due is nought."""
    code, reps = Codes(rng), []
    for want in (24999, 25000, 25000):
        carried = rng.randint(0, 24990)
        reps.append(_paying(rng, code, want - carried, draw=0, owed=0, carried=carried))
    reps.append(rep(rng, code, draw=0, owed=0, carried=0))
    return job(reps)


def empty_rep(rng):
    """A job of one rep with no orders and no credit notes: every figure nought, the due of nought carried."""
    return job([rep(rng, Codes(rng), draw=0, owed=0, carried=0)])


# ---- whole statements -------------------------------------------------------------------------

NAMES = ["A", "Z" * 16, " SE-01 ", 'R"\\/1', "é-営業担当", "x", "0000000000000001"]


def statement_order(rng):
    code, reps = Codes(rng), []
    for name in NAMES:
        r = busy(rng, code)
        r["rep"] = name
        reps.append(r)
    return job(reps)


def limits_reps(rng):
    """Section 1 ends on every field, trap-free."""
    code, reps = Codes(rng), []
    for q in ("2020-Q1", "2039-Q4", "2024-Q1", "2031-Q3"):
        first, last = span(q)
        r = rep(rng, code, q, quota=rng.choice([100000, 10**10]), draw=rng.choice([0, 10**7]),
                owed=rng.choice([0, 10**8]), carried=rng.choice([0, 24999]))
        r["orders"] = [[iso(first - D(45)), 100, 1, True], [iso(last + D(45)), 10**9, 100, False], [iso(first), 10**9, 100, True],
                       [iso(last), 100, 1, False], [iso(inside(rng, q)), 10**9, 1, False], [iso(inside(rng, q)), LOGO, 1, True]]
        r["credits"] = [[iso(last), iso(last - D(365)), 10**9, 100], [iso(first), iso(first), REV, 1],
                        [iso(first - D(45)), iso(first - D(410)), 100, 1], [iso(last + D(45)), iso(last + D(45)), 10**9, 100]]
        reps.append(r)
    r = rep(rng, code, "2029-Q3", quota=10**10, draw=10**7, owed=10**8, carried=0)  # the draw's top pays a shortfall
    r["orders"] = [[iso(inside(rng, "2029-Q3")), 100, 1, False]]
    reps.append(r)
    return job(reps)


REPEAT = {"orders": 300, "credits": 100}


def limits_job(rng):
    """One rep holding one entry per list at the tops; the verifier repeats each entry to the list's longest
    (REPEAT: 300 orders of 10^9 cents, bookings 3 x 10^11; 100 reversals of 10^9 cents clawed back) and the rep
    under 60 fresh codes."""
    code = Codes(rng)
    q = "2035-Q2"
    first, last = span(q)
    r = rep(rng, code, q, quota=100000, draw=10**7, owed=10**8, carried=24999)
    r["orders"] = [[iso(last), 10**9, 100, True]]
    r["credits"] = [[iso(first), iso(first), 10**9, 100]]
    return job([r])


def expand(j):
    """limits_job as graded: each list entry repeated to the list's longest."""
    r = dict(j["reps"][0])
    for key, n in REPEAT.items():
        r[key] = r[key] * n
    return dict(j, reps=[r])


def generated(rng):
    code = Codes(rng)
    return job([busy(rng, code) for _ in range(rng.randint(2, 6))])


FAMILIES = {
    "split_bookings": (1, split_bookings), "quarter_edges": (1, quarter_edges),
    "bands": (1, bands), "band_edges": (1, band_edges), "band_rounding": (1, band_rounding),
    "reversal_window": (1, reversal_window), "reversal_age_edge": (1, reversal_age_edge),
    "reversal_threshold": (1, reversal_threshold), "clawback_quarter": (1, clawback_quarter),
    "courtesy_credits": (2, courtesy_credits),
    "new_logo": (1, new_logo), "new_logo_threshold": (1, new_logo_threshold), "trial_orders": (2, trial_orders),
    "draw_shortfall": (1, draw_shortfall), "draw_edge": (1, draw_edge), "negative_total": (1, negative_total),
    "recovery": (1, recovery), "minimum_payment": (1, minimum_payment), "minimum_edge": (1, minimum_edge), "empty_rep": (1, empty_rep),
    "statement_order": (1, statement_order), "limits_reps": (1, limits_reps), "limits_job": (1, limits_job),
    "generated": (4, generated),
}


def families():
    return {name: fam(n, maker) for name, (n, maker) in FAMILIES.items()}


def trap_inputs(j):
    """courtesy_credit: a credit note below 50,000 cents raised in the rep's quarter; trial_order: a first order
    below 250,000 cents booked in the rep's quarter."""
    found = set()
    for r in j["reps"]:
        q = r["quarter"]
        for raised, _booked, amount, _split in r["credits"]:
            if model.in_span(raised, q) and amount < REV:
                found.add("courtesy_credit")
        for booked, value, _split, first in r["orders"]:
            if first and model.in_span(booked, q) and value < LOGO:
                found.add("trial_order")
    return found
