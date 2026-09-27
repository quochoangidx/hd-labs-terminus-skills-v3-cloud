"""Miles driven and the mileage charge."""

from .time_charge import days

MILES_PER_DAY = 150
ODOMETER_TURNOVER = 1000000


def miles(agreement):
    """The miles driven (manual RC-3 rule 2.4), allowing for turnover."""
    driven = agreement["odometer_in"] - agreement["odometer_out"]
    if agreement["odometer_in"] < agreement["odometer_out"]:
        driven += ODOMETER_TURNOVER
    return driven


def mileage_charge(agreement):
    allowance = MILES_PER_DAY * days(agreement)
    return max(0, miles(agreement) - allowance) * agreement["mile_rate"]
