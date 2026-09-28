"""Disability days, the waiting period and the temporary total disability amount."""

from .dates import parse_day
from .money import half_up

WAITING_DAYS = 7
RETROACTIVE_AFTER = 14


def period_days(first, last):
    """The number of days a certified period covers."""
    return (parse_day(last) - parse_day(first)).days + 1


def disability_days(periods):
    """A claim's disability days over all of its certified periods."""
    return sum(period_days(first, last) for first, last in periods)


def total_disability(periods, rate):
    """Waiting, retroactive and paid days, and the amount for them, in cents."""
    days = disability_days(periods)
    waiting = min(WAITING_DAYS, days)
    retroactive = waiting if days >= RETROACTIVE_AFTER else 0
    paid = days - waiting + retroactive
    amount = half_up(rate * paid, 7)
    return {"waiting_days": waiting, "retro_days": retroactive, "ttd_days": paid, "ttd": amount}
