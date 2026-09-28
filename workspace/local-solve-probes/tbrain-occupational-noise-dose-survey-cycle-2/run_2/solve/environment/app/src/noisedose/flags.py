"""Ceiling and impulse flags of one worker."""

from .levels import CEILING_DBA, IMPULSE_DBC, is_reading


def over_ceiling(log):
    """True when one of the worker's readings is above the ceiling level (5.1)."""
    return any(is_reading(level) and level > CEILING_DBA for _minutes, level in log)


def has_impulse(peaks):
    """True when one of the held peaks is an impulse, 140.0 dBC or more (2.6, 5.2)."""
    return any(peak >= IMPULSE_DBC for peak in peaks)
