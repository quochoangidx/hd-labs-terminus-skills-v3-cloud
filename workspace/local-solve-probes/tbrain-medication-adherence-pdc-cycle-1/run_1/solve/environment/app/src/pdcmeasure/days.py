"""Calendar days as ordinals."""

from datetime import date


def day(text):
    """The ordinal of a YYYY-MM-DD day."""
    return date.fromisoformat(text).toordinal()


def text(ordinal):
    """The YYYY-MM-DD form of an ordinal."""
    return date.fromordinal(ordinal).isoformat()


def year_end(year):
    """The ordinal of the last day of a year."""
    return date(year, 12, 31).toordinal()


def month_day(year, month, number):
    """The ordinal of a day named by year, month and day of month."""
    return date(year, month, number).toordinal()
