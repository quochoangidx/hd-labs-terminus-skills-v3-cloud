"""Whole-cent arithmetic."""


def half_up(numerator, denominator):
    """numerator / denominator to the nearest whole cent, an exact half going up."""
    return (2 * numerator + denominator) // (2 * denominator)
