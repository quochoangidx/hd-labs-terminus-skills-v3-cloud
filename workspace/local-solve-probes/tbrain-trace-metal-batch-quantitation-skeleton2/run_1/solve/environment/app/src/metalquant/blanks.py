"""Method-blank level (SOP section 4)."""


def blank_level(runs, analyte, readings, mdl):
    """Blank level of one analyte; readings maps run id to its reading.

    The mean of every method-blank result (reading at or above the mdl).
    With no blank results the SOP gives no rule, so the previous calculation
    (first blank's reading, or nought with no blank) is kept.
    """
    results = [readings[run["id"]] for run in runs if run["kind"] == "blank" and readings[run["id"]] >= mdl]
    if results:
        return sum(results) / len(results)
    for run in runs:
        if run["kind"] == "blank":
            return readings[run["id"]]
    return 0.0
