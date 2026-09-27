"""Index date, the measure's denominator test and the span the PDC is taken over."""

from datetime import date

from .days import year_end

LATEST_INDEX_MONTH = 10
LATEST_INDEX_DAY = 2


def index_date(fills):
    return min(fill.date for fill in fills)


def latest_index(year):
    """The last day of the year that an index date may fall on."""
    return date(year, LATEST_INDEX_MONTH, LATEST_INDEX_DAY).toordinal()


def in_measure(fills, year):
    """Whether the member counts in the measure for the class: fills on two or
    more different fill dates, with the index date no later than 2 October."""
    dates = {fill.date for fill in fills}
    return len(dates) >= 2 and index_date(fills) <= latest_index(year)


def period(fills, covered, year, measured=False):
    """(first, last) day of the span the PDC is taken over."""
    first = index_date(fills)
    if measured:
        return first, year_end(year)
    last = min(max(covered, default=first), year_end(year))
    return first, last
