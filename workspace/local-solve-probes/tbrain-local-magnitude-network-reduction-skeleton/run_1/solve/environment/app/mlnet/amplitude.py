"""From the picker's amplitude to the size of the trace on a Wood-Anderson record."""

import math

# Static magnification the network's simulated Wood-Anderson actually delivers
# (manual rule 2.2); the nominal 2800 of Richter's tables is not used.
WOOD_ANDERSON_GAIN = 2080.0

# The picker measures peak to peak (rule 2.1); the record amplitude is half of
# that peak-to-peak value (rule 2.2).
PEAK_TO_PEAK_HALVING = 2.0

# Nanometres of ground displacement to millimetres, before magnification.
NM_TO_MM = 1.0e-6


def record_amplitude_mm(amplitude_nm):
    """Trace amplitude on the simulated Wood-Anderson record, in millimetres."""
    return float(amplitude_nm) / PEAK_TO_PEAK_HALVING * WOOD_ANDERSON_GAIN * NM_TO_MM


def log_record_amplitude(amplitude_nm):
    """Base-ten logarithm of the record amplitude in millimetres."""
    return math.log10(record_amplitude_mm(amplitude_nm))
