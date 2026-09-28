"""Figures for operating hours that are not valid."""

from fractions import Fraction

from .rounding import half_up


def _neighbours(operating):
    """For each operating hour, the last valid hour before it and the first after it."""
    before = []
    seen = None
    for hour in operating:
        before.append(seen)
        if hour["valid"]:
            seen = hour
    after = [None] * len(operating)
    seen = None
    for index in range(len(operating) - 1, -1, -1):
        after[index] = seen
        if operating[index]["valid"]:
            seen = operating[index]
    return before, after


def fill(hours):
    """Give every operating hour that is not valid its reported figures."""
    operating = [hour for hour in hours if hour["operating"]]
    before, after = _neighbours(operating)
    last = (0, 0)
    for index, hour in enumerate(operating):
        if hour["valid"]:
            last = (hour["conc"], hour["rate"])
            continue
        if hour["lost"]:
            # Rules 4.2 and 4.3.
            earlier, later = before[index], after[index]
            if earlier is not None and later is not None:
                hour["conc"] = half_up(Fraction(earlier["conc"] + later["conc"], 2))
                hour["rate"] = half_up(Fraction(earlier["rate"] + later["rate"], 2))
            elif earlier is not None:
                hour["conc"], hour["rate"] = earlier["conc"], earlier["rate"]
            elif later is not None:
                hour["conc"], hour["rate"] = later["conc"], later["rate"]
            else:
                hour["conc"], hour["rate"] = 0, 0
        else:
            hour["conc"], hour["rate"] = last
    return hours
