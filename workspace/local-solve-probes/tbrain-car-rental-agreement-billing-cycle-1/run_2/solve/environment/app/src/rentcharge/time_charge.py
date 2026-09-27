"""Days and the time charge."""

from .clock import DAY, length

FREE_MINUTES = 59


def days(agreement):
    """The days a rental is charged for (manual RC-3 rules 2.2 and 2.3).

    A day rental, one of 1,440 minutes or more, is charged for its whole days
    of 1,440 minutes and for one more day when the minutes left over are more
    than 59.  The manual gives no day rule for a shorter rental, so one is
    worked out as before, from the rental's length.
    """
    spell = length(agreement)
    if spell < DAY:
        return -(-spell // DAY)
    whole, over = divmod(spell, DAY)
    return whole + (1 if over > FREE_MINUTES else 0)


def time_charge(agreement):
    return days(agreement) * agreement["day_rate"]
