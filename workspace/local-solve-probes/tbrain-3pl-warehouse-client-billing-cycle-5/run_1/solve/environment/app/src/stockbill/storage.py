"""Storage weeks, storage and peak stock (billing schedule sections 2.4 and 4)."""

from .dates import ONE_WEEK, parse
from .lots import on_hand
from .rates import rates_for, tier_rate


def billed_weeks(lot, start, end):
    """(number, first day) of each billed week of the lot (2.4)."""
    received = parse(lot["received"])
    number, day = 1, received
    out = []
    while day <= end:
        if day >= start and on_hand(lot, day) > 0:
            out.append((number, day))
        number += 1
        day += ONE_WEEK
    return out


def storage(lot, client, start, end):
    """(billed weeks, storage in cents) for the lot over the period."""
    weeks, total = 0, 0
    for number, first in billed_weeks(lot, start, end):
        rate = tier_rate(number, rates_for(client, first)["storage"])
        weeks += 1
        total += on_hand(lot, first) * rate
    return weeks, total


def peak(lot, start, end):
    """The most pallets the lot held on the first day of a billed week (4.5)."""
    most = 0
    for _number, first in billed_weeks(lot, start, end):
        most = max(most, on_hand(lot, first))
    return most
