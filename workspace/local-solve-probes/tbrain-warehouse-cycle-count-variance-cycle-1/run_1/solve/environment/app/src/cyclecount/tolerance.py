"""Count tolerances."""

TOLERANCE_PERCENT = 5

# Rule 2.3: the tolerance of a graded item, as a percentage of the system
# quantity.  Class A is nought units.
GRADED_PERCENT = {"A": 0, "B": 2, "C": 5}


def tolerance(line):
    """The units a count may be off before it is questioned."""
    percent = GRADED_PERCENT.get(line["class"])
    if percent is None:
        # Not a graded item: the procedure gives no tolerance for it, so the
        # package works it out the way it always has.
        return round(line["system"] * TOLERANCE_PERCENT / 100)
    # A whole number of units, any fraction of a unit dropped.
    return line["system"] * percent // 100


def within(line, off):
    """Rule 2.4."""
    return abs(off) <= tolerance(line)
