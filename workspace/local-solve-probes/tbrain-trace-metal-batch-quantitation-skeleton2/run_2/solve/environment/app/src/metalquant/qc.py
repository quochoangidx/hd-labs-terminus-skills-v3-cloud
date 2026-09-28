"""CCV checks, bracketing and spike recovery (SOP sections 6 and 7)."""


def ccv_recovery(reading, true):
    return reading / true * 100.0


def ccv_passes(recovery):
    return 90.0 <= round(recovery, 1) <= 110.0


def bracket_ok(runs, index, ccv_pass):
    """ccv_pass maps a CCV run id to whether it passed for the analyte."""
    previous = None
    for before in range(index - 1, -1, -1):
        if runs[before]["kind"] == "ccv":
            previous = runs[before]["id"]
            break
    following = None
    for after in range(index + 1, len(runs)):
        if runs[after]["kind"] == "ccv":
            following = runs[after]["id"]
            break
    if previous is not None and following is not None:
        return ccv_pass[previous] and ccv_pass[following]
    if previous is not None:
        return ccv_pass[previous]
    return True


def spike_recovery(spike_amount, parent_amount, added):
    return (spike_amount - parent_amount) / added * 100.0
