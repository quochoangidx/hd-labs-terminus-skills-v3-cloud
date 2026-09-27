"""Index date, the measure's denominator test and the span the PDC is taken over."""

from datetime import date

from .days import year_end

LAST_INDEX_MONTH = 10
LAST_INDEX_DAY = 2


def index_date(fills):
    return min(fill.date for fill in fills)


def last_index_day(year):
    """The ordinal of the latest index date the measure accepts (rule 2.4)."""
    return date(year, LAST_INDEX_MONTH, LAST_INDEX_DAY).toordinal()


def in_measure(fills, year):
    """Whether the member counts in the measure for the class (rule 2.4)."""
    dates = {fill.date for fill in fills}
    return len(dates) >= 2 and index_date(fills) <= last_index_day(year)


def period(fills, covered, year):
    """(first, last) day of the treatment period (rule 2.5)."""
    return index_date(fills), year_end(year)
