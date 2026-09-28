"""Returns taken back by the supplier."""

from .dates import in_quarter, parse_day
from .rates import figure


def returns_credit(returns, quarter):
    """The credit in cents for the returns of the quarter."""
    credit = 0
    for taken, units, unit_cents in returns:
        if in_quarter(parse_day(taken), quarter):
            credit += units * (unit_cents - figure("return_charge"))
    return credit
