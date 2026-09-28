"""Shift dose of one surveyed worker.

A dosimeter is often switched on late or taken off early, so a survey may
sample less of the day than the worker actually worked.
"""

from .levels import EIGHT_HOURS
from .runs import measure


def shift_dose(log, shift_minutes):
    """Dose for the worker's shift in per cent.

    A full-shift survey (manual 2.5: sampled time at least three quarters of
    the shift) that sampled less than the whole shift is projected to the
    shift by manual 3.3; one that sampled the whole shift or longer reports
    its measured dose. The manual gives no rule for a survey that sampled
    less than three quarters of the shift, so the package's own long-standing
    step stands for those.
    """
    sampled, measured = measure(log)
    if 4 * sampled >= 3 * shift_minutes:
        if sampled < shift_minutes:
            return measured * shift_minutes / sampled
        return measured
    if sampled == 0:
        return 0.0
    if sampled < EIGHT_HOURS:
        return measured * EIGHT_HOURS / sampled
    return measured
