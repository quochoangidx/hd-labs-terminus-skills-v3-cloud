"""Count tolerances."""

TOLERANCE_PERCENT = 5
GRADED_PERCENT = {"A": 0, "B": 2, "C": 5}


def tolerance(line):
    """The units a count may be off before it is questioned."""
    if line["class"] in GRADED_PERCENT:
        return line["system"] * GRADED_PERCENT[line["class"]] // 100
    return round(line["system"] * TOLERANCE_PERCENT / 100)


def within(line, off):
    return abs(off) <= tolerance(line)
