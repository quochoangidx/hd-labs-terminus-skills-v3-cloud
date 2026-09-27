"""A member's figures for one class."""

from .coverage import covered as covered_days
from .measure import in_measure, index_date, period
from .rounding import tenth

ADHERENT_PDC = 80.0


def figures(fills, starts, stays, year):
    """The report figures of one member for one class, from the member's fills of that class."""
    days = covered_days(fills, starts)
    first, last = period(fills, days, year)
    span = (last - first + 1) - sum(1 for d in stays if first <= d <= last)
    counted = sum(1 for d in days if first <= d <= last and d not in stays)
    pdc = tenth(100 * counted / span) if span else tenth(0)
    measured = in_measure(fills, year)
    return {
        "index": index_date(fills),
        "in_measure": measured,
        "period": span,
        "covered": counted,
        "pdc": pdc,
        "adherent": measured and pdc >= ADHERENT_PDC,
    }
