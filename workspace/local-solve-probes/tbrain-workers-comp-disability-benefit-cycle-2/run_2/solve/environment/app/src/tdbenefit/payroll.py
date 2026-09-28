"""Wage lines, the base period and the average weekly wage."""

from .dates import parse_day, week_ending, week_paid_on, weeks_back, WEEK
from .money import half_up

BASE_WEEKS = 13

# A wage line of this much or more is a week's pay (manual 2.2); smaller lines are
# corrections to earlier pay, and no rule of the manual says which payroll week they
# count toward, so they keep counting toward the week that holds their payday.
WEEKS_PAY_MINIMUM = 2000


def credit_lines(lines):
    """Pair each wage line with the payroll week (its Sunday) the line counts toward.

    Lines come from the payroll register as [paid, cents]; the register is dated by the
    day the money went out. A week's pay counts toward the week whose work it pays
    (manual 2.2, 3.1); a correction keeps counting toward the week of its payday.
    """
    credited = []
    for paid, cents in lines:
        day = parse_day(paid)
        if cents >= WEEKS_PAY_MINIMUM:
            credited.append((week_paid_on(day), cents))
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
    """The worker's average weekly wage in cents: the base-period wages over thirteen."""
    wages = sum(cents for _week, cents in base_period_lines(lines, injury))
    return half_up(wages, BASE_WEEKS)
