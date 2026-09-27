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


def index_limit(year):
    """The ordinal of 2 October, the latest index date the measure accepts (AM-2 2.4)."""
    return date(year, 10, 2).toordinal()
