"""Bonus on a customer's first order."""

from .figures import figure
from .money import rep_share, share_of


def bonus_lines(counted):
    """One bonus line in cents for each first order among the quarter's orders."""
    lines = []
    for value, split, first in counted:
        if not first:
            continue
        credit = rep_share(value, split)
        if credit < figure("bonus_floor"):
            lines.append(0)
        else:
            lines.append(share_of(credit, figure("bonus_rate")))
    return lines


def bonus(counted):
    """The rep's bonus in cents."""
    return sum(bonus_lines(counted))
