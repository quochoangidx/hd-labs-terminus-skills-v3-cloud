"""CCV checks, bracketing and spike recovery (SOP sections 6 and 7)."""


def ccv_recovery(reading, true):
    return reading / true * 100.0


def ccv_passes(recovery):
    """The CCV passes when the recovery, rounded to one decimal, is 90.0 to 110.0."""
    rounded = round(recovery, 1)
    return 90.0 <= rounded <= 110.0


def bracket_ok(runs, index, ccv_pass):
    """ccv_pass maps a CCV run id to whether it passed for the analyte.

    A run with a CCV both before and after it is bracketed by the nearest CCV
    on each side and is ok only when both passed (SOP 6).  For a run the SOP
    does not bracket the package's own value is kept.
    """
    before = None
    for position in range(index - 1, -1, -1):
        if runs[position]["kind"] == "ccv":
            before = runs[position]["id"]
            break
    after = None
    for position in range(index + 1, len(runs)):
        if runs[position]["kind"] == "ccv":
            after = runs[position]["id"]
            break
    if before is not None and after is not None:
        return ccv_pass[before] and ccv_pass[after]
    if before is not None:
        return ccv_pass[before]
    return True


def spike_recovery(spike_amount, parent_amount, added):
    """The spike's amount less its parent's, as a percentage of the amount added."""
    return (spike_amount - parent_amount) / added * 100.0
