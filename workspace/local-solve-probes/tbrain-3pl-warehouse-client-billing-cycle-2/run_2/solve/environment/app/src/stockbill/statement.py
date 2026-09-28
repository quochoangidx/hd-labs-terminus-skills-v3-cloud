"""The period statement (billing schedule sections 4.4, 6 and 7)."""

from .dates import Calendar, parse
from .handling import handling
from .storage import peak, storage


def billed_storage(weeks, stored, minimum):
    """A lot with billed weeks pays at least the client's minimum for storage (4.4)."""
    if weeks and stored < minimum:
        return minimum
    return stored


def has_storage_charge(weeks, stored, minimum):
    """Whether the lot's billed storage is a storage charge (2.5), not a minimum fee."""
    return bool(weeks) and stored >= minimum


def surcharge_on_charge(charge, percent):
    """The energy surcharge on a lot's storage charge (6.2), rounded as 1.3 says."""
    return (charge * percent + 50) // 100


def surcharge_on(stored, percent):
    """The surcharge the package works out where 6.2 gives no rule (2.6)."""
    return stored * percent // 100


def lot_entry(lot, job, calendar, start, end):
    """One lot's statement entry."""
    client = job["clients"][lot["client"]]
    minimum = client["minimum"]
    percent = client["surcharge_percent"]
    weeks, stored = storage(lot, client, start, end)
    charged = has_storage_charge(weeks, stored, minimum)
    stored = billed_storage(weeks, stored, minimum)
    handled = handling(lot, client, calendar, start, end)
    if charged:
        surcharge = surcharge_on_charge(stored, percent)
    else:
        surcharge = surcharge_on(stored, percent)
    return {
        "id": lot["id"],
        "client": lot["client"],
        "storage_weeks": weeks,
        "peak": peak(lot, start, end),
        "storage": stored,
        "handling": handled,
        "surcharge": surcharge,
        "amount": stored + handled + surcharge,
    }


def build_statement(job):
    """The statement for one job, as a JSON-ready dict."""
    calendar = Calendar(job)
    start, end = parse(job["period"]["start"]), parse(job["period"]["end"])
    lots = [lot_entry(lot, job, calendar, start, end) for lot in job["lots"]]
    return {"statement": job["statement"], "lots": lots, "total": sum(entry["amount"] for entry in lots)}
