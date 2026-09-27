"""A member's figures for one class."""

from .coverage import covered as covered_days
from .measure import in_measure, index_date, period
from .rounding import tenth

ADHERENT_PDC = 80.0


def figures(fills, stays, year):
    """The report figures of one member for one class, from the member's fills of that class."""
    days = covered_days(fills)
    measured = in_measure(fills, year)
    first, last = period(fills, days, year)
    span = last - first + 1
    if measured:
        span -= sum(1 for d in range(first, last + 1) if d in stays)
    counted = sum(1 for d in range(first, last + 1) if d in days and d not in stays)
    pdc = tenth(100 * counted / span)
    return {
        "index": index_date(fills),
        "in_measure": measured,
        "period": span,
        "covered": counted,
        "pdc": pdc,
        "adherent": measured and pdc >= ADHERENT_PDC,
    }
