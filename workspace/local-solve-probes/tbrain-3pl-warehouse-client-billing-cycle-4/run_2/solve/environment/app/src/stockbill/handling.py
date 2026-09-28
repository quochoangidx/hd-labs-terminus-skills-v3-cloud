"""Handling of receipts and dispatches (billing schedule section 5)."""

from .dates import parse
from .lots import dispatches
from .rates import rates_on


def movement_rate(handling, day, calendar, kind):
    """The per-pallet rate for a movement of `kind` ("in" or "out") on `day` (5.2)."""
    if calendar.is_out_of_hours(day):
        return handling["after_hours"]
    return handling[kind]


def handling(lot, client, calendar, start, end):
    """The lot's handling over the period, in cents."""
    total = 0
    received = parse(lot["received"])
    if lot["pallets"] >= 1 and start <= received <= end:
        rates = rates_on(client, received)["handling"]
        total += rates["fee"]
        total += lot["pallets"] * movement_rate(rates, received, calendar, "in")
    for when, pallets in dispatches(lot):
        if pallets < 1:
            continue  # nothing leaves the warehouse on this entry
        if start <= when <= end:
            rates = rates_on(client, when)["handling"]
            total += pallets * movement_rate(rates, when, calendar, "out")
    return total
