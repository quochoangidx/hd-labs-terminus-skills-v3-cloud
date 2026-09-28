"""Calendar helpers: dates are ISO strings in the job file, payroll weeks run Monday to Sunday."""

from datetime import date, timedelta

WEEK = timedelta(days=7)

# Rule 2.2: the payroll pays for a payroll week on the Friday that follows the
# week's Sunday, five days after it.
PAYDAY_LAG = timedelta(days=5)


def parse_day(text):
    """The calendar day written as YYYY-MM-DD."""
    return date.fromisoformat(text)


def week_ending(day):
    """The Sunday that closes the payroll week holding `day`."""
    return day + timedelta(days=6 - day.weekday())


def week_paid_for(payday):
    """The Sunday of the payroll week whose work is paid on `payday` (rule 2.2)."""
    return payday - PAYDAY_LAG


def weeks_back(sunday, count):
    """The `count` payroll weeks ending with the one closed by `sunday`, oldest first."""
    return [sunday - WEEK * k for k in range(count - 1, -1, -1)]
