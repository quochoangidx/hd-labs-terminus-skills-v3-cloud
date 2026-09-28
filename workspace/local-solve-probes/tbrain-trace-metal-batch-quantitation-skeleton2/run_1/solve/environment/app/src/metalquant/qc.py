"""CCV checks, bracketing and spike recovery (SOP sections 6 and 7)."""


def ccv_recovery(reading, true):
    return reading / true * 100.0


def ccv_passes(recovery):
    return 90.0 <= round(recovery, 1) <= 110.0


def bracket_ok(runs, index, ccv_pass):
    """ccv_pass maps a CCV run id to whether it passed for the analyte."""
    before_id = None
    for before in range(index - 1, -1, -1):
        if runs[before]["kind"] == "ccv":
            before_id = runs[before]["id"]
            break
    if before_id is None:
        return True
    after_id = None
    for after in range(index + 1, len(runs)):
        if runs[after]["kind"] == "ccv":
            after_id = runs[after]["id"]
            break
    if after_id is None:
        return ccv_pass[before_id]
    return ccv_pass[before_id] and ccv_pass[after_id]


def spike_recovery(spike_amount, parent_amount, added, dilution):
    return (spike_amount - parent_amount) / added * 100.0
