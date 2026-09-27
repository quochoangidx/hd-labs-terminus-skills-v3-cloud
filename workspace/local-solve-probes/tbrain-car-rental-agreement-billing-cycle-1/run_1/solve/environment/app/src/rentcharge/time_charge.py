"""Days and the time charge."""

from .clock import DAY, length

FREE_MINUTES = 59


def days(agreement):
    """The days a rental's time charge is for (manual RC-3 rules 2.2, 2.3).

    A day rental, one of 1,440 minutes or more, is charged for its whole days
    and for one more day when more than 59 minutes are left over; up to 59
    minutes past a whole day are free.
    """
    span = length(agreement)
    if span < DAY:
        return -(-span // DAY)
    whole, extra = divmod(span, DAY)
    return whole + (1 if extra > FREE_MINUTES else 0)


def time_charge(agreement):
    return days(agreement) * agreement["day_rate"]
