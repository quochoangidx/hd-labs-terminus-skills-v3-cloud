"""Reported percentages."""

import math


def tenth(value):
    """A percentage as reported, to the tenth."""
    return math.floor(value * 10 + 0.5) / 10
