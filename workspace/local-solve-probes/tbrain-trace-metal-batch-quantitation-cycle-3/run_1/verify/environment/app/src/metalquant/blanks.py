"""Method-blank level (SOP section 4)."""


def blank_level(runs, analyte, readings):
    """Blank level of one analyte; readings maps run id to its reading.

    The mean of the batch's method-blank results, that is the readings of the
    blanks that are at or above the analyte's `mdl`, taking every blank of the
    batch wherever it sits in the run order.  When the batch has no method-blank
    result the SOP defines no level and the level stays nought.
    """
    mdl = analyte["mdl"]
    results = [
        readings[run["id"]]
        for run in runs
        if run["kind"] == "blank" and readings[run["id"]] >= mdl
    ]
    if not results:
        return 0.0
    return sum(results) / len(results)
