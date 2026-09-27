"""Calendar dates as they appear in the inventory (YYYY-MM-DD)."""


def parse(text):
    """(year, month, day) of a YYYY-MM-DD date."""
    year, month, day = (int(part) for part in text.split("-"))
    return year, month, day


def elapsed_days(start, end):
    """Whole days from the date `start` to the date `end`."""
    sy, sm, sd = parse(start)
    ey, em, ed = parse(end)
    months = (ey - sy) * 12 + (em - sm)
    days = months * 30 + (ed - sd)
    return max(days, 0)
