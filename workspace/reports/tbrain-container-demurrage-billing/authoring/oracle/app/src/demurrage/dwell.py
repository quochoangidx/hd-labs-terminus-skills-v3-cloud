"""Dwell and free time."""

FREE_DAYS = 5
TARIFF_FREE_DAYS = {"DRY": 5, "REEFER": 3}


def dwell(box):
    """Days the container stood in the terminal."""
    return box["picked_up"] - box["discharged"] + 1


def free_days(box):
    return TARIFF_FREE_DAYS.get(box["type"], FREE_DAYS)
