"""Storage weeks (billing schedule section 4)."""

from datetime import timedelta

from .dates import parse
from .lots import on_hand
from .rates import rates_for, tier_rate

ONE_WEEK = timedelta(days=7)


def week_starts(lot, start, end):
    """(number, first day) of the lot's storage weeks that start within the period.

    The weeks run in blocks of seven days from the receipt date (4.1); the ones
    whose first day falls between the period's start and end dates, both
    included, are the candidates for billing (4.2).
    """
    received = parse(lot["received"])
    out = []
    number, day = 1, received
    if start > received:
        skipped = (start - received).days // 7
        number, day = number + skipped, day + skipped * ONE_WEEK
        if day < start:
            number, day = number + 1, day + ONE_WEEK
    while day <= end:
        out.append((number, day))
        number, day = number + 1, day + ONE_WEEK
    return out


def week_number(lot, day):
    """The number of the lot's storage week that `day` falls in."""
    return (day - parse(lot["received"])).days // 7 + 1


def storage(lot, client, start, end):
    """(billed weeks, storage in cents) for the lot over the period."""
    weeks, total = 0, 0
    for number, first in week_starts(lot, start, end):
        pallets = on_hand(lot, first)
        if pallets > 0:
            rate = tier_rate(number, rates_for(client, first)["storage"])
            weeks += 1
            total += pallets * rate
    return weeks, total
