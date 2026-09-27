"""Reported percentages."""

from fractions import Fraction


def tenth(value):
    """A percentage as reported, to the tenth, an exact half going up (rule 1.2)."""
    scaled = Fraction(value) * 10
    whole = (2 * scaled.numerator + scaled.denominator) // (2 * scaled.denominator)
    return whole / 10
