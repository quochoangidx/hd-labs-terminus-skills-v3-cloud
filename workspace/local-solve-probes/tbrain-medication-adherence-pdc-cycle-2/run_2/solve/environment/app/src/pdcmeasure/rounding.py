"""Reported percentages."""


def tenth(numerator, denominator):
    """The percentage 100 * numerator / denominator as reported, to the nearest
    tenth with an exact half going up."""
    tenths = (2000 * numerator + denominator) // (2 * denominator)
    return tenths / 10
