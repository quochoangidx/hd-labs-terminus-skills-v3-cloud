"""Storage weeks, storage and peak stock (billing schedule sections 2.4 and 4)."""

from .dates import ONE_WEEK, parse
from .lots import on_hand
from .rates import rates_on, tier_rate


def week_starts(lot, start, end):
    """(number, first day) of the lot's storage weeks that start within the period (2.4).

    A lot's storage weeks run in blocks of seven days from its receipt date.
    """
    received = parse(lot["received"])
    number = 1
    day = received
    if start > received:
        skipped = ((start - received).days + 6) // 7
        number += skipped
        day += ONE_WEEK * skipped
    out = []
    while day <= end:
        out.append((number, day))
        number += 1
        day += ONE_WEEK
    return out


def billed_weeks(lot, start, end):
    """(number, first day, pallets on hand) of the lot's billed weeks (2.4)."""
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
        tiers = rates_on(client, first)["storage"]
        weeks += 1
        total += pallets * tier_rate(number, tiers)
    return weeks, total


def peak(lot, start, end):
    """The most pallets the lot held on the first day of one of its billed weeks (4.5)."""
    most = 0
    for _number, _first, pallets in billed_weeks(lot, start, end):
        most = max(most, pallets)
    return most
