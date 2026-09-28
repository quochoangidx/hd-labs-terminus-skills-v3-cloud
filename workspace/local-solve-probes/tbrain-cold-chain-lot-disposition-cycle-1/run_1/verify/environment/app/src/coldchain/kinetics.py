"""Mean kinetic temperature."""

import math

KELVIN_OFFSET = 273.15


def mean_kinetic_temperature(temps, ratio):
    """Arrhenius mean of temperatures in degrees Celsius; ratio is the activation ratio in kelvin."""
    total = sum(math.exp(-ratio / (temp + KELVIN_OFFSET)) for temp in temps)
    return ratio / -math.log(total / len(temps)) - KELVIN_OFFSET
