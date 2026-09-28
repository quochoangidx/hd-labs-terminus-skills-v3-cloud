"""Storage weeks, storage and peak stock (billing schedule sections 2.4 and 4)."""

from .dates import ONE_DAY, parse
from .lots import on_hand
from .rates import rates_for, tier_rate


def week_starts(lot, start, end):
    """(number, first day) of the lot's storage weeks starting within the period (2.4)."""
    received = parse(lot["received"])
    out = []
    number = 1
    day = received
    while day <= end:
        if day >= start:
            out.append((number, day))
        number += 1
        day = received + ONE_DAY * (7 * (number - 1))
    return out


def billed_weeks(lot, start, end):
    """The lot's billed weeks as (number, first day) pairs (2.4)."""
    return [(number, first) for number, first in week_starts(lot, start, end) if on_hand(lot, first) > 0]


def week_number(lot, day):
    """The number of the lot's storage week that `day` falls in."""
    return (day - parse(lot["received"])).days // 7 + 1


def storage(lot, client, start, end):
    """(billed weeks, storage in cents) for the lot over the period (4.1 to 4.3)."""
    weeks, total = 0, 0
    for number, first in billed_weeks(lot, start, end):
        pallets = on_hand(lot, first)
        rate = tier_rate(number, rates_for(client, first)["storage"])
        weeks += 1
        total += pallets * rate
    return weeks, total


def peak(lot, start, end):
    """The most pallets the lot held on the first day of one of its billed weeks (4.5).

    A lot with no billed weeks has no such figure (2.6): the package keeps the
    figure it worked out for it before, the most it held on a day of the period.
    """
    firsts = billed_weeks(lot, start, end)
    if firsts:
        return max(on_hand(lot, first) for _number, first in firsts)
    day = max(start, parse(lot["received"]))
    most = 0
    while day <= end:
        most = max(most, on_hand(lot, day))
        day += ONE_DAY
    return most
