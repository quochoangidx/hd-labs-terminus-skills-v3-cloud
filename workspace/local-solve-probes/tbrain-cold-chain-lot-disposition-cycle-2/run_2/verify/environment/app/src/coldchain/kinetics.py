"""Mean kinetic temperature."""

import math

KELVIN_OFFSET = 273.15


def mean_kinetic_temperature(temps, weights, ratio):
    """Arrhenius mean of temperatures in degrees Celsius, each weighted; ratio is the activation ratio in kelvin."""
    total = math.fsum(weight * math.exp(-ratio / (temp + KELVIN_OFFSET)) for temp, weight in zip(temps, weights))
    return ratio / -math.log(total / math.fsum(weights)) - KELVIN_OFFSET
