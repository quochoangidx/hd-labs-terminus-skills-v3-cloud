"""Index date, the measure's denominator test and the span the PDC is taken over."""

from datetime import date

from .days import year_end

LATEST_INDEX = (10, 2)
FILL_DATES = 2


def index_date(fills):
    return min(fill.date for fill in fills)


def latest_index(year):
    """The last day of the year on which an index date may fall (rule 2.4)."""
    month, day_of_month = LATEST_INDEX
    return date(year, month, day_of_month).toordinal()


def in_measure(fills, year):
    """Whether the member counts in the measure for the class (rule 2.4)."""
    dates = {fill.date for fill in fills}
    return len(dates) >= FILL_DATES and index_date(fills) <= latest_index(year)


def period(fills, covered, year, measured):
    """(first, last) day of the span the PDC is taken over."""
    first = index_date(fills)
    if measured:
        return first, year_end(year)
    last = min(max(covered, default=first), year_end(year))
    return first, last
