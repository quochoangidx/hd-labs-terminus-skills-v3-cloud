"""Index date, the measure's denominator test and the span the PDC is taken over."""

from .days import month_day, year_end

INDEX_LAST_MONTH = 10
INDEX_LAST_DAY = 2


def index_date(fills):
    return min(fill.date for fill in fills)


def in_measure(fills, year):
    """Whether the member counts in the measure for the class."""
    dates = {fill.date for fill in fills}
    return len(dates) >= 2 and index_date(fills) <= month_day(year, INDEX_LAST_MONTH, INDEX_LAST_DAY)


def period(fills, covered, year):
    """(first, last) day of the span the PDC is taken over."""
    first = index_date(fills)
    if in_measure(fills, year):
        return first, year_end(year)
    last = min(max(covered, default=first), year_end(year))
    return first, last
