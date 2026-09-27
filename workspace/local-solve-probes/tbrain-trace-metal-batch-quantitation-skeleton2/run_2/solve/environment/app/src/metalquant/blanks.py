"""Method-blank level (SOP section 4)."""


def blank_level(runs, analyte, readings, mdl):
    """Blank level of one analyte; readings maps run id to its reading.

    The mean of every method-blank result (reading at or above the mdl).
    The SOP gives no rule when the batch has no blank result; the
    earlier calculation (first blank's reading, or 0.0) is kept then.
    """
    results = [
        readings[run["id"]]
        for run in runs
        if run["kind"] == "blank" and readings[run["id"]] >= mdl
    ]
    if results:
        return sum(results) / len(results)
    for run in runs:
        if run["kind"] == "blank":
            return readings[run["id"]]
    return 0.0
