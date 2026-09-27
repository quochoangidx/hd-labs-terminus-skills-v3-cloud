"""Index date, the measure's denominator test and the span the PDC is taken over."""

from .days import in_year, year_end

LAST_INDEX_MONTH = 10
LAST_INDEX_DAY = 2
FILL_DATES_NEEDED = 2


def index_date(fills):
    """The fill date of the member's earliest fill of the class (rule 2.3)."""
    return min(fill.date for fill in fills if fill.days)


def in_measure(fills, year):
    """Whether the member counts in the measure for the class (rule 2.4)."""
    dates = {fill.date for fill in fills if fill.days}
    if len(dates) < FILL_DATES_NEEDED:
        return False
    return min(dates) <= in_year(year, LAST_INDEX_MONTH, LAST_INDEX_DAY)


def period(fills, year):
    """(first, last) day of the treatment period (rule 2.5)."""
    return index_date(fills), year_end(year)
