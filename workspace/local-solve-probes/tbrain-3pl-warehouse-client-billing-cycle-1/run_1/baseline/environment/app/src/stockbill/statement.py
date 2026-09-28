"""The period statement (billing schedule sections 6 and 7)."""

from .dates import Calendar, parse
from .handling import handling
from .lots import is_closed
from .storage import storage


def discount_on(amount, percent):
    """The client discount on a lot's amount, in cents."""
    return amount * percent // 100


def lot_entry(lot, job, calendar, start, end):
    """One lot's statement entry."""
    client = job["clients"][lot["client"]]
    weeks, stored = storage(lot, client, start, end)
    handled = handling(lot, client, calendar, start, end)
    amount = stored + handled
    discount = discount_on(amount, client["discount_percent"])
    return {
        "id": lot["id"],
        "client": lot["client"],
        "status": "closed" if is_closed(lot) else "open",
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
