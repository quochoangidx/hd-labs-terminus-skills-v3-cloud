"""Network magnitude of an event from its station magnitudes."""

from .attenuation import TABLE_FARTHEST_KM, TABLE_NEAREST_KM, in_table

NEAREST_KM = TABLE_NEAREST_KM
FARTHEST_KM = TABLE_FARTHEST_KM

# Rule 5.3: fewer contributing stations than this give no network magnitude.
LEAST_STATIONS = 3


def contributes(distance_km):
    """Whether a station at ``distance_km`` counts toward the network magnitude.

    Rule 5.1: its distance must lie within the calibration table, from 10 km to
    600 km, both ends included.
    """
    return in_table(distance_km)


def network_magnitude(station_magnitudes):
    """Network local magnitude from the contributing stations' magnitudes.

    Rule 5.2: the median of the station magnitudes, one value per contributing
    station -- the middle one of an odd number, the mean of the two middle ones
    of an even number.  Returns ``None`` when no magnitude can be formed
    (rule 5.3).
    """
    values = sorted(float(value) for value in station_magnitudes)
    if len(values) < LEAST_STATIONS:
        return None
    middle = len(values) // 2
    if len(values) % 2:
        return values[middle]
    return (values[middle - 1] + values[middle]) / 2.0
