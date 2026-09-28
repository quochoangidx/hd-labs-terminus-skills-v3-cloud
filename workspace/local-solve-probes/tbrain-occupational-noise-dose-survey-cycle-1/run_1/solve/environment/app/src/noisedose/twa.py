"""Eight-hour time-weighted average level and exposure status."""

import math
from decimal import Decimal, ROUND_FLOOR

ACTION_LEVEL_DB = 82.0  # bottom of the programme's action band (5.3)
EXPOSURE_LIMIT_DB = 85.0  # the programme's exposure limit (5.3)


def twa_for(dose):
    """Eight-hour TWA in dB for a dose in per cent, or None for no dose (4.1)."""
    if dose <= 0.0:
        return None
    return 85.0 + 3.0 * math.log2(dose / 100.0)


def to_tenth(value):
    """A level as reported, to the nearest tenth of a decibel, a half going up (1.2)."""
    scaled = Decimal(value) * 10
    whole = scaled.to_integral_value(rounding=ROUND_FLOOR)
    if scaled - whole >= Decimal("0.5"):
        whole += 1
    return float(whole / 10)


def status_for(twa):
    """``"over"``, ``"action"`` or ``"below"`` for a reported TWA (5.3).

    A worker or group without a TWA is below the action level. Ceiling and
    impulse flags are handled by the caller.
    """
    if twa is None:
        return "below"
    if twa > EXPOSURE_LIMIT_DB:
        return "over"
    if twa >= ACTION_LEVEL_DB:
        return "action"
    return "below"
