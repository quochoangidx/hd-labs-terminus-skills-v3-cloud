"""Sampled time and measured dose of one dosimeter log.

A log is a list of runs, each a ``(minutes, level)`` pair in the order the
dosimeter logged it.
"""

from .levels import CEILING_DBA, adds_dose, is_reading, reference_minutes


def measure(log):
    """Return ``(sampled_minutes, measured_dose)`` for a log.

    The sampled time is the total length of the worker's readings (2.4). The
    measured dose is in per cent: the sum over the counted readings of each
    reading's length divided by the reference duration at the level it is
    counted at, times 100 (3.2).
    """
    sampled = 0
    fraction = 0.0
    for minutes, level in log:
        if not is_reading(level):
            continue
        sampled += minutes
        counted = min(level, CEILING_DBA)
        if not adds_dose(counted):
            continue
        fraction += minutes / reference_minutes(counted)
    return sampled, 100.0 * fraction
