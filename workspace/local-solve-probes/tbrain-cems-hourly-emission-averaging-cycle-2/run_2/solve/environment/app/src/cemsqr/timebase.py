"""Record times, hours and calendar days."""

import datetime


def hour_of(start):
    """The clock hour a record starting at `start` (YYYY-MM-DD HH:MM) falls in."""
    return start[:13]


def day_of(hour):
    """The calendar day an hour (YYYY-MM-DD HH) belongs to."""
    return hour[:10]


def day_number(day):
    """A day count that grows by one from each calendar day to the next."""
    return datetime.date.fromisoformat(day).toordinal()
