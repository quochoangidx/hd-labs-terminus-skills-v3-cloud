"""Which day of the month each reading on a station's form belongs to."""

from .entries import UNREAD, hundredths, tenths


def form_rows(station):
    """The station's entries with their form days: 1 to N for the month's own days, N + 1 for `next`,
    the first observation of the following month."""
    rows = list(station["days"]) + [station["next"]]
    return list(enumerate(rows, start=1))


def morning(station):
    """Whether the station's observation is a morning one (2.2): an hour from 0 through 11."""
    return 0 <= station["hour"] <= 11


def in_month(by_day, days):
    """Only the readings credited to one of the month's days."""
    return {day: value for day, value in by_day.items() if 1 <= day <= days}


def credit_temperatures(station, days):
    """The maxima and minima credited to the month's days, each as {day: tenths}.

    A day's maximum read at a morning observation belongs to the day before its form day (3.1); a
    day's minimum belongs to its form day at every hour (3.2).
    """
    shift = 1 if morning(station) else 0
    maxima, minima = {}, {}
    for day, entry in form_rows(station):
        high = tenths(entry["max"])
        if high is not None:
            maxima[day - shift] = high
        low = tenths(entry["min"])
        if low is not None:
            minima[day] = low
    return in_month(maxima, days), in_month(minima, days)


def credit_precipitation(station, days):
    """The precipitation credited to the month's days, as {day: hundredths}.

    A day's precipitation is credited as a day's maximum is (3.3): to the day before its form day at a
    morning observation and to its form day at an afternoon one. An accumulated amount (1.3) is the
    catch of more than one observation day, so it is not a day's precipitation (2.4) and no rule of the
    handbook credits it; it keeps the form day the package has always given it.
    """
    shift = 1 if morning(station) else 0
    totals = {}
    previous_unread = False
    for day, entry in form_rows(station):
        written = entry["precip"]
        accumulated = previous_unread
        previous_unread = written == UNREAD
        amount = hundredths(written)
        if amount is None:
            continue
        credited = day if accumulated else day - shift
        totals[credited] = totals.get(credited, 0) + amount
    return in_month(totals, days)
