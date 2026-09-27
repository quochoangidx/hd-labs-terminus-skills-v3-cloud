"""Miles driven and the mileage charge."""

from .time_charge import days

MILES_PER_ALLOWANCE_DAY = 150
TURNOVER = 1000000


def miles(agreement):
    driven = agreement["odometer_in"] - agreement["odometer_out"]
    return driven + TURNOVER if driven < 0 else driven


def mileage_charge(agreement):
    allowance = MILES_PER_ALLOWANCE_DAY * days(agreement)
    return max(0, miles(agreement) - allowance) * agreement["mile_rate"]
