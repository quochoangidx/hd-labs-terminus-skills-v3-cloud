"""A member's figures for one class."""

from fractions import Fraction

from .coverage import covered as covered_days
from .measure import in_measure, index_date, period
from .rounding import tenth

ADHERENT_PDC = 80.0


def figures(fills, stays, year):
    """The report figures of one member for one class, from the member's fills of that class."""
    days = covered_days(fills)
    measured = in_measure(fills, year)
    first, last = period(fills, days, year)
    span = range(first, last + 1)
    counted = sum(1 for d in span if d in days and d not in stays)
    if measured:
        # Rule 4.1: the period days are the treatment period days that are not stay days.
        period_days = sum(1 for d in span if d not in stays)
    else:
        period_days = last - first + 1
    pdc = tenth(Fraction(100 * counted, period_days))
    return {
        "index": index_date(fills),
        "in_measure": measured,
        "period": period_days,
        "covered": counted,
        "pdc": pdc,
        "adherent": measured and pdc >= ADHERENT_PDC,
    }
