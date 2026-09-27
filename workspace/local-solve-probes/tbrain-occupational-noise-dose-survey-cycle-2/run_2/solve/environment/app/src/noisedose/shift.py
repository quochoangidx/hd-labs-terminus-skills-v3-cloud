"""Shift dose of one surveyed worker.

A dosimeter is often switched on late or taken off early, so a survey may
sample less of the day than the worker actually worked.
"""

from .levels import EIGHT_HOURS
from .runs import measure


def is_partial(sampled, shift_minutes):
    """True for a partial survey (2.5): at least three quarters of the shift,
    but shorter than the shift."""
    return 4 * sampled >= 3 * shift_minutes and sampled < shift_minutes


def shift_dose(log, shift_minutes):
    """Dose for the worker's shift in per cent, projecting a partial survey (3.3)."""
    sampled, measured = measure(log)
    if sampled == 0:
        return 0.0
    if sampled >= shift_minutes:
        return measured
    if is_partial(sampled, shift_minutes):
        return measured * shift_minutes / sampled
    # The manual gives no shift dose for a survey that sampled less than three
    # quarters of the shift; keep the figure this step has always worked out.
    if sampled < EIGHT_HOURS:
        return measured * EIGHT_HOURS / sampled
    return measured
