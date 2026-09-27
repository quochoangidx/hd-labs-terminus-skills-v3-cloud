"""Reported percentages."""

from fractions import Fraction


def tenth(value):
    """A percentage as reported, to the nearest tenth, an exact half going up (AM-2 1.2)."""
    scaled = Fraction(value) * 10
    whole = scaled.numerator // scaled.denominator
    if scaled - whole >= Fraction(1, 2):
        whole += 1
    return whole / 10
