"""Count tolerances."""

TOLERANCE_PERCENT = 5


def tolerance(line):
    """The units a count may be off before it is questioned."""
    return round(line["system"] * TOLERANCE_PERCENT / 100)


def within(line, off):
    return abs(off) <= tolerance(line)
