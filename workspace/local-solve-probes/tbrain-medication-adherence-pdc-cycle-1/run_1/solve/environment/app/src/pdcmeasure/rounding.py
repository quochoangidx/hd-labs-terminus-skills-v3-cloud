"""Reported percentages."""

from fractions import Fraction


def tenth(value):
    """A percentage as reported, to the tenth, an exact half going up."""
    scaled = Fraction(value) * 10 + Fraction(1, 2)
    return (scaled.numerator // scaled.denominator) / 10
