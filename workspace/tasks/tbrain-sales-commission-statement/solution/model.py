"""Expectation model for the Field Sales Compensation Plan (issue 6), written from the plan alone.

It never imports the package. Where no rule of the plan reaches a figure, the model mirrors the
statement the shipped package executes for that input and says so ("Shipped step").
"""

import datetime

ONE_DAY = datetime.timedelta(days=1)

REVERSAL_CENTS = 50000     # 2.3
NEW_LOGO_CENTS = 250000    # 2.4
BAND_BP = (800, 1200, 1600)  # 4.1
REVERSAL_AGE = 120         # 5.1
CLAWBACK_BP = 800          # 5.1
BONUS_BP = 300             # 6.1
MINIMUM_PAYMENT = 25000    # 7.4

# Shipped figures the plan does not set for the inputs they decide (reach rule of the instruction).
SHIPPED_WINDOW_DAYS = 90       # commission/figures.py FIGURES["window_days"] (use "clawback_age")
SHIPPED_CLAWBACK_BP = 800      # commission/figures.py FIGURES["base_bp"] (use "clawback_rate")
SHIPPED_SMALL_CENTS = 10000    # commission/figures.py FIGURES["small_cents"] (use "bonus_floor")
SHIPPED_BONUS_BP = 300         # commission/figures.py FIGURES["logo_bp"] (use "bonus_rate")


def day(text):
    return datetime.date.fromisoformat(text)


def quarter_span(quarter):
    """1.2: first and last day of YYYY-Qn."""
    year, n = int(quarter[:4]), int(quarter[6:])
    first = datetime.date(year, 3 * n - 2, 1)
    nxt = datetime.date(year + 1, 1, 1) if n == 4 else datetime.date(year, 3 * n + 1, 1)
    return first, nxt - ONE_DAY


def in_span(text, quarter):
    first, last = quarter_span(quarter)
    return first <= day(text) <= last


def share(amount, bp):
    """1.1: bp basis points of a non-negative amount, to the nearest cent, half up."""
    assert amount >= 0 and bp >= 0
    q, r = divmod(amount * bp, 10000)
    return q + (1 if 2 * r >= 10000 else 0)


def rep_share(amount, split):
    """2.2 with 1.1: the rep's split, in per cent, of an amount."""
    return share(amount, 100 * split)


def commission(bookings, quota):
    """4.1, 4.2: three marginal bands, each rounded on its own."""
    low = min(bookings, quota)
    mid = min(max(bookings - quota, 0), quota)
    top = max(bookings - 2 * quota, 0)
    return share(low, BAND_BP[0]) + share(mid, BAND_BP[1]) + share(top, BAND_BP[2])


def clawback_line(raised, booked, amount, split):
    """5.1, 5.2: the line a credit note raised in the quarter carries."""
    age = (day(raised) - day(booked)).days          # 2.5
    if amount >= REVERSAL_CENTS:                    # 2.3: a reversal
        return rep_share_line(amount, split, CLAWBACK_BP) if age <= REVERSAL_AGE else 0
    # Shipped step: a credit note that is not a reversal is priced by no rule; clawback.py
    # takes the base rate of the rep's share when the age is within the shipped window.
    if age > SHIPPED_WINDOW_DAYS:
        return 0
    return rep_share_line(amount, split, SHIPPED_CLAWBACK_BP)


def rep_share_line(amount, split, bp):
    return share(rep_share(amount, split), bp)


def bonus_line(value, split):
    """6.1, 6.2: the line a first order counting toward the quarter carries."""
    credit = rep_share(value, split)
    if value >= NEW_LOGO_CENTS:                     # 2.4: a new-logo order
        return share(credit, BONUS_BP)
    # Shipped step: a first order that is not a new-logo order is priced by no rule; bonus.py
    # pays the bonus rate on the rep's share when that share reaches the shipped floor.
    if credit < SHIPPED_SMALL_CENTS:
        return 0
    return share(credit, SHIPPED_BONUS_BP)


