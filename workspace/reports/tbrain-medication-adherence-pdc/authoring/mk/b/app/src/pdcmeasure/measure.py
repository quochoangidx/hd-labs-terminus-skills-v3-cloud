"""Index date, the measure's denominator test and the span the PDC is taken over."""

from .days import year_end


def index_date(fills):
    return min(fill.date for fill in fills)


def in_measure(fills, year):
    """Whether the member counts in the measure for the class."""
    return len({fill.date for fill in fills}) >= 2 and index_date(fills) <= year_end(year) - 90


def period(fills, covered, year):
    """(first, last) day of the span the PDC is taken over."""
    first = index_date(fills)
    if in_measure(fills, year):
        return first, year_end(year)
    last = min(max(covered, default=first), year_end(year))
    return first, last
