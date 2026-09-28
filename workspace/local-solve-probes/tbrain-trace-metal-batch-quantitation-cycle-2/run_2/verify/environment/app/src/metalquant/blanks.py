"""Method-blank level (SOP section 4)."""


def blank_level(runs, analyte, readings, mdl):
    """Blank level of one analyte; readings maps run id to its reading.

    The mean of the batch's method-blank results, that is of the readings of
    every blank of the batch, wherever it sits in the run order, that are at or
    above the analyte's method detection limit (SOP sections 3 and 4).

    When the batch has no method-blank result the SOP defines no blank level;
    the historic calculation is kept for that case: the first blank's reading
    if the batch has a blank at all, and nought otherwise.
    """
    results = [readings[run["id"]] for run in runs if run["kind"] == "blank" and readings[run["id"]] >= mdl]
    if results:
        return sum(results) / len(results)
    for run in runs:
        if run["kind"] == "blank":
            return readings[run["id"]]
    return 0.0
