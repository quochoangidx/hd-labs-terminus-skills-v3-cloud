"""Temporary partial disability after the worker goes back to lighter work."""

from .money import ratio_of
from .rates import RATE_FRACTION


def wage_loss(aww, earned):
    """What the week fell short of the average weekly wage, in cents (rule 2.8)."""
    return aww - earned if earned < aww else 0


def week_benefit(aww, earned, rate):
    """One partial week's benefit: two thirds of its wage loss, capped at the weekly rate (rule 5.1)."""
    benefit = ratio_of(wage_loss(aww, earned), RATE_FRACTION)
    return benefit if benefit < rate else rate


def partial_disability(earnings, aww, rate):
    """The number of partial weeks and the partial amount in cents."""
    total = 0
    for _week, earned in earnings:
        total += week_benefit(aww, earned, rate)
    return {"tpd_weeks": len(earnings), "tpd": total}
