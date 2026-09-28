"""Sampled time and measured dose of one dosimeter log.

A log is a list of runs, each a ``(minutes, level)`` pair in the order the
dosimeter logged it.
"""

from .levels import adds_dose, is_reading, reference_minutes


def measure(log):
    """Return ``(sampled_minutes, measured_dose)`` for a log.

    The sampled time is the total length of the worker's readings (manual 2.4).
    The measured dose is in per cent: the sum over the counted readings of each
    reading's minutes divided by its reference duration, times 100 (manual 3.2).
    """
    sampled = 0
    fraction = 0.0
    for minutes, level in log:
        if is_reading(level):
            sampled += minutes
        if adds_dose(level):
            fraction += minutes / reference_minutes(level)
    return sampled, 100.0 * fraction
