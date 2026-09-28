"""Calendar days and quarters."""

import datetime

DAY = datetime.timedelta(days=1)


def parse_day(text):
    """A YYYY-MM-DD string as a date."""
    return datetime.date.fromisoformat(text)


def quarter_bounds(quarter):
    """The first and last day of a quarter written YYYY-Qn."""
    year, number = quarter.split("-Q")
    year, number = int(year), int(number)
    first = datetime.date(year, 3 * number - 2, 1)
    if number == 4:
        after = datetime.date(year + 1, 1, 1)
    else:
        after = datetime.date(year, 3 * number + 1, 1)
    return first, after - DAY


def in_quarter(day, quarter):
    """Whether a date falls in the quarter, both ends included."""
    first, last = quarter_bounds(quarter)
    return first <= day <= last


def days_between(earlier, later):
    """Whole days from one YYYY-MM-DD date to another."""
    return (parse_day(later) - parse_day(earlier)).days
