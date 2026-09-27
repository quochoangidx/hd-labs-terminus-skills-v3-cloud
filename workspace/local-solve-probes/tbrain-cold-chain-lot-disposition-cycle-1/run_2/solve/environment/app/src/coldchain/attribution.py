"""How long each logger reading stands for, and where the logger missed readings."""

LOGGED_INTERVAL_MINUTES = 30  # 2.4: an interval this long or shorter is logged, a longer one is a gap
HOLD_CAP_MINUTES = 60  # the stretch credited to a reading that opens a logger gap (2.7 fixes no value)


def holds(readings):
    """Minutes each reading of one export stands for, in export order (2.7)."""
    held = []
    for index, reading in enumerate(readings):
        if index + 1 == len(readings):
            held.append(0)  # the last reading of an export has a hold of nought
            continue
        span = readings[index + 1].minute - reading.minute
        if span <= LOGGED_INTERVAL_MINUTES:
            held.append(span)  # the reading opens a logged interval: its hold is that interval
        else:
            held.append(min(span, HOLD_CAP_MINUTES))
    return held


def unlogged_minutes(readings):
    """Total length of this export's logger gaps (3.2)."""
    total = 0
    for earlier, later in zip(readings, readings[1:]):
        span = later.minute - earlier.minute
        if span > LOGGED_INTERVAL_MINUTES:
            total += span
    return total
