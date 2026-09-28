"""Storage weeks, storage and peak stock (billing schedule sections 2.4 and 4)."""

from datetime import timedelta

from .dates import parse
from .lots import on_hand
from .rates import rates_for, tier_rate

ONE_WEEK = timedelta(days=7)


def billed_weeks(lot, start, end):
    """The lot's billed weeks as (number, first day) pairs (2.4)."""
    received = parse(lot["received"])
    out = []
    number = 1
    day = received
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
        tiers = rates_for(client, first)["storage"]
        weeks += 1
        total += on_hand(lot, first) * tier_rate(number, tiers)
    return weeks, total


def peak(lot, start, end):
    """The most pallets the lot held on the first day of one of its billed weeks (4.5)."""
    most = 0
    for _number, first in billed_weeks(lot, start, end):
        held = on_hand(lot, first)
        if held > most:
            most = held
    return most
