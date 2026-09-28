"""Shift dose of one surveyed worker.

A dosimeter is often switched on late or taken off early, so a survey may
sample less of the day than the worker actually worked.
"""

from .levels import EIGHT_HOURS
from .runs import measure


def shift_dose(log, shift_minutes):
    """Dose for the worker's shift in per cent, projecting a partial survey.

    A partial survey is scaled up to the shift on the assumption that the
    unsampled time looked like the sampled time.
    """
    sampled, measured = measure(log)
    if sampled >= shift_minutes:
        return measured
    if 4 * sampled >= 3 * shift_minutes:  # a partial survey (manual 2.5, 3.3)
        return measured * shift_minutes / sampled
    if sampled == 0:
        return 0.0
    if sampled < EIGHT_HOURS:
        return measured * EIGHT_HOURS / sampled
    return measured
