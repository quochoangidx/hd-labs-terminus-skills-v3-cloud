"""Which reading's temperature stands for which logger minutes."""

GAP_MINUTES = 60  # a spacing longer than this means the logger missed readings


def attribute(readings):
    """Minutes attributed to each reading of one export, in export order."""
    minutes = [0] * len(readings)
    for index in range(1, len(readings)):
        minutes[index] += readings[index].minute - readings[index - 1].minute
    return minutes


def unlogged_minutes(readings):
    """Total length of the spacings where the logger missed readings."""
    total = 0
    for earlier, later in zip(readings, readings[1:]):
        spacing = later.minute - earlier.minute
        if spacing > GAP_MINUTES:
            total += spacing
    return total
