"""Sampled time and measured dose of one dosimeter log.

A log is a list of runs, each a ``(minutes, level)`` pair in the order the
dosimeter logged it.
"""

from .levels import adds_dose, is_reading, reference_minutes


def measure(log):
    """Return ``(sampled_minutes, measured_dose)`` for a log.

    The sampled time is the total length of the worker's readings (2.4): every
    run logged at or above the bottom of the measuring range, whether or not it
    counts toward the dose. The measured dose is in per cent (3.2): the sum over
    the counted readings of each reading's minutes divided by its reference
    duration, times 100.
    """
    sampled = 0
    fraction = 0.0
    for minutes, level in log:
        if not is_reading(level):
            continue
        sampled += minutes
        if not adds_dose(level):
            continue
        fraction += minutes / reference_minutes(level)
    return sampled, 100.0 * fraction
