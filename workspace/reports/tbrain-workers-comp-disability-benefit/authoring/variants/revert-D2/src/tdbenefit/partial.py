"""Temporary partial disability after the worker goes back to lighter work."""

from .money import ratio_of
from .rates import RATE_FRACTION

PARTIAL_WEEK_FROM = 1_000  # cents earned: a week below it is not a week of partial disability
EARLIER_FRACTION = (3, 5)  # the share such a week has always been paid at


def wage_loss(aww, earned):
    """What the week fell short of the average weekly wage, in cents."""
    return aww - earned if earned < aww else 0


def partial_disability(earnings, aww, rate):
    """The number of partial weeks and the partial amount in cents."""
    total = 0
    for _week, earned in earnings:
        fraction = RATE_FRACTION if earned >= PARTIAL_WEEK_FROM else EARLIER_FRACTION
        benefit = ratio_of(wage_loss(aww, earned), fraction)
        total += min(benefit, rate)
    return {"tpd_weeks": len(earnings), "tpd": total}
