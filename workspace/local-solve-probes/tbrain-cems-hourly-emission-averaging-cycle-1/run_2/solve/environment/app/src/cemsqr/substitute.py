"""Figures for operating hours that are not valid."""

from fractions import Fraction

from .rounding import half_up


def fill(hours):
    """Give every operating hour that is not valid its reported figures."""
    operating = [hour for hour in hours if hour["operating"]]
    # The reported figures of the nearest valid hour on either side (4.2, 4.3).
    before = [None] * len(operating)
    after = [None] * len(operating)
    seen = None
    for index, hour in enumerate(operating):
        before[index] = seen
        if hour["valid"]:
            seen = (hour["conc"], hour["rate"])
    seen = None
    for index in range(len(operating) - 1, -1, -1):
        after[index] = seen
        if operating[index]["valid"]:
            seen = (operating[index]["conc"], operating[index]["rate"])
    for index, hour in enumerate(operating):
        if hour["valid"]:
            continue
        if hour["lost"]:
            sides = [side for side in (before[index], after[index]) if side is not None]
            if not sides:
                hour["conc"], hour["rate"] = 0, 0
            elif len(sides) == 1:
                hour["conc"], hour["rate"] = sides[0]
            else:
                hour["conc"] = half_up(Fraction(sides[0][0] + sides[1][0], 2))
                hour["rate"] = half_up(Fraction(sides[0][1] + sides[1][1], 2))
        else:
            # No rule settles an hour that holds a valid reading yet is not a
            # valid hour: the package's own carry-forward stands.
            carried = before[index]
            hour["conc"], hour["rate"] = carried if carried is not None else (0, 0)
    return hours
