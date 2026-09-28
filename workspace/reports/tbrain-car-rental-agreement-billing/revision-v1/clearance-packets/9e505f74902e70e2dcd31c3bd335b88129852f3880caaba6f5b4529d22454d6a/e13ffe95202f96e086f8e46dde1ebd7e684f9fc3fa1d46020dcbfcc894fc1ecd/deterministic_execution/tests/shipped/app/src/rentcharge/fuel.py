"""The fuel charge."""


def fuel_charge(agreement):
    return (agreement["fuel_out"] - agreement["fuel_in"]) * agreement["fuel_rate"]
