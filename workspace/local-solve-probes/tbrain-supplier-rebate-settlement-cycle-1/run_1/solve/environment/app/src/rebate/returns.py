"""Returns taken back by the supplier."""

from .dates import in_quarter, parse_day

# Cents the supplier keeps for each unit it handles back.
HANDLING_PER_UNIT = 40


def returns_credit(returns, quarter):
    """The credit in cents for the returns of the quarter."""
    credit = 0
    for taken, units, unit_cents in returns:
        if in_quarter(parse_day(taken), quarter):
            credit += units * (unit_cents - HANDLING_PER_UNIT)
    return credit
