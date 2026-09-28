"""Miles driven and the mileage charge."""

from .time_charge import days

MILES_PER_DAY = 100


def miles(agreement):
    return agreement["odometer_in"] - agreement["odometer_out"]


def mileage_charge(agreement):
    allowance = MILES_PER_DAY * days(agreement)
    return max(0, miles(agreement) - allowance) * agreement["mile_rate"]
