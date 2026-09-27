"""Mean kinetic temperature."""

import math

KELVIN_OFFSET = 273.15


def mean_kinetic_temperature(temps, weights, ratio):
    """Arrhenius mean of temperatures in degrees Celsius, each weighted by its hold (5.1).

    ratio is the activation ratio in kelvin.
    """
    total = 0.0
    weight = 0.0
    for temp, held in zip(temps, weights):
        if held:
            total += held * math.exp(-ratio / (temp + KELVIN_OFFSET))
            weight += held
    return ratio / -math.log(total / weight) - KELVIN_OFFSET
