"""Method-blank level (SOP section 4)."""


def blank_level(runs, analyte, readings, mdl):
    """Blank level of one analyte; readings maps run id to its reading.

    The mean of the batch's method-blank results, taking every blank of the
    batch wherever it sits in the run order. A blank is judged on its reading:
    it is a result when that reading is at or above the analyte's `mdl`.
    """
    values = [
        readings[run["id"]]
        for run in runs
        if run["kind"] == "blank" and readings[run["id"]] >= mdl
    ]
    if not values:
        return 0.0
    return sum(values) / len(values)
