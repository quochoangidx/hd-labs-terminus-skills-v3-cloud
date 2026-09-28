"""From the picker's amplitude to the size of the trace on a Wood-Anderson record."""

import math

# Static magnification the network's simulated Wood-Anderson actually delivers
# (rule 2.2); Richter's tables assumed the nominal 2800.
WOOD_ANDERSON_GAIN = 2080.0

# Nanometres of ground displacement to millimetres, before magnification.
NM_TO_MM = 1.0e-6


def record_amplitude_mm(amplitude_nm):
    """Trace amplitude on the simulated Wood-Anderson record, in millimetres.

    The picker's ``amplitude_nm`` is a peak-to-peak value, so the record
    amplitude is half of it, magnified (rule 2.2).
    """
    return float(amplitude_nm) / 2.0 * WOOD_ANDERSON_GAIN * NM_TO_MM


def log_record_amplitude(amplitude_nm):
    """Base-ten logarithm of the record amplitude in millimetres."""
    return math.log10(record_amplitude_mm(amplitude_nm))


# An amplitude is a reading when it is at least this many times its channel's
# noise (rule 2.3).
NOISE_FACTOR = 3.0


def is_reading(amplitude):
    """Whether one amplitude object is a reading (rule 2.3)."""
    return float(amplitude["amplitude_nm"]) >= NOISE_FACTOR * float(amplitude["noise_nm"])
