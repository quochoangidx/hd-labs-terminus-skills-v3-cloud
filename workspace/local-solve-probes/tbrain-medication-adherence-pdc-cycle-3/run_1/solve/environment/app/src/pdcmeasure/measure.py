"""Index date, the measure's denominator test and the span the PDC is taken over."""

from datetime import date

from .days import year_end


def index_date(fills):
    """The fill date of the member's earliest fill of the class (AM-2 2.3)."""
    return min(fill.date for fill in fills if fill.days >= 1)


def last_index_day(year):
    """The ordinal of 2 October of the measurement year (AM-2 2.4)."""
    return date(year, 10, 2).toordinal()


def in_measure(fills, year):
    """Whether the member counts in the measure for the class (AM-2 2.4)."""
    dates = {fill.date for fill in fills if fill.days >= 1}
    return len(dates) >= 2 and min(dates) <= last_index_day(year)


def period(fills, covered, year, measured):
    """(first, last) day of the span the PDC is taken over: the treatment period of a member in the
    measure (AM-2 2.5)."""
    first = index_date(fills)
    end = year_end(year)
    last = end if measured else min(max(covered, default=first), end)
    return first, last
