"""CCV checks, bracketing and spike recovery (SOP sections 6 and 7)."""


def ccv_recovery(reading, true):
    return reading / true * 100.0


def ccv_passes(recovery):
    """The CCV passes when the recovery, rounded to one decimal, is 90.0-110.0."""
    rounded = round(recovery, 1)
    return 90.0 <= rounded <= 110.0


def bracket_ok(runs, index, ccv_pass):
    """ccv_pass maps a CCV run id to whether it passed for the analyte.

    A run with a CCV both before and after it is bracketed by the nearest CCV on
    each side and is ok only when both passed (SOP section 6).
    """
    before_pass = None
    for before in range(index - 1, -1, -1):
        if runs[before]["kind"] == "ccv":
            before_pass = ccv_pass[runs[before]["id"]]
            break
    after_pass = None
    for after in range(index + 1, len(runs)):
        if runs[after]["kind"] == "ccv":
            after_pass = ccv_pass[runs[after]["id"]]
            break
    if before_pass is not None and after_pass is not None:
        return before_pass and after_pass
    if before_pass is not None:
        return before_pass
    return True


def spike_recovery(spike_amount, parent_amount, added):
    """Spike recovery as a percentage of the amount added (SOP section 7)."""
    return (spike_amount - parent_amount) / added * 100.0
