"""Which day of the month each reading on a station's form belongs to."""

from .entries import hundredths, tenths

LAST_MORNING_HOUR = 11  # an observation at hour 0 through 11 is a morning observation (2.2)


def is_morning(station):
    """Whether the station's observations are morning observations (2.2)."""
    return int(station["hour"]) <= LAST_MORNING_HOUR


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
    shift = 1 if is_morning(station) else 0
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
    """The precipitation credited to the month's days, as {day: hundredths}."""
    shift = 1 if is_morning(station) else 0
    totals = {}
    for day, entry in form_rows(station):
        amount = hundredths(entry["precip"])
        if amount is None:
            continue
        credited = day - shift
        totals[credited] = totals.get(credited, 0) + amount
    return in_month(totals, days)
