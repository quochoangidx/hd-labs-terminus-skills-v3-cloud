"""From the picker's amplitude to the size of the trace on a Wood-Anderson record."""

import math

# Static magnification of the Wood-Anderson torsion seismometer.
WOOD_ANDERSON_GAIN = 2800.0

# Nanometres of ground displacement to millimetres, before magnification.
NM_TO_MM = 1.0e-6


def record_amplitude_mm(amplitude_nm):
    """Trace amplitude on the simulated Wood-Anderson record, in millimetres."""
    return float(amplitude_nm) * WOOD_ANDERSON_GAIN * NM_TO_MM


def log_record_amplitude(amplitude_nm):
    """Base-ten logarithm of the record amplitude in millimetres."""
    return math.log10(record_amplitude_mm(amplitude_nm))
