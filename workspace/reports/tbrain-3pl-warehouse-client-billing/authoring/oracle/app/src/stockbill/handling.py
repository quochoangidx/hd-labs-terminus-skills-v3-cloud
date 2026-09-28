"""Handling of receipts and dispatches (billing schedule section 5)."""

from .dates import parse
from .lots import dispatches
from .rates import rates_for


def movement_rate(handling, day, calendar, kind):
    """The per-pallet rate for a movement of `kind` ("in" or "out") on `day`."""
    if calendar.is_out_of_hours(day):
        return handling["after_hours"]
    return handling[kind]


def handling(lot, client, calendar, start, end):
    """The lot's handling over the period, in cents."""
    total = 0
    received = parse(lot["received"])
    if start <= received <= end and lot["pallets"] >= 1:  # a receipt is an arrival of one pallet or more (2.1)
        rates = rates_for(client, received)["handling"]
        total += rates["fee"] + lot["pallets"] * movement_rate(rates, received, calendar, "in")
    for when, pallets in dispatches(lot):
        if pallets < 1:
            continue  # nothing leaves the warehouse on this entry
        if start <= when <= end:
            total += pallets * movement_rate(rates_for(client, when)["handling"], when, calendar, "out")
    return total
