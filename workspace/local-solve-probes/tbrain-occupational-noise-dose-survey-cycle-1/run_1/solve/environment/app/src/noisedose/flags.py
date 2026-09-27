"""Ceiling and impulse flags of one worker."""

from .levels import CEILING_DBA, IMPULSE_DBC


def over_ceiling(log):
    """True when a reading in the log was logged above the continuous-level ceiling (5.1)."""
    return any(level > CEILING_DBA for _minutes, level in log)


def has_impulse(peaks):
    """True when a held peak is an impulse, that is at or above the impulse level (2.6, 5.2)."""
    return any(peak >= IMPULSE_DBC for peak in peaks)
