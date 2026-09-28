"""The statutory rate table and the weekly compensation rate."""

from .dates import parse_day
from .money import ratio_of

# Share of the average weekly wage paid as the weekly rate.
RATE_FRACTION = (2, 3)


def load_table(rows):
    """Rate-table rows as (effective day, maximum cents, minimum cents), in table order."""
    return [(parse_day(row["from"]), row["max"], row["min"]) for row in rows]


def row_in_force(table, day):
    """The row in force on `day`: the last row taking effect on or before it."""
    chosen = table[0]
    for row in table:
        if row[0] <= day:
            chosen = row
    return chosen


def weekly_rate(aww, table, injury):
    """The weekly compensation rate in cents for an average weekly wage `aww`."""
    _effective, maximum, minimum = row_in_force(table, injury)
    if aww < minimum:
        return aww
    rate = ratio_of(aww, RATE_FRACTION)
    if rate > maximum:
        rate = maximum
    if rate < minimum:
        rate = minimum
    return rate
