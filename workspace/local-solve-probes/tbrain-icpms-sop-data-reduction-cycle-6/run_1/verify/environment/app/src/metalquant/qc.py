"""CCV checks, bracketing and spike recovery (SOP sections 6 and 7)."""


def ccv_recovery(reading, true):
    return reading / true * 100.0


def ccv_passes(recovery):
    """Pass when the recovery, rounded to one decimal, is 90.0 to 110.0."""
    rounded = round(recovery, 1)
    return 90.0 <= rounded <= 110.0


def bracket_ok(runs, index, ccv_pass):
    """ccv_pass maps a CCV run id to whether it passed for the analyte.

    A run with a CCV both before and after it is bracketed by the nearest CCV
    on each side and is ok only when both passed (SOP 6). For a run the SOP
    does not bracket the package keeps its earlier answer.
    """
    before = None
    for i in range(index - 1, -1, -1):
        if runs[i]["kind"] == "ccv":
            before = runs[i]["id"]
            break
    if before is None:
        return True
    after = None
    for i in range(index + 1, len(runs)):
        if runs[i]["kind"] == "ccv":
            after = runs[i]["id"]
            break
    if after is None:
        return ccv_pass[before]
    return ccv_pass[before] and ccv_pass[after]


def spike_recovery(spike_amount, parent_amount, added):
    """The added amount is already in ug/L of the sample as received (SOP 7)."""
    return (spike_amount - parent_amount) / added * 100.0
