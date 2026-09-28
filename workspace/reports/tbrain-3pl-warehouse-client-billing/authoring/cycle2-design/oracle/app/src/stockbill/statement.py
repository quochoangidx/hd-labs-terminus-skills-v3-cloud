"""The period statement (billing schedule sections 4.4, 6 and 7)."""

from .dates import Calendar, parse
from .handling import handling
from .storage import peak, storage


def billed_storage(weeks, stored, minimum):
    """A lot with billed weeks pays at least the client's minimum for storage."""
    if weeks and stored < minimum:
        return minimum
    return stored


def surcharge_on(stored, percent, is_charge):
    """The energy surcharge on a lot's storage, in cents."""
    if is_charge:
        return (stored * percent + 50) // 100
    # A minimum fee is not a storage charge (2.5), so 6.2 gives no rule (2.6): the package's own step stands.
    return stored * percent // 100


def lot_entry(lot, job, calendar, start, end):
    """One lot's statement entry."""
    client = job["clients"][lot["client"]]
    weeks, stored = storage(lot, client, start, end)
    is_charge = bool(weeks) and stored >= client["minimum"]
    stored = billed_storage(weeks, stored, client["minimum"])
    handled = handling(lot, client, calendar, start, end)
    surcharge = surcharge_on(stored, client["surcharge_percent"], is_charge)
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
