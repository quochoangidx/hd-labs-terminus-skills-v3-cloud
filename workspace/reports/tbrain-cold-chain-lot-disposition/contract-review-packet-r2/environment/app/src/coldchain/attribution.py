"""How long each logger reading stands for, and where the logger missed readings."""

LOGGER_WINDOW_MINUTES = 60  # the longest stretch one logger reading is trusted to cover


def holds(readings):
    """Minutes each reading of one export stands for, in export order."""
    held = []
    for index, reading in enumerate(readings):
        if index + 1 < len(readings):
            span = readings[index + 1].minute - reading.minute
        else:
            span = LOGGER_WINDOW_MINUTES
        held.append(min(span, LOGGER_WINDOW_MINUTES))
    return held


def unlogged_minutes(readings):
    """Total length of the spacings where the logger missed readings."""
    total = 0
    for earlier, later in zip(readings, readings[1:]):
        span = later.minute - earlier.minute
        if span > LOGGER_WINDOW_MINUTES:
            total += span
    return total
