"""The fuel charge."""

REFUELLING_FEE = 1500


def fuel_charge(agreement):
    """The fuel charge of a refuelling rental (rules 2.5, 3.3).

    A rental refuels when its car came back with fewer eighths than it went
    out with: the fuel rate for each eighth short, plus the refuelling fee.
    Any other rental carries no fuel charge.
    """
    eighths_short = agreement["fuel_out"] - agreement["fuel_in"]
    if eighths_short <= 0:
        return 0
    return eighths_short * agreement["fuel_rate"] + REFUELLING_FEE
