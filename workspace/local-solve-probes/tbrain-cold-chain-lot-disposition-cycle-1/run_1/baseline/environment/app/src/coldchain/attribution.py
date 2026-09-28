"""How long each logger reading stands for, and where the logger missed readings."""

HOLD_CAP_MINUTES = 60  # the longest stretch one logger reading is credited with
GAP_MINUTES = 60  # a spacing longer than this means the logger missed readings


def holds(readings):
    """Minutes each reading of one export stands for, in export order."""
    held = []
    for index, reading in enumerate(readings):
        if index + 1 < len(readings):
            span = readings[index + 1].minute - reading.minute
        else:
            span = HOLD_CAP_MINUTES
        held.append(min(span, HOLD_CAP_MINUTES))
    return held


def unlogged_minutes(readings):
    """Total length of the spacings where the logger missed readings."""
    total = 0
    for earlier, later in zip(readings, readings[1:]):
        span = later.minute - earlier.minute
        if span > GAP_MINUTES:
            total += span
    return total
