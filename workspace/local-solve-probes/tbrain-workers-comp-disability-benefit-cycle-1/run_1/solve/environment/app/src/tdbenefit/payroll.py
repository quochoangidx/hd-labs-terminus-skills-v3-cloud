"""Wage lines, the base period and the average weekly wage."""

from .dates import (
    WEEK,
    is_payroll_day,
    parse_day,
    week_ending,
    week_paid_for,
    weeks_back,
)
from .money import half_up

BASE_WEEKS = 13
FULL_TIME_WEEKS = 10


def credit_lines(lines):
    """Pair each wage line with the payroll week (its Sunday) the line counts toward.

    Lines come from the payroll register as [paid, cents]; the register is dated by the
    day the money went out. A payroll line goes out on the Friday after the Sunday of
    the week whose work it pays (manual 2.2, 3.1); pay outside the payroll never falls
    on a Friday and counts toward the payroll week it went out in.

    Each pair also says whether the line is a week's pay.
    """
    credited = []
    for paid, cents in lines:
        day = parse_day(paid)
        if is_payroll_day(day):
            credited.append((week_paid_for(day), cents, True))
        else:
            credited.append((week_ending(day), cents, False))
    return credited


def base_period(injury):
    """The Sundays of the base-period weeks for a date of injury, oldest first."""
    return weeks_back(week_ending(injury) - WEEK, BASE_WEEKS)


def base_period_lines(lines, injury):
    """The credited lines that fall in the base period, as (week, cents, is_weeks_pay)."""
    weeks = set(base_period(injury))
    return [entry for entry in credit_lines(lines) if entry[0] in weeks]


def is_full_time(lines, injury):
    """Whether the base period holds a week's pay for ten or more of its weeks (2.4)."""
    paid_weeks = {week for week, _cents, weeks_pay in base_period_lines(lines, injury) if weeks_pay}
    return len(paid_weeks) >= FULL_TIME_WEEKS


def average_weekly_wage(lines, injury):
    """The worker's average weekly wage in cents."""
    in_base = base_period_lines(lines, injury)
    wages = sum(cents for _week, cents, _weeks_pay in in_base)
    paid_weeks = {week for week, _cents, weeks_pay in in_base if weeks_pay}
    if len(paid_weeks) >= FULL_TIME_WEEKS:
        return half_up(wages, BASE_WEEKS)
    weeks_paid = len({week for week, _cents, _weeks_pay in in_base})
    return half_up(wages, weeks_paid)
