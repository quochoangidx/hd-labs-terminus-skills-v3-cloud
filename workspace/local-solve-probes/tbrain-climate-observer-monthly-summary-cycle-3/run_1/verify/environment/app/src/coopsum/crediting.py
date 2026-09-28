"""Which day of the month each reading on a station's form belongs to."""

from .entries import hundredths, tenths


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
    for day, entry in form_rows(station):
        high = tenths(entry["max"])
        if high is not None:
            maxima[day] = high
        low = tenths(entry["min"])
        if low is not None:
            minima[day] = low
    return in_month(maxima, days), in_month(minima, days)


def credit_precipitation(station, days):
    """The precipitation credited to the month's days, as {day: hundredths}."""
    totals = {}
    for day, entry in form_rows(station):
        amount = hundredths(entry["precip"])
        if amount is None:
            continue
        totals[day] = totals.get(day, 0) + amount
    return in_month(totals, days)
