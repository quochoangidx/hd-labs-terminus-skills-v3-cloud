"""Method-blank level (SOP section 4)."""


def blank_level(runs, analyte, readings):
    """Blank level of one analyte.

    The mean of the batch's method-blank results for the analyte, taking every
    blank wherever it sits in the run order (SOP section 4). A blank is judged
    on its reading (SOP section 3): a reading below the analyte's `mdl` is a
    non-detect and so is not a result. `analyte` is the analyte record and
    `readings` maps run id to that analyte's reading.
    """
    results = [
        readings[run["id"]]
        for run in runs
        if run["kind"] == "blank" and readings[run["id"]] >= analyte["mdl"]
    ]
    if not results:
        return 0.0
    return sum(results) / len(results)
