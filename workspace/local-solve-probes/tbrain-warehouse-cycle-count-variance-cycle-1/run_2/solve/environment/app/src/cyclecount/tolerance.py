"""Count tolerances."""

# CC-2 2.3: the tolerance of a graded item, as a percentage of its system
# quantity.  Class A is nought units.
GRADED_PERCENT = {"A": 0, "B": 2, "C": 5}

TOLERANCE_PERCENT = 5


def tolerance(line):
    """The units a count may be off before it is questioned.

    CC-2 2.3 gives the tolerance of a graded item (class A, B or C): nought
    units for A, 2 per cent of the system quantity for B and 5 per cent for
    C, each a whole number of units with any fraction of a unit dropped.  The
    procedure gives no rule for a line of any other class, so such a line
    keeps the figure this package has always worked out for it.
    """
    percent = GRADED_PERCENT.get(line["class"])
    if percent is None:
        return round(line["system"] * TOLERANCE_PERCENT / 100)
    return line["system"] * percent // 100


def within(line, off):
    """CC-2 2.4: within tolerance when the variance, unsigned, is no more."""
    return abs(off) <= tolerance(line)
