"""Room, taxes and fees."""

import math
from fractions import Fraction

from .money import percent, to_cents

CITY_TAX_PER_NIGHT = 250
CITY_TAX_MAX_NIGHTS = 14
CITY_TAX_FREE_BELOW = 3000
CITY_TAX_OLD_PER_NIGHT = 200
CITY_TAX_RULE_FROM = 5000
OCCUPANCY_TAX_PERCENT = "13.5"
FREE_NIGHT_EVERY = 7
SERVICE_FEE_PERCENT = "3.5"


def room(stay):
    return (stay["nights"] - stay["nights"] // FREE_NIGHT_EVERY) * stay["rate"]


def city_tax(stay):
    if stay["rate"] >= CITY_TAX_RULE_FROM:
        return min(stay["nights"], CITY_TAX_MAX_NIGHTS) * CITY_TAX_PER_NIGHT
    if stay["rate"] < CITY_TAX_FREE_BELOW:
        return 0
    return stay["nights"] * CITY_TAX_OLD_PER_NIGHT


def occupancy_tax(room_charge):
    tax = percent(room_charge, OCCUPANCY_TAX_PERCENT)
    return math.floor(tax + Fraction(1, 2))


def service_fee(room_charge):
    return to_cents(percent(room_charge, SERVICE_FEE_PERCENT))
