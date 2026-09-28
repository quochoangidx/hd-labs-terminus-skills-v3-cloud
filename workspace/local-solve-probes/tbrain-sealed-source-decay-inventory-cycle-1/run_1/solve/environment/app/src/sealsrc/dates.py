"""Calendar dates as they appear in the inventory (YYYY-MM-DD)."""

import datetime


def parse(text):
    """(year, month, day) of a YYYY-MM-DD date."""
    year, month, day = (int(part) for part in text.split("-"))
    return year, month, day


def elapsed_days(start, end):
    """Whole days from the date `start` to the date `end`.

    Actual days of the Gregorian calendar (manual 1.2): every month at its real
    length and 29 February in a leap year.
    """
    sy, sm, sd = parse(start)
    ey, em, ed = parse(end)
    days = datetime.date(ey, em, ed).toordinal() - datetime.date(sy, sm, sd).toordinal()
    return max(days, 0)
