"""Storage weeks, storage and peak stock (billing schedule sections 2.4 and 4)."""

from .dates import ONE_DAY, ONE_WEEK, parse
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
    """The first days of the lot's billed weeks (2.4), in order."""
    return [first for first in week_starts(lot, start, end) if on_hand(lot, first) > 0]


def storage(lot, client, start, end):
    """(billed weeks, storage in cents) for the lot over the period."""
    weeks, total = 0, 0
    for first in billed_weeks(lot, start, end):
        tiers = rates_on(client, first)["storage"]
        rate = tier_rate(week_number(lot, first), tiers)
        weeks += 1
        total += on_hand(lot, first) * rate
    return weeks, total


def peak(lot, start, end):
    """The most pallets the lot held on the first day of one of its billed weeks (4.5).

    A lot with no billed weeks has no such figure (2.6); for it the package keeps
    the most pallets it held on any day of the period.
    """
    firsts = billed_weeks(lot, start, end)
    if firsts:
        return max(on_hand(lot, first) for first in firsts)
    day = max(start, parse(lot["received"]))
    most = 0
    while day <= end:
        most = max(most, on_hand(lot, day))
        day += ONE_DAY
    return most
