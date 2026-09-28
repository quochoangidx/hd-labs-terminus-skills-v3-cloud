"""Network magnitude of an event from its station magnitudes."""

from .attenuation import CALIBRATION

NEAREST_KM = CALIBRATION[0][0]
FARTHEST_KM = CALIBRATION[-1][0]

# An event with fewer than this many contributing stations has no network
# magnitude (manual, rule 5.3).
MINIMUM_STATIONS = 3


def contributes(distance_km):
    """Whether a station at ``distance_km`` counts toward the network magnitude.

    True when the distance lies within the calibration table, both ends
    included (manual, rule 5.1).
    """
    return NEAREST_KM <= float(distance_km) <= FARTHEST_KM


def network_magnitude(station_magnitudes):
    """Network local magnitude from the contributing stations' magnitudes.

    The median of the station magnitudes: the middle one of an odd number of
    them, the mean of the two middle ones of an even number (manual, rule 5.2).
    Returns ``None`` when no magnitude can be formed, that is when fewer than
    three stations contribute (rule 5.3).
    """
    values = sorted(float(value) for value in station_magnitudes)
    if len(values) < MINIMUM_STATIONS:
        return None
    middle = len(values) // 2
    if len(values) % 2:
        return values[middle]
    return (values[middle - 1] + values[middle]) / 2.0
