"""Wage lines, the base period and the average weekly wage."""

from datetime import timedelta

from .dates import parse_day, week_ending, weeks_back, WEEK
from .money import half_up

BASE_WEEKS = 13

# A wage line of this much or more is a week's pay (manual 2.2).
WEEKS_PAY_FLOOR = 2000

# The payroll pays for a payroll week on the Friday that follows the week's Sunday.
PAYDAY_AFTER_SUNDAY = timedelta(days=5)


def credited_week(paid, cents):
    """The payroll week (its Sunday) a wage line counts toward.

    A week's pay counts toward the week whose work it pays: the payroll pays for a week
    on the Friday that follows the week's Sunday, so that Sunday is five days before the
    payday (manual 2.2, 3.1).
    """
    if cents >= WEEKS_PAY_FLOOR:
        return paid - PAYDAY_AFTER_SUNDAY
    return week_ending(paid)


def credit_lines(lines):
    """Pair each wage line with the payroll week (its Sunday) the line counts toward.

    Lines come from the payroll register as [paid, cents]; the register is dated by the
    day the money went out.
    """
    credited = []
    for paid, cents in lines:
        day = parse_day(paid)
        credited.append((credited_week(day, cents), cents))
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
