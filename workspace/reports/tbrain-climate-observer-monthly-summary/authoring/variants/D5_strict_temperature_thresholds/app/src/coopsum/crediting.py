"""Which day of the month each reading on a station's form belongs to."""

from .entries import UNREAD, hundredths, tenths

LAST_MORNING_HOUR = 11


def morning(station):
    """Whether the station's observation is a morning observation (hour 0 through 11)."""
    return station["hour"] <= LAST_MORNING_HOUR


def form_rows(station):
    """The station's entries with their form days: 1 to N for the month's own days, N + 1 for `next`,
    the first observation of the following month."""
    rows = list(station["days"]) + [station["next"]]
    return list(enumerate(rows, start=1))


def in_month(by_day, days):
    """Only the readings credited to one of the month's days."""
    return {day: value for day, value in by_day.items() if 1 <= day <= days}


def credit_temperatures(station, days):
    """The maxima and minima credited to the month's days, each as {day: tenths}."""
    maxima, minima = {}, {}
    shift = 1 if morning(station) else 0
    for day, entry in form_rows(station):
        high = tenths(entry["max"])
        if high is not None:
            maxima[day - shift] = high
        low = tenths(entry["min"])
        if low is not None:
            minima[day] = low
    return in_month(maxima, days), in_month(minima, days)


def credit_precipitation(station, days):
    """The precipitation credited to the month's days, as {day: hundredths}."""
    totals = {}
    shift = 1 if morning(station) else 0
    unread = False
    for day, entry in form_rows(station):
        if entry["precip"] == UNREAD:
            unread = True
            continue
        amount = hundredths(entry["precip"])
        if amount is None:
            continue
        # An accumulated amount (after unread days) holds two or more observation days, so it is not a
        # day's precipitation (2.4) and 3.3 does not reach it; it stays on its form day as before.
        credited = day if unread else day - shift
        unread = False
        totals[credited] = totals.get(credited, 0) + amount
    return in_month(totals, days)
