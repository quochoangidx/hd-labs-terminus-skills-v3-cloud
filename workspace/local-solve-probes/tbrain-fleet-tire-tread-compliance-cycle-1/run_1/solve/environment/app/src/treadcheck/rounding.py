"""Division rounded to a whole tenth or kilometre."""


def divide(numerator, denominator):
    """numerator / denominator rounded to a whole unit, an exact half up.

    Section 1.1 of the standard: the result is rounded to the nearest whole
    unit the figure is kept in, and an exact half goes up, to the larger
    number.
    """
    if denominator < 0:
        numerator, denominator = -numerator, -denominator
    return (2 * numerator + denominator) // (2 * denominator)
