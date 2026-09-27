"""Network magnitude of an event from its station magnitudes."""

from .attenuation import CALIBRATION

NEAREST_KM = CALIBRATION[0][0]
FARTHEST_KM = CALIBRATION[-1][0]


def contributes(distance_km):
    """Whether a station at ``distance_km`` counts toward the network magnitude."""
    return NEAREST_KM <= distance_km <= FARTHEST_KM


def network_magnitude(station_magnitudes):
    """Network local magnitude from the contributing stations' magnitudes.

    Returns ``None`` when no magnitude can be formed.
    """
    values = [float(value) for value in station_magnitudes]
    if not values:
        return None
    return sum(values) / len(values)
