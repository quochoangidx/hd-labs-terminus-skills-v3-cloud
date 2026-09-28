"""Temporary partial disability after the worker goes back to lighter work."""

from .money import ratio_of
from .rates import RATE_FRACTION

# Rule 2.8: a week of the partial earnings in which the worker earned this much
# or more is a week of partial disability.
PARTIAL_DISABILITY_EARNINGS = 1000

# Weeks that are not weeks of partial disability are reached by no rule of the
# manual, so their benefit stays the one the package has always worked out, with
# the share it has always used.
OTHER_WEEK_FRACTION = (3, 5)


def wage_loss(aww, earned):
    """What the week fell short of the average weekly wage, in cents (rule 2.7)."""
    return aww - earned if earned < aww else 0


def week_benefit(aww, earned, rate):
    """The benefit for one week of the partial earnings, in cents."""
    loss = wage_loss(aww, earned)
    if earned >= PARTIAL_DISABILITY_EARNINGS:
        return min(ratio_of(loss, RATE_FRACTION), rate)
    return min(ratio_of(loss, OTHER_WEEK_FRACTION), rate)


def partial_disability(earnings, aww, rate):
    """The number of partial weeks and the partial amount in cents."""
    total = 0
    for _week, earned in earnings:
        total += week_benefit(aww, earned, rate)
    return {"tpd_weeks": len(earnings), "tpd": total}
