"""Wage lines, the base period and the average weekly wage."""

from .dates import parse_day, week_ending, week_paid_for, weeks_back, WEEK
from .money import half_up

BASE_WEEKS = 13

# Rule 2.2: a wage line of this much or more is a week's pay.
WEEKS_PAY_MINIMUM = 2000


def credit_lines(lines):
    """Pair each wage line with the payroll week (its Sunday) the line counts toward.

    Lines come from the payroll register as [paid, cents]; the register is dated by the
    day the money went out. A week's pay (rule 2.2) counts toward the payroll week whose
    work it pays (rule 3.1), the week closed by the Sunday five days before the payday.
    Small corrections are not a week's pay; no rule of the manual reaches them, so they
    keep counting toward the payroll week the package has always credited them to.
    """
    credited = []
    for paid, cents in lines:
        day = parse_day(paid)
        if cents >= WEEKS_PAY_MINIMUM:
            credited.append((week_paid_for(day), cents))
        else:
            credited.append((week_ending(day), cents))
    return credited


def base_period(injury):
    """The Sundays of the base-period weeks for a date of injury, oldest first."""
    return weeks_back(week_ending(injury) - WEEK, BASE_WEEKS)


def base_period_lines(lines, injury):
    """The credited lines that fall in the base period, as (week, cents)."""
    weeks = set(base_period(injury))
    return [(week, cents) for week, cents in credit_lines(lines) if week in weeks]


def average_weekly_wage(lines, injury):
    """The worker's average weekly wage in cents (rules 3.2 and 3.3)."""
    in_base = base_period_lines(lines, injury)
    wages = sum(cents for _week, cents in in_base)
    return half_up(wages, BASE_WEEKS)
