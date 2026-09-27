"""How long each logger reading stands for, and where the logger missed readings."""

LOGGED_MINUTES = 30  # an interval of this length or less is logged; a longer one is a logger gap


def spacings(readings):
    """Minutes from each reading of one export to the next, in export order (nought for the last)."""
    spans = [later.minute - earlier.minute for earlier, later in zip(readings, readings[1:])]
    spans.append(0)
    return spans


def holds(readings):
    """Minutes each reading of one export stands for, in export order."""
    return [span if span <= LOGGED_MINUTES else 0 for span in spacings(readings)]


def unlogged_minutes(readings):
    """Total length of the spacings where the logger missed readings."""
    total = 0
    for earlier, later in zip(readings, readings[1:]):
        span = later.minute - earlier.minute
        if span > LOGGED_MINUTES:
            total += span
    return total
