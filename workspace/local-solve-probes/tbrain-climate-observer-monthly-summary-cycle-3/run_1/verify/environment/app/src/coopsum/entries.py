"""The observer's entries as whole numbers: temperatures in tenths of a degree, precipitation in
hundredths of an inch, and the month's calendar."""

import calendar

MISSING = "M"
UNREAD = "A"
TRACE = "T"


def tenths(text):
    """A temperature entry ("71.3", "-4.0") as whole tenths of a degree, or None for M."""
    if text == MISSING:
        return None
    sign = -1 if text.startswith("-") else 1
    whole, _, frac = text.lstrip("-").partition(".")
    return sign * (int(whole) * 10 + int(frac))


def hundredths(text):
    """A precipitation entry ("0.37", "T") as whole hundredths of an inch; None when the entry holds
    no amount (M, or A for a gauge that was not read)."""
    if text in (MISSING, UNREAD):
        return None
    if text == TRACE:
        return 1
    whole, _, frac = text.partition(".")
    return int(whole) * 100 + int(frac)


def half_up(num, den):
    """num / den to the nearest whole number, an exact half going to the higher one (den > 0)."""
    return (2 * num + den) // (2 * den)


def month_length(month):
    """The number of days in a `YYYY-MM` month."""
    year, number = (int(part) for part in month.split("-"))
    return calendar.monthrange(year, number)[1]


def day_label(month, day):
    """The `YYYY-MM-DD` label of a day of the month."""
    return f"{month}-{day:02d}"
