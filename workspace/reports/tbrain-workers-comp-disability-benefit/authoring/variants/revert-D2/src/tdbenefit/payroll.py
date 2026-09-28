"""Wage lines, the base period and the average weekly wage."""

from .dates import parse_day, week_ending, weeks_back, WEEK
from .money import half_up

BASE_WEEKS = 13
WEEKS_PAY_FROM = 2_000  # cents: a smaller line is not a week's pay


def credit_lines(lines):
    """Pair each wage line with the payroll week (its Sunday) the line counts toward.

    Lines come from the payroll register as [paid, cents]; the register is dated by the
    day the money went out.
    """
    credited = []
    for paid, cents in lines:
        day = parse_day(paid)
        week = week_ending(day)
        if cents >= WEEKS_PAY_FROM:
            week -= WEEK
        credited.append((week, cents))
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
    return half_up(wages, len({week for week, _cents in in_base}))
