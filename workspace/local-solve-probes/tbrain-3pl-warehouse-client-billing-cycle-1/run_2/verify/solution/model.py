"""Expectation model for tbrain-3pl-warehouse-client-billing, written from billing schedule WB-5.

It reads only the job and the schedule and never imports the package under /app/src. Where the
schedule gives no rule for a value (3.1 and 6.2, through the instruction's silence clause), the model
keeps the step the package took before the repair, applied to the figures the schedule does define;
each such place is marked "Shipped step".
"""

from datetime import date, timedelta

WEEK = timedelta(days=7)


def _d(text):
    return date.fromisoformat(text)


def is_working_day(day, holidays):
    """2.4."""
    return day.weekday() < 5 and day not in holidays


def pallets_on_hand(lot, day):
    """2.2: received less those dispatched on earlier days."""
    return lot["pallets"] - sum(x["pallets"] for x in lot["dispatches"] if _d(x["date"]) < day)


def closed(lot):
    """2.3."""
    return sum(x["pallets"] for x in lot["dispatches"]) == lot["pallets"]


def revision_in_force(revisions, day):
    """3.1: the latest revision effective on or before the day, or None before the earliest."""
    found = None
    for rev in revisions:
        if _d(rev["effective"]) <= day:
            found = rev
    return found


def rates_on(client, day):
    """3.2."""
    rev = revision_in_force(client["revisions"], day)
    if rev is None:
        # Shipped step: 3.1 gives no rule for the rates on a day before the client's earliest
        # effective date; the package bills on the last revision of the rate card.
        rev = client["revisions"][-1]
    return rev["rates"]


def tier_of(number, tiers):
    """4.3: the rate of the tier that takes week `number`."""
    first = 1
    for length, rate in tiers:
        if length is None or number < first + length:
            return rate
        first += length
    raise AssertionError("the last tier has no length")


def billed_weeks(lot, start, end):
    """4.1-4.2: (first day, number, pallets) of each billed week."""
    out = []
    first, number = _d(lot["received"]), 1
    while first <= end:
        if first >= start:
            pallets = pallets_on_hand(lot, first)
            if pallets > 0:
                out.append((first, number, pallets))
        first += WEEK
        number += 1
    return out


def storage_total(lot, client, start, end):
    weeks = billed_weeks(lot, start, end)
    total = sum(p * tier_of(n, rates_on(client, f)["storage"]) for f, n, p in weeks)
    return len(weeks), total


def handling_total(lot, client, holidays, start, end):
    """5.1-5.2."""
    moves = [(_d(lot["received"]), lot["pallets"], "in")]
    moves += [(_d(x["date"]), x["pallets"], "out") for x in lot["dispatches"]]
    total = 0
    for day, pallets, kind in moves:
        if start <= day <= end:
            rates = rates_on(client, day)["handling"]
            rate = rates[kind] if is_working_day(day, holidays) else rates["after_hours"]
            total += pallets * rate
    return total


def discount(amount, handling, percent, is_closed):
    """6.3 with 1.3 (amounts are never below nought)."""
    if is_closed:
        return (amount * percent + 50) // 100
    # Shipped step: 6.2 gives no rule for the discount of an open lot (6.3 needs its storage
    # charge, and an open lot's storage is an accrual); the package takes the percentage of the
    # lot's amount, truncated.
    return amount * percent // 100


def lot_report(lot, job, holidays, start, end):
    client = job["clients"][lot["client"]]
    weeks, stored = storage_total(lot, client, start, end)
    handled = handling_total(lot, client, holidays, start, end)
    amount = stored + handled
    is_closed = closed(lot)
    disc = discount(amount, handled, client["discount_percent"], is_closed)
    return {"id": lot["id"], "client": lot["client"], "status": "closed" if is_closed else "open",
            "storage_weeks": weeks, "storage": stored, "handling": handled, "amount": amount,
            "discount": disc, "net": amount - disc}


def report(job):
    """The statement billing schedule WB-5 gives for the job (section 7)."""
    holidays = {_d(x) for x in job.get("holidays", [])}
    start, end = _d(job["period"]["start"]), _d(job["period"]["end"])
    rows = [lot_report(lot, job, holidays, start, end) for lot in job["lots"]]
    return {"statement": job["statement"], "lots": rows, "total": sum(r["net"] for r in rows)}


# ---- trap-input predicates, used by the authoring scorer and generators ----

def carries_open_lot_discount(job):
    """T1 input: an open lot with a discount above nought and an amount above nought."""
    for row in report(job)["lots"]:
        pct = job["clients"][row["client"]]["discount_percent"]
        if row["status"] == "open" and pct > 0 and row["amount"] > 0:
            return True
    return False


def carries_pre_card_date(job):
    """T2 input: a billed week or a movement in the period dated before its client's earliest effective date."""
    start, end = _d(job["period"]["start"]), _d(job["period"]["end"])
    for lot in job["lots"]:
        earliest = _d(job["clients"][lot["client"]]["revisions"][0]["effective"])
        days = [f for f, _n, _p in billed_weeks(lot, start, end)]
        days += [d for d in [_d(lot["received"])] + [_d(x["date"]) for x in lot["dispatches"]] if start <= d <= end]
        if any(d < earliest for d in days):
            return True
    return False


if __name__ == "__main__":
    import json
    import sys

    with open(sys.argv[1], encoding="utf-8") as handle:
        print(json.dumps(report(json.load(handle))))
