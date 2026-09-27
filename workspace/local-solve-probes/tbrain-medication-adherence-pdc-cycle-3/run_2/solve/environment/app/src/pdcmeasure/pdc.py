"""A member's figures for one class."""

from fractions import Fraction

from .coverage import covered as covered_days
from .measure import in_measure, index_date, period
from .rounding import tenth

ADHERENT_PDC = 80.0


def figures(fills, stays, year):
    """The report figures of one member for one class, from the member's fills of that class."""
    days = covered_days(fills)
    first, last = period(fills, year)
    span = [d for d in range(first, last + 1) if d not in stays]
    period_days = len(span)
    counted = sum(1 for d in span if d in days)
    pdc = tenth(Fraction(100 * counted, period_days)) if period_days else tenth(0)
    measured = in_measure(fills, year)
    return {
        "index": index_date(fills),
        "in_measure": measured,
        "period": period_days,
        "covered": counted,
        "pdc": pdc,
        "adherent": measured and pdc >= ADHERENT_PDC,
    }
