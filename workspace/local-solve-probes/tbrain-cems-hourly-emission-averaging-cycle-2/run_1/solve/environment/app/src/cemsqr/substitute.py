"""Figures for operating hours that are not valid."""

from .rounding import half_up, mean


def fill(hours):
    """Give every operating hour that is not valid its reported figures."""
    operating = [hour for hour in hours if hour["operating"]]
    before = [None] * len(operating)
    after = [None] * len(operating)
    seen = None
    for index, hour in enumerate(operating):
        before[index] = seen
        if hour["valid"]:
            seen = index
    seen = None
    for index in range(len(operating) - 1, -1, -1):
        after[index] = seen
        if operating[index]["valid"]:
            seen = index
    carried = (0, 0)
    for index, hour in enumerate(operating):
        if not hour["valid"]:
            if hour["lost"]:
                past, ahead = before[index], after[index]
                if past is not None and ahead is not None:
                    hour["conc"] = half_up(
                        mean([operating[past]["conc"], operating[ahead]["conc"]]))
                    hour["rate"] = half_up(
                        mean([operating[past]["rate"], operating[ahead]["rate"]]))
                elif past is not None:
                    hour["conc"] = operating[past]["conc"]
                    hour["rate"] = operating[past]["rate"]
                elif ahead is not None:
                    hour["conc"] = operating[ahead]["conc"]
                    hour["rate"] = operating[ahead]["rate"]
                else:
                    hour["conc"], hour["rate"] = 0, 0
            else:
                # No rule settles a substitute hour that is not a lost hour, so
                # it keeps the figures the package carried forward today.
                hour["conc"], hour["rate"] = carried
        carried = (hour["conc"], hour["rate"])
    return hours
