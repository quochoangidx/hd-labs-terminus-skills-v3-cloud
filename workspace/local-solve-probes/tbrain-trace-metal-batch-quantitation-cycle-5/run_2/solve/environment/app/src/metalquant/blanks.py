"""Method-blank level (SOP section 4)."""


def blank_level(runs, analyte, readings):
    """Blank level of one analyte; readings maps run id to its reading.

    The mean of the batch's method-blank results, that is of the blank
    readings at or above the analyte's `mdl` (SOP 3 and 4), taking every
    blank wherever it sits in the run order.  When the batch holds no such
    result the SOP defines no blank level and the package's own value, nought,
    is kept.
    """
    mdl = analyte["mdl"]
    values = [
        readings[run["id"]]
        for run in runs
        if run["kind"] == "blank" and readings[run["id"]] >= mdl
    ]
    if not values:
        return 0.0
    return sum(values) / len(values)
