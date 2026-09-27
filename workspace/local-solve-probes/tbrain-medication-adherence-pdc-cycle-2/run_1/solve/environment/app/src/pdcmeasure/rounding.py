"""Reported percentages."""

from fractions import Fraction

HALF = Fraction(1, 2)


def tenth(value):
    """A percentage as reported: to the nearest tenth, an exact half going up."""
    scaled = Fraction(value) * 10
    whole = scaled.numerator // scaled.denominator
    if scaled - whole >= HALF:
        whole += 1
    return whole / 10
