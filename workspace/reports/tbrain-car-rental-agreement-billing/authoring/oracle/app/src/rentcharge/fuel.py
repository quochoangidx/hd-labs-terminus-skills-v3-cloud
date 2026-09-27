"""The fuel charge."""


REFUELLING_FEE = 1500


def fuel_charge(agreement):
    short = agreement["fuel_out"] - agreement["fuel_in"]
    if short > 0:
        return short * agreement["fuel_rate"] + REFUELLING_FEE
    return short * agreement["fuel_rate"]
