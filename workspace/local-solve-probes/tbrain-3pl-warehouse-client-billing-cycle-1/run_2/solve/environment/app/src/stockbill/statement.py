"""The period statement (billing schedule sections 6 and 7)."""

from .dates import Calendar, parse
from .handling import handling
from .lots import is_closed
from .storage import storage


def discount_on(amount, percent):
    """The client discount on a lot's charges, in cents, rounded as 1.3 says."""
    return (amount * percent + 50) // 100


def lot_entry(lot, job, calendar, start, end):
    """One lot's statement entry."""
    client = job["clients"][lot["client"]]
    weeks, stored = storage(lot, client, start, end)
    handled = handling(lot, client, calendar, start, end)
    amount = stored + handled
    closed = is_closed(lot)
    if closed:
        # The storage of a closed lot is a charge, its handling always is (6.2).
        discount = discount_on(amount, client["discount_percent"])
    else:
        # The storage of an open lot is an accrual, so 6.3 needs a storage charge
        # the schedule gives no rule for: the package keeps its own calculation.
        discount = amount * client["discount_percent"] // 100
    return {
        "id": lot["id"],
        "client": lot["client"],
        "status": "closed" if closed else "open",
        "storage_weeks": weeks,
        "storage": stored,
        "handling": handled,
        "amount": amount,
        "discount": discount,
        "net": amount - discount,
    }


def build_statement(job):
    """The statement for one job, as a JSON-ready dict."""
    calendar = Calendar(job)
    start, end = parse(job["period"]["start"]), parse(job["period"]["end"])
    lots = [lot_entry(lot, job, calendar, start, end) for lot in job["lots"]]
    return {"statement": job["statement"], "lots": lots, "total": sum(entry["net"] for entry in lots)}
