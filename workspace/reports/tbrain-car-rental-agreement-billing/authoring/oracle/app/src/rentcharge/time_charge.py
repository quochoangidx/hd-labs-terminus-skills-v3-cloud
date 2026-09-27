"""Days and the time charge."""

from .clock import DAY, length


def days(agreement):
    """The days a rental is charged for: a day rental's whole days, and one more past 59 minutes over."""
    minutes = length(agreement)
    if minutes >= DAY:
        return minutes // DAY + (1 if minutes % DAY > 59 else 0)
    return -(-minutes // DAY)


def time_charge(agreement):
    return days(agreement) * agreement["day_rate"]
