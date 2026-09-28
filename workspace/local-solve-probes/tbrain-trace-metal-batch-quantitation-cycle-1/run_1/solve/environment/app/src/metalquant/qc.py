"""CCV checks, bracketing and spike recovery (SOP sections 6 and 7)."""


def ccv_recovery(reading, true):
    return reading / true * 100.0


def ccv_passes(recovery):
    rounded = round(recovery, 1)
    return 90.0 <= rounded <= 110.0


def bracket_ok(runs, index, ccv_pass):
    """ccv_pass maps a CCV run id to whether it passed for the analyte."""
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
    if before is not None and after is not None:
        return ccv_pass[before] and ccv_pass[after]
    # Not bracketed: the SOP gives no rule, keep the previous calculation.
    if before is not None:
        return ccv_pass[before]
    return True


def spike_recovery(spike_amount, parent_amount, added, dilution, both_results=True):
    if both_results:
        return (spike_amount - parent_amount) / added * 100.0
    # A non-detect has no result: the SOP gives no rule, keep the previous calculation.
    return (spike_amount - parent_amount) / (added * dilution) * 100.0
