"""Temporary partial disability after the worker goes back to lighter work."""

from .money import ratio_of
from .rates import RATE_FRACTION

# A week of the partial earnings is a week of partial disability when the worker
# earned this much or more (manual 2.8).
PARTIAL_DISABILITY_EARNINGS = 1000

# Every week of the partial earnings has a benefit (manual 5.2), but only a week of
# partial disability has one the manual works out (manual 5.1). For the other weeks the
# benefit keeps coming out the way the package has always worked it out, from the
# average weekly wage and weekly rate of the manual.
OTHER_WEEK_FRACTION = (3, 5)


def wage_loss(aww, earned):
    """What the week fell short of the average weekly wage, in cents."""
    return aww - earned if earned < aww else 0


def week_benefit(earned, aww, rate):
    """The benefit of one week of the partial earnings, in cents."""
    fraction = RATE_FRACTION if earned >= PARTIAL_DISABILITY_EARNINGS else OTHER_WEEK_FRACTION
    benefit = ratio_of(wage_loss(aww, earned), fraction)
    return min(benefit, rate)


def partial_disability(earnings, aww, rate):
    """The number of weeks in the partial earnings and the partial amount in cents."""
    total = sum(week_benefit(earned, aww, rate) for _week, earned in earnings)
    return {"tpd_weeks": len(earnings), "tpd": total}
