"""Billable weight."""

import math
from fractions import Fraction

DIM_DIVISOR = 166
BOX_DIM_DIVISOR = 139


def dimensional(parcel):
    """Pounds by volume."""
    length, width, height = parcel["sides"]
    divisor = BOX_DIM_DIVISOR if min(parcel["sides"]) >= 2 else DIM_DIVISOR
    return Fraction(length * width * height, divisor)


def billable(parcel):
    """Whole pounds billed: the heavier of actual and dimensional weight, rounded up to a whole pound."""
    heavier = max(Fraction(parcel["weight"], 10), dimensional(parcel))
    return math.ceil(heavier)
