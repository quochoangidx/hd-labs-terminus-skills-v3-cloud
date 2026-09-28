"""Method-blank level (SOP section 4)."""


def blank_level(runs, analyte, readings, mdl):
    """Blank level of one analyte; readings maps run id to its reading.

    The mean of the batch's method-blank results, that is of the readings of
    every blank of the batch, wherever it sits in the run order, that are at or
    above the analyte's `mdl` (SOP 3 and 4). With no such result the SOP gives
    no rule, and no blank correction is made.
    """
    results = [
        readings[run["id"]]
        for run in runs
        if run["kind"] == "blank" and readings[run["id"]] >= mdl
    ]
    if not results:
        return 0.0
    return sum(results) / len(results)
