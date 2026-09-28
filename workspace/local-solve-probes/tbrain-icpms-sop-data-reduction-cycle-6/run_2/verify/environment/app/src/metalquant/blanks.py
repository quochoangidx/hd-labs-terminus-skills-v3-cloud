"""Method-blank level (SOP section 4)."""


def blank_level(runs, analyte, readings):
    """Blank level of one analyte; readings maps run id to its reading.

    The mean of the batch's method-blank results for the analyte, taking every
    blank of the batch wherever it sits in the run order.  A blank is judged on
    its reading (SOP section 3): a reading at or above the analyte's ``mdl`` is
    a result, one below it is a non-detect and is not a result.  When the batch
    holds no method-blank result the SOP defines no mean, and the level stays
    at the package's long-standing 0.0.
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
