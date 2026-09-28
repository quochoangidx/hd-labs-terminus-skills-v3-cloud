"""Temporary partial disability after the worker goes back to lighter work."""

from .money import ratio_of
from .rates import RATE_FRACTION


def wage_loss(aww, earned):
    """What the week fell short of the average weekly wage, in cents."""
    return aww - earned if earned < aww else 0


def partial_disability(earnings, aww):
    """The number of partial weeks and the partial amount in cents."""
    total = 0
    for _week, earned in earnings:
        total += ratio_of(wage_loss(aww, earned), RATE_FRACTION)
    return {"tpd_weeks": len(earnings), "tpd": total}
