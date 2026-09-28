"""Calendar helpers: dates are ISO strings in the job file, payroll weeks run Monday to Sunday."""

from datetime import date, timedelta

WEEK = timedelta(days=7)

# The payroll runs on Fridays (rule 1.4); Monday is 0, so Friday is 4.
PAYROLL_WEEKDAY = 4

# A week's pay goes out on the Friday that follows the week's Sunday (rule 2.2).
PAYDAY_AFTER_WEEK = timedelta(days=5)


def parse_day(text):
    """The calendar day written as YYYY-MM-DD."""
    return date.fromisoformat(text)


def week_ending(day):
    """The Sunday that closes the payroll week holding `day`."""
    return day + timedelta(days=6 - day.weekday())


def payroll_week_paid(payday):
    """The Sunday of the payroll week whose work the payroll pays on `payday`."""
    return payday - PAYDAY_AFTER_WEEK


def weeks_back(sunday, count):
    """The `count` payroll weeks ending with the one closed by `sunday`, oldest first."""
    return [sunday - WEEK * k for k in range(count - 1, -1, -1)]
