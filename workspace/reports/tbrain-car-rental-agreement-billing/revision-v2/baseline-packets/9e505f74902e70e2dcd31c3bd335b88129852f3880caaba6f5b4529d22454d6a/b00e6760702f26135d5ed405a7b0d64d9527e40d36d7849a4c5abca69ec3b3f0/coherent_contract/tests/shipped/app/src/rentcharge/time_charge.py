"""Days and the time charge."""

from .clock import DAY, length


def days(agreement):
    """The days a rental is charged for: every day begun."""
    return -(-length(agreement) // DAY)


def time_charge(agreement):
    return days(agreement) * agreement["day_rate"]
