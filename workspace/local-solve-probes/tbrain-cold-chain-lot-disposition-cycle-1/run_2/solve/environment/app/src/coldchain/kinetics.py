"""Mean kinetic temperature."""

import math

KELVIN_OFFSET = 273.15


def mean_kinetic_temperature(temps, weights, ratio):
    """Arrhenius mean of temperatures in degrees Celsius, each weighted by its hold (5.1).

    ratio is the activation ratio in kelvin.
    """
    total_weight = sum(weights)
    weighted = sum(
        weight * math.exp(-ratio / (temp + KELVIN_OFFSET)) for temp, weight in zip(temps, weights)
    )
    return ratio / -math.log(weighted / total_weight) - KELVIN_OFFSET
