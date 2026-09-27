"""How long each logger reading stands for, and where the logger missed readings."""

LOGGED_INTERVAL_MINUTES = 30  # an interval of this length or less is a logged interval (2.4)


def spacings(readings):
    """Minutes from each reading of one export to the next, nought for the last (5.1)."""
    spans = []
    for index, reading in enumerate(readings):
        if index + 1 < len(readings):
            spans.append(readings[index + 1].minute - reading.minute)
        else:
            spans.append(0)
    return spans


def holds(readings):
    """Minutes each reading of one export stands for, in export order (2.7)."""
    held = []
    for span in spacings(readings):
        held.append(span if span <= LOGGED_INTERVAL_MINUTES else 0)
    return held


def unlogged_minutes(readings):
    """Total length of the logger gaps of one export (2.4, 3.2)."""
    total = 0
    for earlier, later in zip(readings, readings[1:]):
        span = later.minute - earlier.minute
        if span > LOGGED_INTERVAL_MINUTES:
            total += span
    return total
