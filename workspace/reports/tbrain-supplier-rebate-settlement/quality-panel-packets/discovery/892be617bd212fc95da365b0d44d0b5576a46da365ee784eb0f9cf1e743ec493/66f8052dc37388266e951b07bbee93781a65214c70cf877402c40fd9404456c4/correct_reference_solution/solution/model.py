"""Expectation model for Schedule R (edition R-4), written from the schedule alone.

It never imports the package. Where the schedule reaches no rule, the model mirrors the
statement the shipped package executes for that input and says so ("Shipped step").
"""

import datetime

ONE_DAY = datetime.timedelta(days=1)


def day(text):
    return datetime.date.fromisoformat(text)


def quarter_span(quarter):
    """1.2: first and last day of YYYY-Qn."""
    year, n = int(quarter[:4]), int(quarter[6:])
    first = datetime.date(year, 3 * n - 2, 1)
    nxt = datetime.date(year + 1, 1, 1) if n == 4 else datetime.date(year, 3 * n + 1, 1)
    return first, nxt - ONE_DAY


def share(amount, bp):
    """1.1: bp basis points of a non-negative amount, nearest cent, half up."""
    assert amount >= 0 and bp >= 0
    q, r = divmod(amount * bp, 10000)
    return q + (1 if 2 * r >= 10000 else 0)


CARTON_UNITS = 12      # 2.2
TRANSIT_DAYS = 4       # 2.2
HANDLING = 40          # 3.3
PRICE_DROP_CUT = 250   # 2.4
CONTRACT_GAP = 100     # 2.5
GROWTH_PCT = 110       # 4.1
GROWTH_BP = 200        # 4.1
MINIMUM = 25000        # 6.2

# Shipped figures the schedule does not set for the inputs they decide (reach rule).
SHIPPED_SMALL_CREDIT = 5000      # rebate/rates.py FIGURES["small_credit"] as shipped (use "notice_cutoff")
SHIPPED_HANDLING_PER_UNIT = 25   # rebate/rates.py FIGURES["unit_handling"] as shipped (use "claim_cutoff")


def counting_day(invoiced, units):
    d = day(invoiced)
    if units >= CARTON_UNITS:
        return d + datetime.timedelta(days=TRANSIT_DAYS)    # 2.2, 3.1: received on the fourth day
    return d  # Shipped step: a line that is not a carton shipment counts by the date the export gives it


def tier_rate(amount, tiers):
    """2.6, 3.5."""
    rate = 0
    for row in tiers:
        if amount >= row["from"]:
            rate = row["bp"]
    return rate


def price_credit(old, new, on_hand):
    cut = old - new
    if cut >= PRICE_DROP_CUT:
        return cut * on_hand                                   # 5.1
    credit = cut * on_hand                                     # Shipped step for a notice that is not a price drop
    return 0 if credit < SHIPPED_SMALL_CREDIT else credit


def sale_chargeback(units, cost, price):
    below = cost - price
    if below >= CONTRACT_GAP:
        return below * units                                   # 5.2
    return 0 if below < SHIPPED_HANDLING_PER_UNIT else below * units   # Shipped step for a sale that is not a contract sale


def account(acc, tiers):
    first, last = quarter_span(acc["quarter"])
    inq = lambda d: first <= d <= last  # noqa: E731
    purchases = sum(u * c for inv, u, c in acc["purchases"] if inq(counting_day(inv, u)))
    returns = sum(u * (c - HANDLING) for t, u, c in acc["returns"] if inq(day(t)))
    net = purchases - returns
    bp = tier_rate(net, tiers) if net >= 0 else 0
    rebate = share(net, bp) if net > 0 else 0
    prior = acc["prior"]
    growth = share(net - prior, GROWTH_BP) if prior > 0 and net * 100 >= prior * GROWTH_PCT else 0
    protection = sum(price_credit(o, n, h) for e, o, n, h in acc["notices"] if inq(day(e)))
    charged = sum(sale_chargeback(u, c, p) for s, u, c, p in acc["sales"] if inq(day(s)))
    total = rebate + growth + protection + charged
    paid, carried = (total, 0) if total >= MINIMUM else (0, total)
    return {"account": acc["account"], "purchases": purchases, "returns": returns, "net": net,
            "tier_bp": bp, "rebate": rebate, "growth": growth, "protection": protection,
            "chargebacks": charged, "total": total, "paid": paid, "carried": carried}


def statements(job):
    return {"settlements": [account(a, job["tiers"]) for a in job["accounts"]]}


def within_limits(job):
    """Section 1 limits; returns a list of violations (empty when the job keeps them)."""
    bad = []
    t = job["tiers"]
    if not 1 <= len(t) <= 12 or t[0]["from"] != 0:
        bad.append("tiers")
    for i, r in enumerate(t):
        if not (0 <= r["from"] <= 10**11 and 0 <= r["bp"] <= 1500):
            bad.append("tier row")
        if i and r["from"] <= t[i - 1]["from"]:
            bad.append("tier order")
    accs = job["accounts"]
    if not 1 <= len(accs) <= 100 or len({a["account"] for a in accs}) != len(accs):
        bad.append("accounts")
    for a in accs:
        if not 1 <= len(a["account"]) <= 16:
            bad.append("code")
        if not 2020 <= int(a["quarter"][:4]) <= 2039 or not 0 <= a["prior"] <= 10**11:
            bad.append("quarter/prior")
        first, last = quarter_span(a["quarter"])
        lo, hi = first - datetime.timedelta(days=45), last + datetime.timedelta(days=45)
        win = lambda s: lo <= day(s) <= hi  # noqa: E731
        if len(a["purchases"]) > 400 or len(a["returns"]) > 100 or len(a["notices"]) > 50 or len(a["sales"]) > 200:
            bad.append("counts")
        for d, u, c in a["purchases"] + a["returns"]:
            if not (win(d) and 1 <= u <= 5000 and 100 <= c <= 10**6):
                bad.append("line")
        for d, o, n, h in a["notices"]:
            if not (win(d) and 1 <= n < o <= 10**6 and 100 <= h <= 50000):
                bad.append("notice")
        for d, u, c, p in a["sales"]:
            if not (win(d) and 1 <= u <= 5000 and 100 <= c <= 10**6 and 1 <= p < c):
                bad.append("sale")
    return bad
