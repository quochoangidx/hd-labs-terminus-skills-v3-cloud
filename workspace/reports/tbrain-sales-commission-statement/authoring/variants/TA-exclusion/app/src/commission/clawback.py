"""Commission taken back on credit notes."""

from .dates import days_between, in_quarter, parse_day
from .figures import figure
from .money import rep_share, share_of

REVERSAL_CENTS = 50000  # plan 2.3


def clawback_lines(credits, quarter):
    """One clawback line in cents for each credit note raised in the quarter."""
    lines = []
    for raised, booked, amount, split in credits:
        if not in_quarter(parse_day(raised), quarter):
            continue
        if amount < REVERSAL_CENTS:
            lines.append(0)
            continue
        limit = figure("reversal_age")
        if days_between(booked, raised) > limit:
            lines.append(0)
            continue
        lines.append(share_of(rep_share(amount, split), figure("clawback_rate")))
    return lines


def clawback(credits, quarter):
    """The rep's clawback in cents."""
    return sum(clawback_lines(credits, quarter))
