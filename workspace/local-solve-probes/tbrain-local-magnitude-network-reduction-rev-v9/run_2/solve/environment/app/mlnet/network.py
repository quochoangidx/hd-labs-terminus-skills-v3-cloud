"""Network magnitude of an event from its station magnitudes."""

from .attenuation import FARTHEST_KM, NEAREST_KM

# Fewest contributing stations an event needs for a network magnitude (rule 5.3).
LEAST_STATIONS = 3


def contributes(distance_km):
    """Whether a station at ``distance_km`` counts toward the network magnitude.

    A station contributes when its distance lies within the calibration table,
    from 10 km to 600 km, both ends included (rule 5.1).
    """
    return NEAREST_KM <= float(distance_km) <= FARTHEST_KM


def network_magnitude(station_magnitudes):
    """Network local magnitude from the contributing stations' magnitudes.

    The median of the station magnitudes: the middle one of an odd number of
    them, the mean of the two middle ones of an even number (rule 5.2).  An
    event with fewer than three contributing stations has no network magnitude
    (rule 5.3), and ``None`` is returned for it.
    """
    values = sorted(float(value) for value in station_magnitudes)
    if len(values) < LEAST_STATIONS:
        return None
    middle = len(values) // 2
    if len(values) % 2:
        return values[middle]
    return (values[middle - 1] + values[middle]) / 2.0
