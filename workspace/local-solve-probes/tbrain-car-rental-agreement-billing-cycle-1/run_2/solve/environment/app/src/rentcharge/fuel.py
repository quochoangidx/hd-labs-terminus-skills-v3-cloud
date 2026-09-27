"""The fuel charge."""

REFUELLING_FEE = 1500


def eighths_short(agreement):
    """The eighths a refuelling rental came back short (manual RC-3 rule 2.5)."""
    return agreement["fuel_out"] - agreement["fuel_in"]


def fuel_charge(agreement):
    """The fuel charge (manual RC-3 rule 3.3).

    Only a rental whose car came back with fewer eighths than it went out with
    is charged for fuel: the fuel rate for each eighth short and a refuelling
    fee.
    """
    if agreement["fuel_in"] >= agreement["fuel_out"]:
        return 0
    return eighths_short(agreement) * agreement["fuel_rate"] + REFUELLING_FEE
