"""Calendar helpers: dates are ISO strings in the job file, payroll weeks run Monday to Sunday."""

from datetime import date, timedelta

WEEK = timedelta(days=7)

# The payroll runs on Fridays (weekday 4) and pays for a week on the Friday
# that follows that week's Sunday, five days later (manual 2.2).
PAYROLL_WEEKDAY = 4
PAYROLL_LAG = timedelta(days=5)


def parse_day(text):
    """The calendar day written as YYYY-MM-DD."""
    return date.fromisoformat(text)


def week_ending(day):
    """The Sunday that closes the payroll week holding `day`."""
    return day + timedelta(days=6 - day.weekday())


def is_payroll_day(day):
    """Whether `day` is a payroll day, that is a Friday."""
    return day.weekday() == PAYROLL_WEEKDAY


def week_paid_for(day):
    """The Sunday of the payroll week a Friday payroll line pays for."""
    return day - PAYROLL_LAG


def weeks_back(sunday, count):
    """The `count` payroll weeks ending with the one closed by `sunday`, oldest first."""
    return [sunday - WEEK * k for k in range(count - 1, -1, -1)]
