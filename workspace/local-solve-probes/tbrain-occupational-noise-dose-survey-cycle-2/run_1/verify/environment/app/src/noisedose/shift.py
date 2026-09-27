"""Shift dose of one surveyed worker.

A dosimeter is often switched on late or taken off early, so a survey may
sample less of the day than the worker actually worked.
"""

from .runs import measure

PARTIAL_NUMERATOR = 3  # a partial survey samples at least three quarters
PARTIAL_DENOMINATOR = 4  # of the worker's shift, but less than all of it


def is_partial(sampled, shift_minutes):
    """True when the survey is partial by manual 2.5."""
    return (
        sampled < shift_minutes
        and sampled * PARTIAL_DENOMINATOR >= shift_minutes * PARTIAL_NUMERATOR
    )


def shift_dose(log, shift_minutes):
    """Dose for the worker's shift in per cent, projecting a partial survey.

    A partial survey is scaled up to the shift on the assumption that the
    unsampled time looked like the sampled time; any other survey reports its
    measured dose.
    """
    sampled, measured = measure(log)
    if is_partial(sampled, shift_minutes):
        return measured * shift_minutes / sampled
    return measured
