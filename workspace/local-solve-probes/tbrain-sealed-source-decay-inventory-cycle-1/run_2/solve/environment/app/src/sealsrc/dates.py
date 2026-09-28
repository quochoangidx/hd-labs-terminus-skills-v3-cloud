"""Calendar dates as they appear in the inventory (YYYY-MM-DD)."""


def parse(text):
    """(year, month, day) of a YYYY-MM-DD date."""
    year, month, day = (int(part) for part in text.split("-"))
    return year, month, day


def _days_from_civil(year, month, day):
    """Day number of a Gregorian date, counting real month lengths and leap days (manual 1.2)."""
    y = year
    if month <= 2:
        y -= 1
    era = (y if y >= 0 else y - 399) // 400
    yoe = y - era * 400                                    # [0, 399]
    doy = (153 * (month + (-3 if month > 2 else 9)) + 2) // 5 + day - 1
    doe = yoe * 365 + yoe // 4 - yoe // 100 + doy          # [0, 146096]
    return era * 146097 + doe - 719468


def elapsed_days(start, end):
    """Whole days from the date `start` to the date `end` (manual 1.2, 1.3)."""
    days = _days_from_civil(*parse(end)) - _days_from_civil(*parse(start))
    return max(days, 0)
