"""Storage weeks, storage and peak stock (billing schedule sections 2.4 and 4)."""

from datetime import timedelta

from .dates import ONE_DAY, parse
from .lots import on_hand
from .rates import rates_for, tier_rate

WEEK = timedelta(days=7)


def week_starts(lot, start, end):
    """First days of the lot's storage weeks (every seventh day from receipt) that fall in the period."""
    day = parse(lot["received"])
    out = []
    while day <= end:
        if day >= start:
            out.append(day)
        day += WEEK
    return out


def week_number(lot, day):
    """The number of the lot's storage week that `day` falls in."""
    return (day - parse(lot["received"])).days // 7 + 1


def storage(lot, client, start, end):
    """(billed weeks, storage in cents) for the lot over the period."""
    weeks, total = 0, 0
    for first in week_starts(lot, start, end):
        pallets = on_hand(lot, first)
        if pallets > 0:
            weeks += 1
            total += pallets * tier_rate(week_number(lot, first), rates_for(client, first)["storage"])
    return weeks, total


def peak(lot, start, end):
    """4.5: the most pallets on hand on the first day of a billed week."""
    billed = [on_hand(lot, first) for first in week_starts(lot, start, end) if on_hand(lot, first) > 0]
    if billed:
        return max(billed)
    # With no billed week 4.5 gives no rule (2.6), so the package's own step stands.
    day = max(start, parse(lot["received"]))
    most = 0
    while day <= end:
        most = max(most, on_hand(lot, day))
        day += ONE_DAY
    return most
