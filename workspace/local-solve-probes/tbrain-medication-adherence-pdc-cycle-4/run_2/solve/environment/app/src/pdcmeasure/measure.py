"""Index date, the measure's denominator test and the span the PDC is taken over."""

from .days import index_limit, year_end


def dispensed(fills):
    """The claim lines that dispensed a supply (AM-2 2.1)."""
    return [fill for fill in fills if fill.days >= 1]


def index_date(fills):
    """The fill date of the member's earliest fill of the class (AM-2 2.3)."""
    return min(fill.date for fill in dispensed(fills))


def in_measure(fills, year):
    """Whether the member counts in the measure for the class (AM-2 2.4)."""
    dates = {fill.date for fill in dispensed(fills)}
    return len(dates) >= 2 and index_date(fills) <= index_limit(year)


def period(fills, covered, year):
    """(first, last) day of the span the PDC is taken over.

    For a member in the measure this is the treatment period, from the index date to the last day of
    the measurement year (AM-2 2.5). The specification gives no period for a member who is not in the
    measure, so that span is still worked out as the package has always worked it out.
    """
    first = index_date(fills)
    if in_measure(fills, year):
        return first, year_end(year)
    last = min(max(covered, default=first), year_end(year))
    return first, last
