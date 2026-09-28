"""Figures for operating hours that are not valid."""

from fractions import Fraction

from .rounding import half_up


def _reported(hour):
    return (hour["conc"], hour["rate"])


def fill(hours):
    """Give every operating hour that is not valid its reported figures."""
    operating = [hour for hour in hours if hour["operating"]]
    last = (0, 0)
    for index, hour in enumerate(operating):
        if not hour["valid"]:
            if hour["lost"]:
                hour["conc"], hour["rate"] = _bracket(operating, index)
            else:
                hour["conc"], hour["rate"] = last
        last = _reported(hour)
    return hours


def _bracket(operating, index):
    """Rules 4.2 and 4.3: a lost hour's figures from the valid hours around it."""
    before = None
    for hour in reversed(operating[:index]):
        if hour["valid"]:
            before = _reported(hour)
            break
    after = None
    for hour in operating[index + 1:]:
        if hour["valid"]:
            after = _reported(hour)
            break
    if before is not None and after is not None:
        return tuple(half_up(Fraction(one + other, 2))
                     for one, other in zip(before, after))
    if before is not None:
        return before
    if after is not None:
        return after
    return (0, 0)
