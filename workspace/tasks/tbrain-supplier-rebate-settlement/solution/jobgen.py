"""Seeded graded jobs for the rebate verifier, one family per rule and per case left to today's code.

Used only by solution/seal.py. Every job keeps within Schedule R section 1 (model.within_limits), and an
input the schedule leaves to today's code (see trap_inputs) appears only in the family named for it.
"""

import datetime
import random

import model

SEED = 20260928
D = datetime.timedelta
CARTON = 12
TRAP_INPUTS = {
    "loose_units": {"loose_edge"},
    "tidy_ups": {"tidy_up"},
    "price_match": {"price_match"},
}


def iso(d):
    return d.isoformat()


def span(q):
    return model.quarter_span(q)


def quarter(rng):
    return f"{rng.randint(2020, 2039)}-Q{rng.randint(1, 4)}"


def mid(rng, q):
    first, last = span(q)
    return first + D(rng.randint(5, (last - first).days - 5))


def inside(rng, q):
    first, last = span(q)
    return first + D(rng.randint(0, (last - first).days))


def window(rng, q):
    first, last = span(q)
    lo = first - D(45)
    return lo + D(rng.randint(0, (last + D(45) - lo).days))


class Codes:
    def __init__(self, rng):
        self.rng, self.used = rng, set()

    def __call__(self):
        while True:
            c = "".join(self.rng.choice("ABCDEFGHJKLMNPQRSTUVWXYZ0123456789-") for _ in range(self.rng.randint(1, 16)))
            if c not in self.used:
                self.used.add(c)
                return c


def tiers(rng, n=None):
    n = n or rng.randint(1, 12)
    scale = rng.choice([10000, 50000, 200000])
    rows = [{"from": 0, "bp": rng.randint(0, 1500)}]
    for t in sorted(rng.sample(range(1, 400), n - 1)):
        rows.append({"from": t * scale, "bp": rng.randint(0, 1500)})
    return rows


def carton(rng, q, anywhere=True):
    d = window(rng, q) if anywhere else mid(rng, q)
    return [iso(d), rng.randint(CARTON, 5000), rng.randint(100, 20000)]


def loose_mid(rng, q):
    return [iso(mid(rng, q)), rng.randint(1, CARTON - 1), rng.randint(100, 20000)]


def ret(rng, q):
    return [iso(window(rng, q)), rng.randint(1, 300), rng.randint(100, 20000)]


def drop(rng, q):
    old = rng.randint(400, 1000000)
    return [iso(window(rng, q)), old, rng.randint(1, old - 250), rng.randint(100, 50000)]


def contract(rng, q):
    cost = rng.randint(200, 1000000)
    return [iso(window(rng, q)), rng.randint(1, 5000), cost, rng.randint(1, cost - 100)]


def account(rng, code, q=None, **kw):
    q = q or quarter(rng)
    a = {"account": code(), "quarter": q, "prior": rng.choice([0, rng.randint(1, 10**8), rng.randint(1, 10**11)]),
         "purchases": [carton(rng, q) for _ in range(rng.randint(0, 3))] + [loose_mid(rng, q) for _ in range(rng.randint(0, 1))],
         "returns": [ret(rng, q) for _ in range(rng.randint(0, 1))],
         "notices": [drop(rng, q) for _ in range(rng.randint(0, 1))],
         "sales": [contract(rng, q) for _ in range(rng.randint(0, 1))]}
    a.update(kw)
    for k in ("purchases", "returns", "notices", "sales"):
        rng.shuffle(a[k])
    return a


def job(rng, accounts, t=None):
    return {"tiers": t or tiers(rng), "accounts": accounts}


def bare(rng, code, q, **kw):
    """An account with only what its family needs."""
    a = {"account": code(), "quarter": q, "prior": 0, "purchases": [], "returns": [], "notices": [], "sales": []}
    a.update(kw)
    return a


def fam(n, maker):
    rng = random.Random(f"{SEED}-{maker.__name__}")
    return [maker(rng) for _ in range(n)]


