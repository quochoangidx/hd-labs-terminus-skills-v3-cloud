"""Method-blank level (SOP section 4)."""


def blank_level(runs, analyte, readings, mdl):
    """Blank level of one analyte; readings maps run id to its reading.

    The mean of the batch's method-blank results, that is of the readings of
    every blank of the batch, wherever it sits in the run order, that are at or
    above the analyte's ``mdl`` (SOP sections 3 and 4).  When the batch holds no
    such result the SOP defines no blank level and the level stays 0.0.
    """
    results = [
        readings[run["id"]]
        for run in runs
        if run["kind"] == "blank" and readings[run["id"]] >= mdl
    ]
    if not results:
        return 0.0
    return sum(results) / len(results)
