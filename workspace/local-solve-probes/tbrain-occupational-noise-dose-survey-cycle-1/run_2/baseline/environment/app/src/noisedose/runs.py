"""Sampled time and measured dose of one dosimeter log.

A log is a list of runs, each a ``(minutes, level)`` pair in the order the
dosimeter logged it.
"""

from .levels import adds_dose, reference_minutes


def measure(log):
    """Return ``(sampled_minutes, measured_dose)`` for a log.

    The measured dose is in per cent: the sum over the runs that count of each
    run's minutes divided by its reference duration, times 100.
    """
    sampled = 0
    fraction = 0.0
    for minutes, level in log:
        if not adds_dose(level):
            continue
        sampled += minutes
        fraction += minutes / reference_minutes(level)
    return sampled, 100.0 * fraction
