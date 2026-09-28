"""Storage weeks, storage and peak stock (billing schedule sections 2.4 and 4)."""

from .dates import ONE_WEEK, parse
from .lots import on_hand
from .rates import rates_on, tier_rate


def week_starts(lot, start, end):
    """First days of the lot's storage weeks that start within the period (2.4)."""
    day = parse(lot["received"])
    out = []
    while day <= end:
        if day >= start:
            out.append(day)
        day += ONE_WEEK
    return out


def week_number(lot, day):
    """The number of the lot's storage week that `day` falls in."""
    return (day - parse(lot["received"])).days // 7 + 1


def billed_weeks(lot, start, end):
    """(first day, pallets on hand) of each billed week of the lot (2.4, 4.1)."""
    out = []
    for first in week_starts(lot, start, end):
        pallets = on_hand(lot, first)
        if pallets > 0:
            out.append((first, pallets))
    return out


def storage(lot, client, start, end):
    """(billed weeks, storage in cents) for the lot over the period."""
    weeks, total = 0, 0
    for first, pallets in billed_weeks(lot, start, end):
        tiers = rates_on(client, first)["storage"]
        weeks += 1
        total += pallets * tier_rate(week_number(lot, first), tiers)
    return weeks, total


def peak(lot, start, end):
    """The most pallets the lot held on the first day of one of its billed weeks (4.5)."""
    most = 0
    for _first, pallets in billed_weeks(lot, start, end):
        if pallets > most:
            most = pallets
    return most
