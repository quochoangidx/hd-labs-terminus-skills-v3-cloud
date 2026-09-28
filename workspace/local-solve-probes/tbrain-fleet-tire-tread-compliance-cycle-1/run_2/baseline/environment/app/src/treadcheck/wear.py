"""Tread worn and wear rate of a tire."""

from . import rounding

PER_KM = 10000  # wear rates are tenths per 10,000 km


def tread_worn(tire, depths):
    """(tread worn in tenths, distance in km it was worn over)."""
    readings = tire["readings"]
    worn = depths[0] - depths[-1]
    distance = readings[-1][1] - readings[0][1]
    return worn, distance


def wear_rate(worn, distance):
    """Tenths worn per 10,000 km."""
    return rounding.divide(worn * PER_KM, distance)
