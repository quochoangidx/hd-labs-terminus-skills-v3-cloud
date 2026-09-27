"""Reported percentages."""

from fractions import Fraction


def tenth(value):
    """A percentage as reported, to the nearest tenth, an exact half going up (AM-2 1.2)."""
    scaled = Fraction(value) * 10
    units = (scaled * 2 + 1) // 2
    return int(units) / 10
