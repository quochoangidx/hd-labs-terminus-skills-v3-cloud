"""Shift dose of one surveyed worker.

A dosimeter is often switched on late or taken off early, so a survey may
sample less of the day than the worker actually worked.
"""

from .levels import EIGHT_HOURS
from .runs import measure


def is_full_shift(sampled, shift_minutes):
    """True when the sampled time is at least three quarters of the shift (2.5)."""
    return 4 * sampled >= 3 * shift_minutes


def shift_dose(log, shift_minutes):
    """Dose for the worker's shift in per cent.

    A full-shift survey that sampled less than the whole shift is projected to
    the shift (3.3); one that sampled the whole shift or longer reports its
    measured dose. The manual gives no rule for a survey that is not a
    full-shift survey, so such a survey keeps the projection the package has
    always made for it, worked out from the manual's sampled time and measured
    dose.
    """
    sampled, measured = measure(log)
    if sampled == 0:
        return 0.0
    if is_full_shift(sampled, shift_minutes):
        if sampled < shift_minutes:
            return measured * shift_minutes / sampled
        return measured
    if sampled < EIGHT_HOURS:
        return measured * EIGHT_HOURS / sampled
    return measured
