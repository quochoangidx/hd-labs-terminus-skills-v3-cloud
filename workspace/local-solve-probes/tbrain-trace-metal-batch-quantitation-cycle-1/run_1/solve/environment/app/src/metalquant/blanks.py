"""Method-blank level (SOP section 4)."""


def blank_level(runs, analyte, readings, mdl):
    """Blank level of one analyte; readings maps run id to its reading.

    The mean of every method-blank result (reading at or above the mdl).
    With no blank result the SOP gives no rule, so the previous calculation
    is kept: the first blank's reading, or 0.0 when the batch has no blank.
    """
    blank_readings = [readings[run["id"]] for run in runs if run["kind"] == "blank"]
    results = [value for value in blank_readings if value >= mdl]
    if results:
        return sum(results) / len(results)
    if blank_readings:
        return blank_readings[0]
    return 0.0