def payment(total, draw, owed):
    """7.2 to 7.4: (recovered, owed, paid, carried)."""
    if total < draw:
        return 0, owed + draw - total, draw, 0
    recovered = min(owed, total - draw)
    due = total - recovered
    owed -= recovered
    if draw > 0:
        return recovered, owed, due, 0
    if due >= MINIMUM_PAYMENT:
        return recovered, owed, due, 0
    return recovered, owed, 0, due


def statement(rep):
    quarter = rep["quarter"]
    counted = [o for o in rep["orders"] if in_span(o[0], quarter)]            # 3.1
    booked = sum(rep_share(value, split) for _d, value, split, _f in counted)  # 3.2
    earned = commission(booked, rep["quota"])
    bonus = sum(bonus_line(value, split) for _d, value, split, first in counted if first)
    raised = [c for c in rep["credits"] if in_span(c[0], quarter)]
    taken = sum(clawback_line(*c) for c in raised)
    total = earned + bonus + rep["carried"] - taken                          # 7.1
    recovered, owed, paid, carried = payment(total, rep["draw"], rep["owed"])
    return {
        "rep": rep["rep"],
        "bookings": booked,
        "commission": earned,
        "bonus": bonus,
        "clawback": taken,
        "total": total,
        "recovered": recovered,
        "owed": owed,
        "paid": paid,
        "carried": carried,
    }


def statements(job):
    return {"statements": [statement(rep) for rep in job["reps"]]}


def _is_int(x):
    return type(x) is int


def limit_problems(job):
    """Every way the job leaves the limits of plan section 1 and the README (empty when inside)."""
    bad = []
    reps = job.get("reps")
    if not isinstance(reps, list) or not 1 <= len(reps) <= 60:
        return ["reps count"]
    codes = [r.get("rep") for r in reps]
    if len(set(codes)) != len(codes):
        bad.append("duplicate rep code")
    for r in reps:
        code = r["rep"]
        if not isinstance(code, str) or not 1 <= len(code) <= 16:
            bad.append(f"{code!r}: code")
        q = r["quarter"]
        if not (len(q) == 7 and q[4:6] == "-Q" and 2020 <= int(q[:4]) <= 2039 and q[6] in "1234"):
            bad.append(f"{code}: quarter")
            continue
        for key, lo, hi in (("quota", 100000, 10**10), ("draw", 0, 10**7), ("owed", 0, 10**8), ("carried", 0, 24999)):
            if not _is_int(r[key]) or not lo <= r[key] <= hi:
                bad.append(f"{code}: {key}")
        first, last = quarter_span(q)
        lo_day, hi_day = first - 45 * ONE_DAY, last + 45 * ONE_DAY
        if len(r["orders"]) > 300 or len(r["credits"]) > 100:
            bad.append(f"{code}: list length")
        for booked, value, split, is_first in r["orders"]:
            if not lo_day <= day(booked) <= hi_day:
                bad.append(f"{code}: order day")
            if not (_is_int(value) and 100 <= value <= 10**9 and _is_int(split) and 1 <= split <= 100):
                bad.append(f"{code}: order figures")
            if type(is_first) is not bool:
                bad.append(f"{code}: first flag")
        for raised, booked, amount, split in r["credits"]:
            if not lo_day <= day(raised) <= hi_day:
                bad.append(f"{code}: credit day")
            if not 0 <= (day(raised) - day(booked)).days <= 365:
                bad.append(f"{code}: credit age")
            if not (_is_int(amount) and 100 <= amount <= 10**9 and _is_int(split) and 1 <= split <= 100):
                bad.append(f"{code}: credit figures")
    return bad


if __name__ == "__main__":
    import json
    import sys

    with open(sys.argv[1], encoding="utf-8") as handle:
        print(json.dumps(statements(json.load(handle))))
