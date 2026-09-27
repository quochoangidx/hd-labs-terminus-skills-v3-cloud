"""Reported percentages."""

import math
from fractions import Fraction


def tenth(value):
    """A percentage as reported, to the nearest tenth with an exact half going up (AM-2 1.2)."""
    scaled = Fraction(value) * 10
    return math.floor(scaled + Fraction(1, 2)) / 10
