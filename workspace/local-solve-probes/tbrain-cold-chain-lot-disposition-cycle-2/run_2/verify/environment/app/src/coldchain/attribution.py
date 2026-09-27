"""How long each logger reading stands for, and where the logger missed readings."""

LAST_READING_MINUTES = 60  # a logger's last reading is taken to cover one more reporting window
GAP_MINUTES = 60  # a spacing longer than this means the logger missed readings


def holds(readings):
    """Minutes each reading of one export stands for, in export order."""
    held = []
    for index, reading in enumerate(readings):
        if index + 1 < len(readings):
            held.append(readings[index + 1].minute - reading.minute)
        else:
            held.append(LAST_READING_MINUTES)
    return held


def unlogged_minutes(readings):
    """Total length of the spacings where the logger missed readings."""
    total = 0
    for earlier, later in zip(readings, readings[1:]):
        span = later.minute - earlier.minute
        if span > GAP_MINUTES:
            total += span
    return total
