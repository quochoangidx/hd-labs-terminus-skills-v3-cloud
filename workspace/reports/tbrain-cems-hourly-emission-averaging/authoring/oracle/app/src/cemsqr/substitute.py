"""Figures for operating hours that are not valid."""

from .rounding import half_up, mean


def fill(hours):
    """Give every operating hour that is not valid its reported figures."""
    last = (0, 0)
    operating = [hour for hour in hours if hour["operating"]]
    valid = [k for k, hour in enumerate(operating) if hour["valid"]]
    for k, hour in enumerate(operating):
        if hour["lost"]:  # DRP-4 2.5, 4.2, 4.3
            before = [operating[j] for j in valid if j < k][-1:]
            after = [operating[j] for j in valid if j > k][:1]
            sides = before + after
            if not sides:
                hour["conc"], hour["rate"] = 0, 0
            else:
                hour["conc"] = half_up(mean(side["conc"] for side in sides))
                hour["rate"] = half_up(mean(side["rate"] for side in sides))
        elif not hour["valid"]:
            hour["conc"], hour["rate"] = last
        last = (hour["conc"], hour["rate"])
    return hours
