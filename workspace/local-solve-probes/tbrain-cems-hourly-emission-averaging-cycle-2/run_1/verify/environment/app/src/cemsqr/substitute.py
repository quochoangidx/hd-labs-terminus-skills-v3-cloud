"""Figures for operating hours that are not valid."""


def fill(hours):
    """Give every operating hour that is not valid its reported figures."""
    last = (0, 0)
    for hour in hours:
        if not hour["operating"]:
            continue
        if not hour["valid"]:
            hour["conc"], hour["rate"] = last
        last = (hour["conc"], hour["rate"])
    return hours
