"""Which day of the month each reading on a station's form belongs to (handbook section 3)."""

from .entries import TRACE, UNREAD, hundredths, tenths

LAST_MORNING_HOUR = 11  # 2.2: an observation from 0 through 11 is a morning observation


def morning(hour):
    """Whether the station's observation hour makes a morning observation (2.2)."""
    return 0 <= hour <= LAST_MORNING_HOUR


def form_rows(station):
    """The station's entries with their form days: 1 to N for the month's own days, N + 1 for `next`,
    the first observation of the following month."""
    rows = list(station["days"]) + [station["next"]]
    return list(enumerate(rows, start=1))


def in_month(by_day, days):
    """Only the readings credited to one of the month's days (3.4)."""
    return {day: value for day, value in by_day.items() if 1 <= day <= days}


def credit_temperatures(station, days):
    """The maxima and minima credited to the month's days, each as {day: tenths}.

    A maximum read at a morning observation belongs to the day before its form day (3.1); a minimum
    belongs to its form day at every observation hour (3.2)."""
    shift = 1 if morning(station["hour"]) else 0
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

    A day's precipitation (2.4) is credited as a day's maximum is (3.3): to the day before its form
    day at a morning observation, and to its form day at an afternoon observation. An accumulated
    amount (1.3) holds two or more observation days, so it is not a day's precipitation and no rule
    of the handbook credits it; it keeps the day the package has always credited it to, its form
    day."""
    shift = 1 if morning(station["hour"]) else 0
    totals = {}
    previous = None
    for day, entry in form_rows(station):
        text = entry["precip"]
        amount = hundredths(text)
        if amount is None:
            previous = text
            continue
        accumulated = previous == UNREAD and text != TRACE
        credited = day if accumulated else day - shift
        totals[credited] = totals.get(credited, 0) + amount
        previous = text
    return in_month(totals, days)
