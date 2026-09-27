"""Free time and chargeable days (tariff rules sections 3 and 4)."""

from .dates import plus_days
from .stays import stage_days


def last_free_day(stage, free_days, calendar):
    """The date on which the stage's last free day is used."""
    return plus_days(stage["first"], free_days - 1)


def chargeable_days(stage, free_days, calendar):
    """How many of the stage's days fall after its free time."""
    return max(0, stage_days(stage) - free_days)
