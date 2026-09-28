"""CCV checks, bracketing and spike recovery (SOP sections 6 and 7)."""


def ccv_recovery(reading, true):
    return reading / true * 100.0


def ccv_passes(recovery):
    """The CCV passes when the recovery, rounded to one decimal, is 90.0-110.0."""
    rounded = round(recovery, 1)
    return 90.0 <= rounded <= 110.0


def bracket_ok(runs, index, ccv_pass):
    """ccv_pass maps a CCV run id to whether it passed for the analyte.

    A run with a CCV both before it and after it is bracketed by the nearest
    CCV on each side, and is ok only when both passed (SOP section 6). The SOP
    gives no rule for a run that is not bracketed, so the nearest preceding
    CCV, if any, decides it as before.
    """
    before_id = None
    for position in range(index - 1, -1, -1):
        if runs[position]["kind"] == "ccv":
            before_id = runs[position]["id"]
            break
    after_id = None
    for position in range(index + 1, len(runs)):
        if runs[position]["kind"] == "ccv":
            after_id = runs[position]["id"]
            break
    if before_id is None:
        return True
    if after_id is None:
        return ccv_pass[before_id]
    return ccv_pass[before_id] and ccv_pass[after_id]


def spike_recovery(spike_amount, parent_amount, added):
    """The spike amount less the parent's, as a percentage of the amount added."""
    return (spike_amount - parent_amount) / added * 100.0
