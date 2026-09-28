"""Storage weeks (billing schedule section 4)."""

from .dates import ONE_WEEK, parse
from .lots import on_hand
from .rates import rates_on, tier_rate


def week_starts(lot, start, end):
    """(week number, first day) of the lot's storage weeks that start in the period.

    A lot's storage weeks run in blocks of seven days from its receipt date (4.1)
    and a week is billed when its first day falls within the period (4.2).
    """
    day = parse(lot["received"])
    number = 1
    while day < start:
        day += ONE_WEEK
        number += 1
    out = []
    while day <= end:
        out.append((number, day))
        day += ONE_WEEK
        number += 1
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
            tiers = rates_on(client, first)["storage"]
            weeks += 1
            total += pallets * tier_rate(number, tiers)
    return weeks, total
