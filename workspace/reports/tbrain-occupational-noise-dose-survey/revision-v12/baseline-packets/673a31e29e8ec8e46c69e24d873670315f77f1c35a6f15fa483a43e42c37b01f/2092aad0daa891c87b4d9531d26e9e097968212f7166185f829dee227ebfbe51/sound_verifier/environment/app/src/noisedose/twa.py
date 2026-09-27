"""Eight-hour time-weighted average level and exposure status."""

import math

ACTION_LEVEL_DB = 85.0
EXPOSURE_LIMIT_DB = 90.0


def twa_for(dose):
    """Eight-hour TWA in dB for a dose in per cent, or None for no dose."""
    if dose <= 0.0:
        return None
    return 90.0 + 16.61 * math.log10(dose / 100.0)


def to_tenth(value):
    """A level as reported, to a tenth of a decibel."""
    return math.floor(value * 10.0) / 10.0


def status_for(twa):
    """``"over"``, ``"action"`` or ``"below"`` for a reported TWA.

    A worker or group without a TWA is below the action level.
    """
    if twa is None:
        return "below"
    if twa >= EXPOSURE_LIMIT_DB:
        return "over"
    if twa >= ACTION_LEVEL_DB:
        return "action"
    return "below"
