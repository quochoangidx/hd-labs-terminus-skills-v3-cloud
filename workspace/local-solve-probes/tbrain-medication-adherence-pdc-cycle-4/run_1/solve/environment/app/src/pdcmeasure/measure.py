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
    """Whether the member counts in the measure for the class (AM-2 2.4).

    Fills on two or more different fill dates, with the index date no later than 2 October.
    """
    dates = {fill.date for fill in fills if fill.days >= 1}
    if len(dates) < 2:
        return False
    return min(dates) <= last_index_day(year)


def period(fills, covered, year, measured):
    """(first, last) day of the span the PDC is taken over.

    For a member in the measure this is the treatment period, from the index date to the last day
    of the measurement year (AM-2 2.5). The specification gives no span for a member who is not in
    the measure, so that span is worked out as the package has always worked it out.
    """
    first = index_date(fills)
    if measured:
        return first, year_end(year)
    last = min(max(covered, default=first), year_end(year))
    return first, last
