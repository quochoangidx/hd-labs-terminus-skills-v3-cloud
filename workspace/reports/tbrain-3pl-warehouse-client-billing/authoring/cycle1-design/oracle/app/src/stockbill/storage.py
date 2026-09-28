"""Storage weeks (billing schedule section 4)."""

from datetime import timedelta

from .dates import parse
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
