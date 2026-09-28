"""Ceiling and impulse flags of one worker."""

from .levels import CEILING_DBA, IMPULSE_DBC, is_reading


def over_ceiling(log):
    """True when a reading in the log was logged above the continuous-level ceiling."""
    return any(is_reading(level) and level > CEILING_DBA for _minutes, level in log)


def has_impulse(peaks):
    """True when a held peak is an impulse: at or above the impulse level."""
    return any(peak >= IMPULSE_DBC for peak in peaks)
