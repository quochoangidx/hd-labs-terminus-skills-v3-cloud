"""What a plate carries into a result: its colonies, its plated amount and its class."""

from fractions import Fraction

COUNTABLE_LOW = 25
COUNTABLE_HIGH = 250


def dilution_at(step):
    """The dilution at a step of the tenfold series."""
    return Fraction(1, 10 ** step)


def plated_amount(dilution):
    """Grams or millilitres of sample on one plate of a dilution."""
    return dilution_at(dilution.step)


def colonies(reading):
    return reading or 0


def is_countable(reading):
    return COUNTABLE_LOW <= colonies(reading) <= COUNTABLE_HIGH


def is_crowded(reading):
    return colonies(reading) > COUNTABLE_HIGH
