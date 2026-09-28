"""Storage weeks (billing schedule section 4)."""

from .dates import ONE_DAY, parse
from .lots import on_hand
from .rates import rates_for, tier_rate


def week_starts(lot, start, end):
    """First days of the lot's storage weeks that fall in the period."""
    day = max(start, parse(lot["received"]))
    out = []
    while day <= end:
        if day.weekday() == 0:
            out.append(day)
        day += ONE_DAY
    return out


def week_number(lot, day):
    """The number of the lot's storage week that `day` falls in."""
    return (day - parse(lot["received"])).days // 7 + 1


def storage(lot, client, start, end):
    """(billed weeks, storage in cents) for the lot over the period."""
    rate = tier_rate(week_number(lot, end), rates_for(client)["storage"])
    weeks, total = 0, 0
    for first in week_starts(lot, start, end):
        pallets = on_hand(lot, first)
        if pallets > 0:
            weeks += 1
            total += pallets * rate
    return weeks, total
