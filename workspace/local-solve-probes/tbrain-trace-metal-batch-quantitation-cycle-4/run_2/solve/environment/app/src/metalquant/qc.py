"""CCV checks, bracketing and spike recovery (SOP sections 6 and 7)."""


def ccv_recovery(reading, true):
    return reading / true * 100.0


def ccv_passes(recovery):
    return 90.0 <= round(recovery, 1) <= 110.0


def bracket_ok(runs, index, ccv_pass):
    """ccv_pass maps a CCV run id to whether it passed for the analyte."""
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
    if before is None:
        return True
    if after is None:
        return ccv_pass[before]
    return ccv_pass[before] and ccv_pass[after]


def spike_recovery(spike_amount, parent_amount, added):
    return (spike_amount - parent_amount) / added * 100.0
