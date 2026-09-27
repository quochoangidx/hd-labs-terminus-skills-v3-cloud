"""Shift dose of one surveyed worker.

A dosimeter is often switched on late or taken off early, so a survey may
sample less of the day than the worker actually worked.
"""

from .levels import EIGHT_HOURS
from .runs import measure


def shift_dose(log, shift_minutes):
    """Dose for the worker's shift in per cent, projecting a partial survey.

    A survey that sampled less than a full day is scaled up to it on the
    assumption that the unsampled time looked like the sampled time.
    """
    sampled, measured = measure(log)
    if sampled == 0:
        return 0.0
    if sampled < EIGHT_HOURS:
        return measured * EIGHT_HOURS / sampled
    return measured
