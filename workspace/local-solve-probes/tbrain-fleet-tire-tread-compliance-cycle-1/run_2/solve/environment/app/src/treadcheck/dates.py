"""Calendar helpers. Dates arrive as YYYY-MM-DD strings."""

from datetime import date


def parse(text):
    """The date a YYYY-MM-DD string names."""
    return date.fromisoformat(text)


def days_between(first, second):
    """Whole days from the first date to the second."""
    return (parse(second) - parse(first)).days


def year_of(text):
    """The calendar year of a date string."""
    return parse(text).year
