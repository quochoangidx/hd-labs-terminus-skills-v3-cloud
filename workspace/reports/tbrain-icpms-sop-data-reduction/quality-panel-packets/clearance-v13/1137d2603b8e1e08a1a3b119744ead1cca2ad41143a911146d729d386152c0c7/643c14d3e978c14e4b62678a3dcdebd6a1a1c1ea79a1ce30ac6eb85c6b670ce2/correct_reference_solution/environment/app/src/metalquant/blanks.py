"""Method-blank level (SOP section 4)."""


def blank_level(runs, analyte, readings):
    """Blank level of one analyte; readings maps run id to its reading."""
    for run in runs:
        if run["kind"] == "blank":
            return readings[run["id"]]
    return 0.0
