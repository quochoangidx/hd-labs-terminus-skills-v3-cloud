"""Reported percentages."""

import math


def tenth(value):
    """A percentage as reported, to the nearest tenth, an exact half going up."""
    return math.floor(value * 10 + 0.5) / 10
