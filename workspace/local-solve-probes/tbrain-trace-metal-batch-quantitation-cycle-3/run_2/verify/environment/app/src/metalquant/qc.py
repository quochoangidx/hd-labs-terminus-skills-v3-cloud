"""CCV checks, bracketing and spike recovery (SOP sections 6 and 7)."""


def ccv_recovery(reading, true):
    return reading / true * 100.0


def ccv_passes(recovery):
    """The CCV passes when the recovery, rounded to one decimal, is 90.0-110.0."""
    rounded = round(recovery, 1)
    return 90.0 <= rounded <= 110.0


def bracket_ok(runs, index, ccv_pass):
    """ccv_pass maps a CCV run id to whether it passed for the analyte.

    A run bracketed by a CCV on each side is qualified by the nearest CCV
    before it and the nearest one after it (SOP section 6); a run that is not
    bracketed carries no such qualification.
    """
    before = None
    for i in range(index - 1, -1, -1):
        if runs[i]["kind"] == "ccv":
            before = runs[i]["id"]
            break
    after = None
    for i in range(index + 1, len(runs)):
        if runs[i]["kind"] == "ccv":
            after = runs[i]["id"]
            break
    if before is None or after is None:
        return True
    return ccv_pass[before] and ccv_pass[after]


def spike_recovery(spike_amount, parent_amount, added):
    """Spike recovery as a percentage of the amount added (SOP section 7)."""
    return (spike_amount - parent_amount) / added * 100.0
