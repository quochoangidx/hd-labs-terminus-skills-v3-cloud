"""Room, taxes and fees."""

from .money import percent, to_cents

CITY_TAX_PER_NIGHT = 200
CITY_TAX_FREE_BELOW = 3000
OCCUPANCY_TAX_PERCENT = 12
SERVICE_FEE_PERCENT = "3.5"


def room(stay):
    return stay["nights"] * stay["rate"]


def city_tax(stay):
    if stay["rate"] < CITY_TAX_FREE_BELOW:
        return 0
    return stay["nights"] * CITY_TAX_PER_NIGHT


def occupancy_tax(room_charge):
    return to_cents(percent(room_charge, OCCUPANCY_TAX_PERCENT))


def service_fee(room_charge):
    return to_cents(percent(room_charge, SERVICE_FEE_PERCENT))
