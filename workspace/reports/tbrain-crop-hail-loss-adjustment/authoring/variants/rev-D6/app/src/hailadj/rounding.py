"""Integer rounding helpers."""


def half_up(numerator, denominator):
    """numerator / denominator rounded to the nearest whole unit, an exact half up.

    Both arguments are integers and the denominator is positive.
    """
    quotient, remainder = divmod(numerator, denominator)
    if 2 * remainder >= denominator:
        quotient += 1
    return quotient
