"""Which day of the month each reading on a station's form belongs to."""

from .entries import UNREAD, hundredths, tenths

LAST_MORNING_HOUR = 11  # 2.2: an observation from hour 0 through 11 is a morning observation


def form_rows(station):
    """The station's entries with their form days: 1 to N for the month's own days, N + 1 for `next`,
    the first observation of the following month."""
    rows = list(station["days"]) + [station["next"]]
    return list(enumerate(rows, start=1))


def morning(station):
    """Whether the station's observations are morning observations (2.2)."""
    return station["hour"] <= LAST_MORNING_HOUR


def credited_day(station, form_day):
    """The day a maximum or an amount read on `form_day` is credited to (3.1, 3.3): the day before
    the form day at a morning observation, the form day itself at an afternoon observation."""
    return form_day - 1 if morning(station) else form_day


def in_month(by_day, days):
    """Only the readings credited to one of the month's days."""
    return {day: value for day, value in by_day.items() if 1 <= day <= days}


def credit_temperatures(station, days):
    """The maxima and minima credited to the month's days, each as {day: tenths}."""
    maxima, minima = {}, {}
    for form_day, entry in form_rows(station):
        high = tenths(entry["max"])
        if high is not None:
            maxima[credited_day(station, form_day)] = high
        low = tenths(entry["min"])
        if low is not None:
            minima[form_day] = low  # 3.2: a minimum is credited to its form day at every hour
    return in_month(maxima, days), in_month(minima, days)


def credit_precipitation(station, days):
    """The precipitation credited to the month's days, as {day: hundredths}.

    An amount or trace entered at the observation after the gauge was left unread is an accumulated
    amount (1.3): the catch of more than one observation day, and so not a day's precipitation (2.4).
    Rule 3.3 credits a day's precipitation, and nothing else; an accumulated amount therefore keeps
    the crediting the package has always given an entry, to the form day it is written on."""
    totals = {}
    previous = None
    for form_day, entry in form_rows(station):
        written = entry["precip"]
        amount = hundredths(written)
        if amount is not None:
            if previous == UNREAD:
                day = form_day
            else:
                day = credited_day(station, form_day)
            totals[day] = totals.get(day, 0) + amount
        previous = written
    return in_month(totals, days)
