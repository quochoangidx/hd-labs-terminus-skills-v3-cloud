"""Eight-hour time-weighted average level and exposure status."""

import math
from decimal import ROUND_HALF_UP, Decimal

from .levels import CRITERION_DBA, EXCHANGE_DB

ACTION_LEVEL_DB = 82.0
EXPOSURE_LIMIT_DB = 85.0

_TENTH = Decimal("0.1")


def twa_for(dose):
    """Eight-hour TWA in dB for a dose in per cent, or None for no dose."""
    if dose <= 0.0:
        return None
    return CRITERION_DBA + EXCHANGE_DB * math.log2(dose / 100.0)


def to_tenth(value):
    """A level as reported, to a tenth of a decibel, an exact half going up."""
    return float(Decimal(value).quantize(_TENTH, rounding=ROUND_HALF_UP))


def status_for(twa):
    """``"over"``, ``"action"`` or ``"below"`` for a reported TWA.

    A worker or group without a TWA is below the action level.
    """
    if twa is None:
        return "below"
    if twa > EXPOSURE_LIMIT_DB:
        return "over"
    if twa >= ACTION_LEVEL_DB:
        return "action"
    return "below"