# ---------------- rule families ----------------

def carton_receipt(rng):
    code, accs = Codes(rng), []
    for _ in range(rng.randint(2, 4)):
        q = quarter(rng)
        first, last = span(q)
        days = [first - D(k) for k in (1, 2, 3, 4)] + [last - D(k) for k in (0, 1, 2, 3)] + [first - D(5), last - D(4)]
        lines = [[iso(rng.choice(days)), rng.randint(12, 5000), rng.randint(100, 20000)] for _ in range(rng.randint(2, 5))]
        accs.append(account(rng, code, q=q, purchases=lines + [carton(rng, q, False)]))
    return job(rng, accs)


def carton_threshold(rng):
    code, accs = Codes(rng), []
    for _ in range(3):
        q = quarter(rng)
        first, last = span(q)
        lines = [[iso(first - D(rng.randint(1, 4))), 12, rng.randint(100, 20000)],
                 [iso(last - D(rng.randint(0, 3))), 12, rng.randint(100, 20000)]]
        accs.append(bare(rng, code, q, purchases=lines))
    return job(rng, accs, [{"from": 0, "bp": 250}])


def loose_units(rng):  # left to today's code
    code, accs = Codes(rng), []
    for _ in range(rng.randint(2, 4)):
        q = quarter(rng)
        first, last = span(q)
        lines = [[iso(rng.choice([first - D(rng.randint(1, 4)), last - D(rng.randint(0, 3))])), rng.randint(1, 11),
                  rng.randint(100, 1000000)] for _ in range(rng.randint(1, 4))]
        accs.append(account(rng, code, q=q, purchases=lines + [carton(rng, q, False)]))
    return job(rng, accs)


def returns_charge(rng):
    code, accs = Codes(rng), []
    for _ in range(rng.randint(2, 4)):
        q = quarter(rng)
        rs = [[iso(inside(rng, q)), rng.randint(1, 5000), rng.randint(100, 20000)] for _ in range(rng.randint(1, 5))]
        accs.append(account(rng, code, q=q, returns=rs))
    return job(rng, accs)


def returns_edges(rng):
    code, accs = Codes(rng), []
    for _ in range(3):
        q = quarter(rng)
        first, last = span(q)
        rs = [[iso(d), rng.randint(1, 50), rng.randint(100, 5000)] for d in (first - D(1), first, last, last + D(1))]
        accs.append(bare(rng, code, q, purchases=[carton(rng, q, False)], returns=rs))
    return job(rng, accs)


def tier_net(rng):
    code, accs = Codes(rng), []
    t = [{"from": 0, "bp": 100}, {"from": 1000000, "bp": 300}, {"from": 5000000, "bp": 700}]
    for _ in range(rng.randint(2, 4)):
        q = quarter(rng)
        accs.append(bare(rng, code, q, purchases=[[iso(mid(rng, q)), 500, rng.randint(2000, 2400)]],
                         returns=[[iso(mid(rng, q)), rng.randint(260, 300), 1000]]))
    return job(rng, accs, t)


def tier_threshold(rng):
    code, accs = Codes(rng), []
    t = [{"from": 0, "bp": 50}, {"from": 1200000, "bp": 300}, {"from": 3600000, "bp": 900}]
    for lines, rs in (([[1000, 1200]], []), ([[3000, 1200]], []), ([[12, 99999]], []), ([[12, 300001]], []),
                      ([[1000, 1300]], [[1000, 140]])):
        q = quarter(rng)
        accs.append(bare(rng, code, q, purchases=[[iso(mid(rng, q)), u, c] for u, c in lines],
                         returns=[[iso(mid(rng, q)), u, c] for u, c in rs]))
    return job(rng, accs, t)


def net_below_nought(rng):
    code, accs = Codes(rng), []
    for _ in range(3):
        q = quarter(rng)
        accs.append(bare(rng, code, q, prior=rng.choice([0, 1000]),
                         purchases=[[iso(mid(rng, q)), rng.randint(12, 40), 500]],
                         returns=[[iso(mid(rng, q)), rng.randint(50, 200), 900]],
                         notices=[[iso(inside(rng, q)), 900, 500, 100]]))
    return job(rng, accs, [{"from": 0, "bp": 1500}])


