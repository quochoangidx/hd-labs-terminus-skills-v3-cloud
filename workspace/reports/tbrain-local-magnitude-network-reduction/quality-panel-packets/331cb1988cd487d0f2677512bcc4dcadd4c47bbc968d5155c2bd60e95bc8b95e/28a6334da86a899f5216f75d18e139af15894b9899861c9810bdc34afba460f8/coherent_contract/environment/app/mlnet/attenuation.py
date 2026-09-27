"""Distance correction -log A0 for the network's local magnitude."""

import math

# The network's 2019 calibration: (distance in km, -log A0).
CALIBRATION = (
    (10.0, 1.700),
    (20.0, 2.060),
    (30.0, 2.290),
    (50.0, 2.580),
    (75.0, 2.820),
    (100.0, 3.000),
    (150.0, 3.300),
    (200.0, 3.530),
    (300.0, 3.900),
    (400.0, 4.220),
    (500.0, 4.510),
    (600.0, 4.790),
)


def _segment(distance_km):
    """Index of the calibration segment used for ``distance_km``."""
    last = len(CALIBRATION) - 2
    for index in range(last):
        if distance_km <= CALIBRATION[index + 1][0]:
            return index
    return last


def minus_log_a0(distance_km):
    """Distance correction -log A0 at ``distance_km`` kilometres."""
    index = _segment(distance_km)
    (near_km, near_value), (far_km, far_value) = CALIBRATION[index], CALIBRATION[index + 1]
    x = math.log10(distance_km)
    x_near = math.log10(near_km)
    x_far = math.log10(far_km)
    return near_value + (far_value - near_value) * (x - x_near) / (x_far - x_near)
