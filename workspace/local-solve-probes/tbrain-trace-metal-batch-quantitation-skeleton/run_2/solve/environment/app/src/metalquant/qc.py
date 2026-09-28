"""CCV checks, bracketing and spike recovery (SOP sections 6 and 7)."""

from decimal import ROUND_HALF_UP, Decimal


def ccv_recovery(reading, true):
    return reading / true * 100.0


def ccv_passes(recovery):
    rounded = Decimal(repr(recovery)).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
    return Decimal("90.0") <= rounded <= Decimal("110.0")


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
    # Not bracketed: the SOP gives no rule, keep the prior calculation.
    if before is not None:
        return ccv_pass[before]
    return True


def spike_recovery(spike_amount, parent_amount, added, dilution, both_results=True):
    if both_results:
        return (spike_amount - parent_amount) / added * 100.0
    # SOP section 7 gives no rule unless both are results: keep the prior calculation.
    return (spike_amount - parent_amount) / (added * dilution) * 100.0
