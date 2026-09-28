"""CCV checks, bracketing and spike recovery (SOP sections 6 and 7)."""


def ccv_recovery(reading, true):
    return reading / true * 100.0


def ccv_passes(recovery):
    """The CCV passes when the recovery, rounded to one decimal place, is from
    90.0 to 110.0 inclusive."""
    rounded = round(recovery, 1)
    return 90.0 <= rounded <= 110.0


def bracket_ok(runs, index, ccv_pass):
    """ccv_pass maps a CCV run id to whether it passed for the analyte.

    A run with a CCV both before it and after it is bracketed by the nearest
    CCV on each side and is ok only when both passed (SOP section 6).  With no
    CCV before it the run keeps the level the package has always reported, and
    with no CCV after it the nearest CCV before it decides.
    """
    before_pass = None
    for before in range(index - 1, -1, -1):
        if runs[before]["kind"] == "ccv":
            before_pass = ccv_pass[runs[before]["id"]]
            break
    if before_pass is None:
        return True
    for after in range(index + 1, len(runs)):
        if runs[after]["kind"] == "ccv":
            return before_pass and ccv_pass[runs[after]["id"]]
    return before_pass


def spike_recovery(spike_amount, parent_amount, added, dilution):
    """The spike's amount less its parent's, as a percentage of the amount added.

    Both amounts and `added` are concentrations in the sample as received, so
    the spike's dilution does not enter (SOP section 7).
    """
    return (spike_amount - parent_amount) / added * 100.0
