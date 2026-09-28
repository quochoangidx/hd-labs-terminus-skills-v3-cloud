"""Division rounded to a whole tenth or kilometre."""


def divide(numerator, denominator):
    """numerator / denominator rounded to a whole unit.

    The result is rounded to the nearest whole unit and an exact half goes up,
    to the larger number (1.1).
    """
    if denominator < 0:
        numerator, denominator = -numerator, -denominator
    return (2 * numerator + denominator) // (2 * denominator)
