"""CCV checks, bracketing and spike recovery (SOP sections 6 and 7)."""


def ccv_recovery(reading, true):
    return reading / true * 100.0


def ccv_passes(recovery):
    return 90.0 <= round(recovery, 1) <= 110.0


def bracket_ok(runs, index, ccv_pass):
    """ccv_pass maps a CCV run id to whether it passed for the analyte.

    A run with a CCV both before and after it is bracketed by the nearest CCV
    on each side and is ok only when both passed (SOP section 6). For a run
    that is not bracketed the SOP defines no value and the historic
    calculation is kept: the nearest earlier CCV, or true when there is none.
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
    if before_id is not None and after_id is not None:
        return ccv_pass[before_id] and ccv_pass[after_id]
    if before_id is not None:
        return ccv_pass[before_id]
    return True


def spike_recovery(spike_amount, parent_amount, added):
    return (spike_amount - parent_amount) / added * 100.0
