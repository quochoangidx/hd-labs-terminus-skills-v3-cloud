"""Count tolerances."""

# CC-2 rule 2.3: the tolerance of a graded item, per class, as a percentage of
# its system quantity.
GRADED_PERCENT = {"A": 0, "B": 2, "C": 5}

# Classes the procedure gives no tolerance rule for keep the figure the package
# has always worked out for them.
TOLERANCE_PERCENT = 5


def tolerance(line):
    """The units a count may be off before it is questioned."""
    percent = GRADED_PERCENT.get(line["class"])
    if percent is None:
        return round(line["system"] * TOLERANCE_PERCENT / 100)
    # A whole number of units, any fraction of a unit dropped (CC-2 2.3).
    return line["system"] * percent // 100


def within(line, off):
    """Whether the line is within tolerance (CC-2 2.4)."""
    return abs(off) <= tolerance(line)
