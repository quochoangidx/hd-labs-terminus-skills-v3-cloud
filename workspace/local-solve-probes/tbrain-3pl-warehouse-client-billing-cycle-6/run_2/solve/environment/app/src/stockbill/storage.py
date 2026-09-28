"""Storage weeks, storage and peak stock (billing schedule sections 2.4 and 4)."""

from datetime import timedelta

from .dates import parse
from .lots import on_hand
from .rates import rates_on, tier_rate

ONE_WEEK = timedelta(days=7)


def week_starts(lot, start, end):
    """(number, first day) of the lot's storage weeks starting within the period (2.4)."""
    day = parse(lot["received"])
    number = 1
    out = []
    while day <= end:
        if day >= start:
            out.append((number, day))
        day += ONE_WEEK
        number += 1
    return out


def billed_weeks(lot, start, end):
    """(number, first day, pallets on hand) of the lot's billed weeks (2.4, 4.1)."""
    out = []
    for number, first in week_starts(lot, start, end):
        pallets = on_hand(lot, first)
        if pallets > 0:
            out.append((number, first, pallets))
    return out


def storage(lot, client, start, end):
    """(billed weeks, storage in cents) for the lot over the period (4.1 to 4.3)."""
    weeks, total = 0, 0
    for number, first, pallets in billed_weeks(lot, start, end):
        rate = tier_rate(number, rates_on(client, first)["storage"])
        weeks += 1
        total += pallets * rate
    return weeks, total


def peak(lot, start, end):
    """The most pallets the lot held on the first day of one of its billed weeks (4.5)."""
    counts = [pallets for _, _, pallets in billed_weeks(lot, start, end)]
    return max(counts) if counts else 0
