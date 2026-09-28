"""Storage weeks, storage and peak stock (billing schedule sections 2.4 and 4)."""

from datetime import timedelta

from .dates import parse
from .lots import on_hand
from .rates import rates_on, tier_rate

WEEK = timedelta(days=7)


def billed_weeks(lot, start, end):
    """(first day, week number) of each billed week of the lot (2.4)."""
    received = parse(lot["received"])
    if received >= start:
        day, number = received, 1
    else:
        skipped = -(-(start - received).days // 7)
        day, number = received + skipped * WEEK, skipped + 1
    out = []
    while day <= end:
        if on_hand(lot, day) > 0:
            out.append((day, number))
        day += WEEK
        number += 1
    return out


def storage(lot, client, start, end):
    """(billed weeks, storage in cents) for the lot over the period."""
    weeks, total = 0, 0
    for first, number in billed_weeks(lot, start, end):
        weeks += 1
        tiers = rates_on(client, first)["storage"]
        total += on_hand(lot, first) * tier_rate(number, tiers)
    return weeks, total


def peak(lot, start, end):
    """The most pallets the lot held on the first day of one of its billed weeks (4.5)."""
    most = 0
    for first, _number in billed_weeks(lot, start, end):
        most = max(most, on_hand(lot, first))
    return most
