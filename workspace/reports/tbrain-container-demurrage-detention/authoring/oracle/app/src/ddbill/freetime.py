"""Free time and chargeable days (tariff rules sections 3 and 4)."""

from .dates import ONE_DAY, plus_days
from .stays import TERMINAL


def last_free_day(stage, free_days, calendar):
    """The date on which the stage's last free day is used."""
    if stage["name"] != TERMINAL or free_days == 0:
        return plus_days(stage["first"], free_days - 1)
    day, used = stage["first"], 0
    while True:
        if calendar.is_working_day(day) and not calendar.is_closure(day):
            used += 1
            if used == free_days:
                return day
        day += ONE_DAY


def chargeable_dates(stage, free_days, calendar):
    """The stage's days after its free time, closure days left out at the terminal."""
    out = []
    day = last_free_day(stage, free_days, calendar) + ONE_DAY
    while day <= stage["last"]:
        if not (stage["name"] == TERMINAL and calendar.is_closure(day)):
            out.append(day)
        day += ONE_DAY
    return out


def chargeable_days(stage, free_days, calendar):
    """How many of the stage's days are chargeable."""
    return len(chargeable_dates(stage, free_days, calendar))
