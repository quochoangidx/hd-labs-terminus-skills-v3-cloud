"""Index date, the measure's denominator test and the span the PDC is taken over."""

from .days import year_end


def index_date(fills):
    return min(fill.date for fill in fills)


def in_measure(fills, year):
    """Whether the member counts in the measure for the class."""
    return len(fills) >= 2


def period(fills, covered, year):
    """(first, last) day of the span the PDC is taken over."""
    first = index_date(fills)
    last = min(max(covered, default=first), year_end(year))
    return first, last
