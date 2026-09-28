"""Method-blank level (SOP section 4)."""


def blank_level(runs, analyte, readings, mdl):
    """Blank level of one analyte; readings maps run id to its reading.

    The mean of the method-blank results (readings at or above the mdl) of the
    batch, wherever the blanks sit in the run order.
    """
    results = [
        readings[run["id"]]
        for run in runs
        if run["kind"] == "blank" and readings[run["id"]] >= mdl
    ]
    if not results:
        return 0.0
    return sum(results) / len(results)
