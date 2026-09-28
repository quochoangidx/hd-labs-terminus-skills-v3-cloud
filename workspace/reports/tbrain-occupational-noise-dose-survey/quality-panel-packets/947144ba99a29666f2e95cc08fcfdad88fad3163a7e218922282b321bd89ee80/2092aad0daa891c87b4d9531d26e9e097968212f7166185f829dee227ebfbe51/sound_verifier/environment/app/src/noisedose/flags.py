"""Ceiling and impulse flags of one worker."""

from .levels import CEILING_DBA, IMPULSE_DBC


def over_ceiling(log):
    """True when a run in the log was logged above the continuous-level ceiling."""
    return any(level > CEILING_DBA for _minutes, level in log)


def has_impulse(peaks):
    """True when a held peak is above the impulse level."""
    return any(peak > IMPULSE_DBC for peak in peaks)
