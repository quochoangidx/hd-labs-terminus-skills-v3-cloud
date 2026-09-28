"""Expectation model for tbrain-3pl-warehouse-client-billing, written from billing schedule WB-5.

It reads only the job and the schedule and never imports the package under /app/src. Where the
schedule gives no rule for a value (2.6 for 4.5 and 6.2, through the instruction's silence clause), the model
keeps the step the package took before the repair, applied to the figures the schedule does define;
each such place is marked "Shipped step".
"""

from datetime import date, timedelta

WEEK = timedelta(days=7)


def _d(text):
    return date.fromisoformat(text)


def is_working_day(day, holidays):
    """2.3."""
    return day.weekday() < 5 and day not in holidays


def pallets_on_hand(lot, day):
    """2.2: received less those dispatched on earlier days."""
    return lot["pallets"] - sum(x["pallets"] for x in lot["dispatches"] if _d(x["date"]) < day)


def revision_in_force(revisions, day):
    """3.1: the latest revision effective on or before the day (1.4 guarantees one)."""
    found = None
    for rev in revisions:
        if _d(rev["effective"]) <= day:
            found = rev
    return found


def rates_on(client, day):
    """3.2."""
    return revision_in_force(client["revisions"], day)["rates"]


def tier_of(number, tiers):
    """4.2: the rate of the tier that takes week `number`."""
    first = 1
    for length, rate in tiers:
        if length is None or number < first + length:
            return rate
        first += length
    raise AssertionError("the last tier has no length")


def billed_weeks(lot, start, end):
    """2.4: (first day, number, pallets) of each billed week."""
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


def peak(lot, start, end):
    """4.5."""
    weeks = billed_weeks(lot, start, end)
    if weeks:
        return max(p for _f, _n, p in weeks)
    # Shipped step: with no billed week 4.5 takes the largest of figures the lot has none of, so
    # it gives no rule (2.6); the package takes the most pallets on hand on any day of the period
    # from the receipt (or the period start) on.
    day, most = max(start, _d(lot["received"])), 0
    while day <= end:
        most = max(most, pallets_on_hand(lot, day))
        day += timedelta(days=1)
    return most


def handling_total(lot, client, holidays, start, end):
    """5.1-5.3."""
    moves = [(_d(lot["received"]), lot["pallets"], "in")]
    moves += [(_d(x["date"]), x["pallets"], "out") for x in lot["dispatches"]]
    total = 0
    for day, pallets, kind in moves:
        if start <= day <= end:
            rates = rates_on(client, day)["handling"]
            rate = rates[kind] if is_working_day(day, holidays) else rates["after_hours"]
            total += pallets * rate
    return total


def lot_report(lot, job, holidays, start, end):
    client = job["clients"][lot["client"]]
    weeks = billed_weeks(lot, start, end)
    storage = sum(p * tier_of(n, rates_on(client, f)["storage"]) for f, n, p in weeks)   # 4.1-4.3
    is_charge = bool(weeks) and storage >= client["minimum"]                              # 2.5
    billed = client["minimum"] if weeks and storage < client["minimum"] else storage     # 4.4
    pct = client["surcharge_percent"]
    if is_charge:
        surcharge = (billed * pct + 50) // 100                                            # 6.2, 1.3
    else:
        # Shipped step: a minimum fee (or no storage at all) is not a storage charge (2.5), so 6.2
        # gives no rule (2.6); the package takes the percentage of the billed storage, truncated.
        surcharge = billed * pct // 100
    handled = handling_total(lot, client, holidays, start, end)
    return {"id": lot["id"], "client": lot["client"], "storage_weeks": len(weeks), "peak": peak(lot, start, end),
            "storage": billed, "handling": handled, "surcharge": surcharge, "amount": billed + handled + surcharge}


def report(job):
    """The statement billing schedule WB-5 gives for the job (section 7)."""
    holidays = {_d(x) for x in job.get("holidays", [])}
    start, end = _d(job["period"]["start"]), _d(job["period"]["end"])
    rows = [lot_report(lot, job, holidays, start, end) for lot in job["lots"]]
    return {"statement": job["statement"], "lots": rows, "total": sum(r["amount"] for r in rows)}


# ---- trap-input predicates, used by the authoring scorer and generators ----

def carries_minimum_fee_surcharge(job):
    """T1 input: a lot billed a minimum fee whose client's surcharge and minimum are above nought."""
    start, end = _d(job["period"]["start"]), _d(job["period"]["end"])
    for lot in job["lots"]:
        client = job["clients"][lot["client"]]
        weeks = billed_weeks(lot, start, end)
        storage = sum(p * tier_of(n, rates_on(client, f)["storage"]) for f, n, p in weeks)
        if weeks and storage < client["minimum"] and client["surcharge_percent"] > 0:
            return True
    return False


def carries_lot_without_billed_week(job):
    """T2 input: a lot with no billed week in the period."""
    start, end = _d(job["period"]["start"]), _d(job["period"]["end"])
    return any(not billed_weeks(lot, start, end) for lot in job["lots"])


if __name__ == "__main__":
    import json
    import sys

    with open(sys.argv[1], encoding="utf-8") as handle:
        print(json.dumps(report(json.load(handle))))
