"""Wage lines, the base period and the average weekly wage."""

from .dates import parse_day, week_ending, weeks_back, WEEK
from .money import half_up

BASE_WEEKS = 13

# A wage line of this much or more is a week's pay (manual 2.2).
WEEKS_PAY = 2000


def week_credited(paid, cents):
    """The payroll week (its Sunday) a wage line paid on `paid` counts toward.

    A week's pay counts toward the week whose work it pays, and the payroll pays for a
    week on the Friday that follows the week's Sunday (manual 2.2, 3.1), so that week is
    the one before the week holding the payday. Smaller lines are corrections to earlier
    pay; the manual sets no week for them, so they keep counting toward the payroll week
    the payment was made in.
    """
    if cents >= WEEKS_PAY:
        return week_ending(paid) - WEEK
    return week_ending(paid)


def credit_lines(lines):
    """Pair each wage line with the payroll week (its Sunday) the line counts toward.

    Lines come from the payroll register as [paid, cents]; the register is dated by the
    day the money went out.
    """
    credited = []
    for paid, cents in lines:
        day = parse_day(paid)
        credited.append((week_credited(day, cents), cents))
    return credited


def base_period(injury):
    """The Sundays of the base-period weeks for a date of injury, oldest first."""
    return weeks_back(week_ending(injury) - WEEK, BASE_WEEKS)


def base_period_lines(lines, injury):
    """The credited lines that fall in the base period, as (week, cents)."""
    weeks = set(base_period(injury))
    return [(week, cents) for week, cents in credit_lines(lines) if week in weeks]


def average_weekly_wage(lines, injury):
    """The worker's average weekly wage in cents."""
    in_base = base_period_lines(lines, injury)
    wages = sum(cents for _week, cents in in_base)
    return half_up(wages, BASE_WEEKS)
