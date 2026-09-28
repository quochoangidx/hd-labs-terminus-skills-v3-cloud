"""Dwell and free time."""

FREE_DAYS = 5


def dwell(box):
    """Days the container stood in the terminal."""
    return box["picked_up"] - box["discharged"]


def free_days(box):
    return FREE_DAYS
