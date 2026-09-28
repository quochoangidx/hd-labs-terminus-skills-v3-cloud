"""Tread worn and wear rate of a tire."""

from . import rounding

PER_KM = 10000  # wear rates are tenths per 10,000 km
FRESH_BAND = 10  # tenths below the new depth that still counts as fresh


def is_fresh(tire, depths):
    """True when the first reading's depth is within 10 tenths of new (2.3)."""
    return tire["new_depth"] - depths[0] <= FRESH_BAND


def tread_worn(tire, depths):
    """(tread worn in tenths, distance in km it was worn over)."""
    readings = tire["readings"]
    if is_fresh(tire, depths):
        # 4.2: from the tread it had when new and the odometer at mounting.
        worn = tire["new_depth"] - depths[-1]
        distance = readings[-1][1] - tire["mounted_km"]
        return worn, distance
    worn = depths[0] - depths[-1]
    distance = readings[-1][1] - readings[0][1]
    return worn, distance


def wear_rate(worn, distance):
    """Tenths worn per 10,000 km (4.3)."""
    return rounding.divide(worn * PER_KM, distance)
