"""Exact arithmetic helpers."""

from fractions import Fraction


def half_up(value):
    """The nearest whole number to an exact value; an exact half goes up."""
    value = Fraction(value)
    return (2 * value.numerator + value.denominator) // (2 * value.denominator)


def mean(values):
    """The exact average of a non-empty list of figures."""
    values = list(values)
    return Fraction(sum(values), len(values))
