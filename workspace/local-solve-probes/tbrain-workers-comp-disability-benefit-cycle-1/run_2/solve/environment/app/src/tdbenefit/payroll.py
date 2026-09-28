"""Wage lines, the base period and the average weekly wage."""

from .dates import parse_day, week_ending, weeks_back, WEEK, PAYROLL_WEEKDAY, payroll_week_paid
from .money import half_up

BASE_WEEKS = 13
FULL_TIME_WEEKS = 10


def is_weeks_pay(day):
    """Whether a wage line paid on `day` is the payroll's pay for one payroll week (rule 1.4, 2.2)."""
    return day.weekday() == PAYROLL_WEEKDAY


def credit_lines(lines):
    """Pair each wage line with the payroll week (its Sunday) the line counts toward.

    Lines come from the payroll register as [paid, cents]; the register is dated by the
    day the money went out. A week's pay goes out on the Friday after the week's Sunday
    and counts toward the week whose work it pays (rules 2.2 and 3.1). Pay outside the
    payroll is no week's pay, so no rule places it: it keeps counting toward the payroll
    week that holds the day it was approved.
    """
    credited = []
    for paid, cents in lines:
        day = parse_day(paid)
        if is_weeks_pay(day):
            credited.append((payroll_week_paid(day), cents, True))
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


def average_weekly_wage(lines, injury):
    """The worker's average weekly wage in cents."""
    in_base = base_period_lines(lines, injury)
    wages = sum(cents for _week, cents, _pay in in_base)
    weeks_with_pay = len({week for week, _cents, is_pay in in_base if is_pay})
    if weeks_with_pay >= FULL_TIME_WEEKS:
        # Rules 2.4 and 3.3: a full-time worker's wages spread over thirteen weeks.
        return half_up(wages, BASE_WEEKS)
    # No rule speaks to a worker who is not full-time: keep spreading the wages over
    # the base-period weeks that hold a line, as the package has always done.
    weeks_paid = len({week for week, _cents, _pay in in_base})
    return half_up(wages, weeks_paid)
