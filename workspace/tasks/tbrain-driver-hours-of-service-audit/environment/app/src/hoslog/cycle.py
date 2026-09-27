"""The rolling on-duty cycle."""

from .stretches import day_totals, is_on_duty

CYCLE_DAYS = 8
CYCLE_MINUTES = 70 * 60
RECAP_DAYS = 7


def history(log, items, ndays):
    """On-duty minutes per day: the recap days, then the log's own days."""
    return list(log["recap"]) + day_totals(items, ndays, is_on_duty)


def earlier_days(hist, day):
    """On-duty minutes of the cycle days before ``day`` (a log day, from 0)."""
    here = RECAP_DAYS + day
    return sum(hist[max(0, here - (CYCLE_DAYS - 1)):here])
