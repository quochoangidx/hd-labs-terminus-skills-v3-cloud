"""In service, on watch or to be pulled."""

REMOVAL = 32  # tenths, at a drive or trailer position
REMOVAL_STEER = 40  # tenths, at a steer position
WATCH_BAND = 16  # tenths above the removal depth

STEER = "steer"

IN_SERVICE = "in service"
WATCH = "watch"
PULL = "pull"


def removal_depth(position):
    """The depth in tenths at which a tire at this position comes off (2.4)."""
    if position == STEER:
        return REMOVAL_STEER
    return REMOVAL


def status(position, latest):
    """The status of a tire from its position and latest depth (5.1)."""
    limit = removal_depth(position)
    if latest <= limit:
        return PULL
    if latest <= limit + WATCH_BAND:
        return WATCH
    return IN_SERVICE