def rebate_rounding(rng):
    code, accs = Codes(rng), []
    bp = rng.choice([1, 3, 7, 125, 333, 1499])
    for _ in range(4):
        q = quarter(rng)
        accs.append(bare(rng, code, q, purchases=[[iso(mid(rng, q)), rng.randint(12, 999), rng.randint(101, 9999)]]))
    # exact half cents: 50 bp of 100 x 101 = 50.5 cents; 1 bp of 5,000 cents... net x bp ending in 5,000
    q = quarter(rng)
    accs.append(bare(rng, code, q, purchases=[[iso(mid(rng, q)), 100, 101]]))
    return job(rng, accs, [{"from": 0, "bp": bp}, {"from": 10000, "bp": 50}, {"from": 10200, "bp": bp}])


def growth_increase(rng):
    code, accs = Codes(rng), []
    for _ in range(rng.randint(2, 4)):
        a = account(rng, code, returns=[])
        a["purchases"].append(carton(rng, a["quarter"], False))
        net = model.account(a, [{"from": 0, "bp": 0}])["net"]
        a["prior"] = rng.randint(max(1, net * 100 // 300), net * 100 // 110)
        accs.append(a)
    return job(rng, accs)


def growth_110(rng):
    code, accs = Codes(rng), []
    for prior, units, price in ((100000, 110, 1000), (1000000, 1100, 1000), (100000, 1099, 100), (100000, 25, 4449)):  # last: bonus 224.5 -> 225
        q = quarter(rng)
        accs.append(bare(rng, code, q, prior=prior, purchases=[[iso(mid(rng, q)), units, price]]))
    return job(rng, accs, [{"from": 0, "bp": 100}])


def growth_no_prior(rng):
    code, accs = Codes(rng), []
    for prior in (0, 1, 0):
        q = quarter(rng)
        accs.append(bare(rng, code, q, prior=prior, purchases=[carton(rng, q, False)]))
    return job(rng, accs, [{"from": 0, "bp": 100}])


def price_drop(rng):
    code, accs = Codes(rng), []
    for _ in range(rng.randint(2, 4)):
        q = quarter(rng)
        first, last = span(q)
        ns = [drop(rng, q) for _ in range(rng.randint(1, 4))]
        ns.append([iso(rng.choice([first, last, first - D(1), last + D(1)])), 5000, 1000, rng.randint(100, 50000)])
        accs.append(account(rng, code, q=q, notices=ns))
    return job(rng, accs)


def price_drop_threshold(rng):
    code, accs = Codes(rng), []
    q = quarter(rng)
    accs.append(bare(rng, code, q, notices=[[iso(inside(rng, q)), 1250, 1000, 100]]))          # exactly 25,000
    q = quarter(rng)
    accs.append(bare(rng, code, q, notices=[[iso(inside(rng, q)), 251, 1, 50000]]))
    return job(rng, accs, [{"from": 0, "bp": 0}])


def tidy_ups(rng):  # left to today's code
    code, accs = Codes(rng), []
    for band in ((1, 4999), (5000, 24999), (5000, 24999), (25000, 10**7)):
        q = quarter(rng)
        cut = rng.randint(1, 249)
        lo, hi = max(100, -(-band[0] // cut)), min(50000, band[1] // cut)
        on_hand = rng.randint(lo, hi) if lo <= hi else rng.randint(100, 50000)
        old = rng.randint(cut + 1, 100000)
        accs.append(account(rng, code, q=q, notices=[[iso(inside(rng, q)), old, old - cut, on_hand], drop(rng, q)]))
    q = quarter(rng)
    accs.append(account(rng, code, q=q, notices=[[iso(inside(rng, q)), 300, 51, 100], [iso(inside(rng, q)), 300, 299, 5000],
                                                  [iso(inside(rng, q)), 300, 280, 250], [iso(inside(rng, q)), 300, 299, 100],
                                                  [iso(inside(rng, q)), 300, 251, 102],
                                                  [iso(inside(rng, q)), 2, 1, 100], [iso(inside(rng, q)), 10**6, 999999, 50000]]))   # 24,900; 5,000; 5,000; 100; 4,998
    return job(rng, accs)


def contract_sale(rng):
    code, accs = Codes(rng), []
    for _ in range(rng.randint(2, 4)):
        q = quarter(rng)
        first, last = span(q)
        ss = [contract(rng, q) for _ in range(rng.randint(1, 5))]
        ss.append([iso(rng.choice([first, last, first - D(1), last + D(1)])), 10, 5000, 1000])
        accs.append(account(rng, code, q=q, sales=ss))
    return job(rng, accs)


def contract_threshold(rng):
    code, accs = Codes(rng), []
    q = quarter(rng)
    accs.append(bare(rng, code, q, sales=[[iso(inside(rng, q)), 250, 1100, 1000], [iso(inside(rng, q)), 1, 200, 100]]))
    return job(rng, accs, [{"from": 0, "bp": 0}])


def price_match(rng):  # left to today's code
    code, accs = Codes(rng), []
    for below in (25, 39, rng.randint(26, 38), 24, 1, 99, rng.randint(40, 98)):
        q = quarter(rng)
        cost = rng.randint(max(200, below + 1), 100000)
        accs.append(account(rng, code, q=q, sales=[[iso(inside(rng, q)), rng.randint(1, 5000), cost, cost - below], contract(rng, q)]))
    q = quarter(rng)
    accs.append(bare(rng, code, q, sales=[[iso(inside(rng, q)), 5000, 100, 1], [iso(inside(rng, q)), 5000, 10**6, 999999]]))
    return job(rng, accs)


def minimum_settlement(rng):
    code, accs = Codes(rng), []
    for cents in (500000, 2499900, rng.randint(500000, 2499900), rng.randint(100, 499900)):
        q = quarter(rng)
        accs.append(bare(rng, code, q, purchases=[[iso(mid(rng, q)), 100, cents // 100]]))
    return job(rng, accs, [{"from": 0, "bp": 100}])


def settlement_edge(rng):
    code, accs = Codes(rng), []
    for chargeback in (25000, 24999, 25001):
        q = quarter(rng)
        accs.append(bare(rng, code, q, sales=[[iso(inside(rng, q)), 1, chargeback + 100, 100]]))
    q = quarter(rng)
    accs.append(bare(rng, code, q))   # an empty account settles nought
    return job(rng, accs, [{"from": 0, "bp": 0}])


NAMES = ["A", "Z" * 16, " SP-01 ", 'Q"\\/1', "é-仕入先", "x", "0000000000000001"]


def statement_order(rng):
    code, accs = Codes(rng), []
    for name in NAMES:
        a = account(rng, code)
        a["account"] = name
        accs.append(a)
    return job(rng, accs)


def limits_accounts(rng):
    """Section 1 ends on every field, trap-free."""
    code, accs = Codes(rng), []
    th = sorted(rng.sample(range(1, 10**11), 10)) + [10**11]
    t = [{"from": 0, "bp": 1500}] + [{"from": x, "bp": rng.choice([0, 1500, rng.randint(1, 1499)])} for x in th]
    for q in ("2020-Q1", "2039-Q4", "2024-Q1", "2031-Q3"):
        first, last = span(q)
        accs.append(bare(rng, code, q, prior=rng.choice([10**11, 1]),
                         purchases=[[iso(first - D(45)), 5000, 10**6], [iso(last + D(45)), 12, 100], [iso(mid(rng, q)), 1, 100],
                                    [iso(mid(rng, q)), 5000, 10**6], [iso(first), 12, 10**6]],
                         returns=[[iso(first), 1, 100], [iso(last), 5000, 10**6], [iso(last + D(45)), 5000, 10**6]],
                         notices=[[iso(first), 10**6, 1, 50000], [iso(last), 351, 101, 100], [iso(first - D(45)), 10**6, 1, 50000]],
                         sales=[[iso(last), 5000, 10**6, 1], [iso(first), 1, 200, 100], [iso(last + D(45)), 5000, 10**6, 1]]))
    q = "2027-Q4"
    first, last = span(q)
    accs.append(bare(rng, code, q, prior=10**11, returns=[[iso(rng.choice([first, last])), 5000, 10**6] for _ in range(100)]))
    return job(rng, accs, t)


REPEAT = {"purchases": 400, "returns": 100, "notices": 50, "sales": 200}


def limits_job(rng):
    """One account holding one entry per list at every figure's top; the verifier repeats each entry to the list's
    longest (REPEAT: 400 lines, 100 returns, 50 notices, 200 sales, purchases 2 x 10^12 cents) and the account under
    100 fresh codes."""
    code = Codes(rng)
    q = "2033-Q2"
    first, last = span(q)
    a = bare(rng, code, q, prior=10**11, purchases=[[iso(mid(rng, q)), 5000, 10**6]],
             returns=[[iso(last + D(45)), 5000, 10**6]], notices=[[iso(first), 10**6, 1, 50000]],
             sales=[[iso(last), 5000, 10**6, 1]])
    th = sorted(rng.sample(range(1, 10**11), 10)) + [10**11]
    return job(rng, [a], [{"from": 0, "bp": 7}] + [{"from": x, "bp": 100 * k + 100} for k, x in enumerate(th[:-1])] + [{"from": th[-1], "bp": 1500}])


def expand(job):
    """limits_job as graded: each list entry repeated to the list's longest."""
    a = dict(job["accounts"][0])
    for key, n in REPEAT.items():
        a[key] = a[key] * n
    return dict(job, accounts=[a])


def generated(rng):
    code = Codes(rng)
    return job(rng, [account(rng, code) for _ in range(rng.randint(1, 5))])


FAMILIES = {
    "carton_receipt": (3, carton_receipt), "carton_threshold": (2, carton_threshold), "loose_units": (3, loose_units),
    "returns_charge": (3, returns_charge), "returns_edges": (2, returns_edges), "tier_net": (2, tier_net),
    "tier_threshold": (1, tier_threshold), "net_below_nought": (2, net_below_nought), "rebate_rounding": (3, rebate_rounding),
    "growth_increase": (3, growth_increase), "growth_110": (1, growth_110), "growth_no_prior": (1, growth_no_prior),
    "price_drop": (2, price_drop), "price_drop_threshold": (1, price_drop_threshold), "tidy_ups": (2, tidy_ups),
    "contract_sale": (2, contract_sale), "contract_threshold": (1, contract_threshold), "price_match": (2, price_match),
    "minimum_settlement": (2, minimum_settlement), "settlement_edge": (1, settlement_edge),
    "statement_order": (1, statement_order), "limits_accounts": (1, limits_accounts), "limits_job": (1, limits_job),
    "generated": (4, generated),
}


def families():
    return {name: fam(n, maker) for name, (n, maker) in FAMILIES.items()}


def trap_inputs(job):
    """loose_edge: a line of fewer than 12 units whose invoice day and fourth day after sit on different sides of
    a quarter edge; tidy_up: a notice in the quarter cutting less than 250 cents; price_match: a sale in the
    quarter less than 100 cents below cost."""
    found = set()
    for a in job["accounts"]:
        first, last = span(a["quarter"])
        inq = lambda d: first <= d <= last  # noqa: E731
        for inv, u, _c in a["purchases"]:
            d = model.day(inv)
            if u < CARTON and inq(d) != inq(d + D(4)):
                found.add("loose_edge")
        for e, o, n, _h in a["notices"]:
            if inq(model.day(e)) and o - n < 250:
                found.add("tidy_up")
        for s, _u, c, p in a["sales"]:
            if inq(model.day(s)) and c - p < 100:
                found.add("price_match")
    return found
