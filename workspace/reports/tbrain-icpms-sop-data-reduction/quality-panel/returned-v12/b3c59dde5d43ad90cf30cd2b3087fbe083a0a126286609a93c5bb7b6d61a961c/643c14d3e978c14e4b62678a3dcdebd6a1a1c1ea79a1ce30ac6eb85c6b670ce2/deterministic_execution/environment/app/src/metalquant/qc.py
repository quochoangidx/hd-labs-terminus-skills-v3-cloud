"""CCV checks, bracketing and spike recovery (SOP sections 6 and 7)."""


def ccv_recovery(reading, true):
    return reading / true * 100.0


def ccv_passes(recovery):
    return 90.0 < recovery < 110.0


def bracket_ok(runs, index, ccv_pass):
    """ccv_pass maps a CCV run id to whether it passed for the analyte."""
    for before in range(index - 1, -1, -1):
        if runs[before]["kind"] == "ccv":
            return ccv_pass[runs[before]["id"]]
    return True


def spike_recovery(spike_amount, parent_amount, added, dilution):
    return (spike_amount - parent_amount) / (added * dilution) * 100.0
