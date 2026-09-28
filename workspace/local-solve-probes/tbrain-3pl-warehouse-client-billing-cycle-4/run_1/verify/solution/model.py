"""Expectation model for tbrain-3pl-warehouse-client-billing, written from billing schedule WB-5.

It reads only the job and the schedule and never imports the package under /app/src. Where the
schedule gives no rule for a value (the instruction's silence clause: pallet counts of nought or
below), the model keeps the step the package took before the repair, applied to the figures the
schedule does define; each such place is marked "Shipped step".
"""

from datetime import date, timedelta

WEEK = timedelta(days=7)


def _d(text):
    return date.fromisoformat(text)


def is_working_day(day, holidays):
    """2.3."""
    return day.weekday() < 5 and day not in holidays


def pallets_on_hand(lot, day):
    """2.2: a dispatch (an entry of one pallet or more, 2.1) takes its pallets away from the day
    after its date."""
    left = lot["pallets"]
    for x in lot["dispatches"]:
        when = _d(x["date"])
        if x["pallets"] >= 1:
            if when < day:
                left -= x["pallets"]
        elif when <= day:
            # Shipped step: the schedule says nothing of an entry below one pallet; the package
            # takes every entry off from its own date on.
            left -= x["pallets"]
    return left

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
    """4.5 (nought with no billed week)."""
    return max((p for _f, _n, p in billed_weeks(lot, start, end)), default=0)


def handling_total(lot, client, holidays, start, end):
    """5.1-5.3: the receipt (an arrival of one pallet or more, 2.1) and the dispatches (entries of one
    pallet or more); an entry below one pallet is not billed (5.3, and the package bills it nothing)."""
    total = 0
    received = _d(lot["received"])
    if start <= received <= end and lot["pallets"] >= 1:
        rates = rates_on(client, received)["handling"]
        total += rates["fee"] + lot["pallets"] * (rates["in"] if is_working_day(received, holidays) else rates["after_hours"])
    for x in lot["dispatches"]:
        day = _d(x["date"])
        if x["pallets"] >= 1 and start <= day <= end:
            rates = rates_on(client, day)["handling"]
            total += x["pallets"] * (rates["out"] if is_working_day(day, holidays) else rates["after_hours"])
    return total


def lot_report(lot, job, holidays, start, end):
    client = job["clients"][lot["client"]]
    weeks = billed_weeks(lot, start, end)
    storage = sum(p * tier_of(n, rates_on(client, f)["storage"]) for f, n, p in weeks)   # 4.1-4.3
    billed = client["minimum"] if weeks and storage < client["minimum"] else storage     # 4.4
    surcharge = (billed * client["surcharge_percent"] + 50) // 100                        # 6.2, 1.3
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

def carries_return_on_a_week_start(job):
    """T1 input: an entry below nought dated on the first day of one of its lot's storage weeks that
    starts within the period (where its timing changes the pallets billed or the peak)."""
    start, end = _d(job["period"]["start"]), _d(job["period"]["end"])
    for lot in job["lots"]:
        received = _d(lot["received"])
        for x in lot["dispatches"]:
            when = _d(x["date"])
            if x["pallets"] < 0 and start <= when <= end and (when - received).days % 7 == 0:
                return True
    return False


def carries_entry_below_nought(job):
    """T1 input class for isolation: any entry below nought, wherever it is dated."""
    return any(x["pallets"] < 0 for lot in job["lots"] for x in lot["dispatches"])


def carries_empty_arrival_in_period(job):
    """T2 input: a lot whose `pallets` is nought, arriving within the period."""
    start, end = _d(job["period"]["start"]), _d(job["period"]["end"])
    return any(lot["pallets"] == 0 and start <= _d(lot["received"]) <= end for lot in job["lots"])


def carries_empty_arrival(job):
    """T2 input class for isolation: any lot whose `pallets` is nought."""
    return any(lot["pallets"] == 0 for lot in job["lots"])


if __name__ == "__main__":
    import json
    import sys

    with open(sys.argv[1], encoding="utf-8") as handle:
        print(json.dumps(report(json.load(handle))))
