"""Sampled time and measured dose of one dosimeter log.

A log is a list of runs, each a ``(minutes, level)`` pair in the order the
dosimeter logged it.
"""

from .levels import CEILING_DBA, adds_dose, reference_minutes


def measure(log):
    """Return ``(sampled_minutes, measured_dose)`` for a log.

    The measured dose is in per cent: the sum over the runs that count of each
    run's minutes divided by its reference duration, times 100.
    """
    sampled = 0
    fraction = 0.0
    for minutes, level in log:
        counted = min(level, CEILING_DBA)
        if not adds_dose(counted):
            continue
        sampled += minutes
        fraction += minutes / reference_minutes(counted)
    return sampled, 100.0 * fraction
