"""Method-blank level (SOP section 4)."""


def blank_level(runs, analyte, readings):
    """Blank level of one analyte; readings maps run id to its reading."""
    results = [
        readings[run["id"]]
        for run in runs
        if run["kind"] == "blank" and readings[run["id"]] >= analyte["mdl"]
    ]
    if len(results) >= 2:
        return sum(results) / len(results)
    for run in runs:
        if run["kind"] == "blank":
            return readings[run["id"]]
    return 0.0
