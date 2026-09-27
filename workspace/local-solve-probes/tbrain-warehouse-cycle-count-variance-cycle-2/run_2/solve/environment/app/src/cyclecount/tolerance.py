"""Count tolerances."""

TOLERANCE_PERCENT = 5

# Rule 2.3: the tolerance of a graded item, as a percentage of its system
# quantity.  Class A is graded to nought units.
GRADED_PERCENT = {"A": 0, "B": 2, "C": 5}


def tolerance(line):
    """The units a count may be off before it is questioned."""
    percent = GRADED_PERCENT.get(line["class"])
    if percent is None:
        # Not a graded item: the procedure gives no tolerance for it.
        return round(line["system"] * TOLERANCE_PERCENT / 100)
    # Rule 2.3 with rule 1.2: a whole number of units, fraction dropped.
    return line["system"] * percent // 100


def within(line, off):
    """Rule 2.4."""
    return abs(off) <= tolerance(line)
