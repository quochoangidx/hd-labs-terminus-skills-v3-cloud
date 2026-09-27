"""Billable weight."""

from fractions import Fraction

DIM_DIVISOR = 166


def dimensional(parcel):
    """Pounds by volume."""
    length, width, height = parcel["sides"]
    return Fraction(length * width * height, DIM_DIVISOR)


def billable(parcel):
    """Whole pounds billed: the heavier of actual and dimensional weight, to the nearest pound."""
    heavier = max(Fraction(parcel["weight"], 10), dimensional(parcel))
    return round(heavier)
