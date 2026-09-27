"""How long each logger reading stands for, and where the logger missed readings."""

HOLD_CAP_MINUTES = 60  # the longest stretch one logger reading is credited with
LOGGED_MINUTES = 30  # an interval this long or shorter is logged (2.4); longer is a logger gap


def holds(readings):
    """Minutes each reading of one export stands for, in export order (2.7)."""
    held = []
    for index, reading in enumerate(readings):
        if index + 1 == len(readings):
            held.append(0)  # the last reading of an export has a hold of nought
            continue
        span = readings[index + 1].minute - reading.minute
        if span <= LOGGED_MINUTES:
            held.append(span)  # the length of the logged interval it opens
        else:
            held.append(min(span, HOLD_CAP_MINUTES))
    return held


def unlogged_minutes(readings):
    """Total length of the logger gaps of one export (3.2)."""
    total = 0
    for earlier, later in zip(readings, readings[1:]):
        span = later.minute - earlier.minute
        if span > LOGGED_MINUTES:
            total += span
    return total
