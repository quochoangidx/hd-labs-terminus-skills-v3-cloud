"""Whole-cent arithmetic."""


def half_up(numerator, denominator):
    """numerator / denominator for non-negative integers, rounded to the nearest whole unit, halves up."""
    return (2 * numerator + denominator) // (2 * denominator)


def ratio_of(amount, fraction):
    """`amount` cents times a (numerator, denominator) fraction, rounded to the cent."""
    numerator, denominator = fraction
    return half_up(amount * numerator, denominator)
