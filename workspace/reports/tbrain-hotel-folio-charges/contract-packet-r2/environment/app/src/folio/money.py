"""Money helpers."""

from fractions import Fraction


def to_cents(amount):
    """Whole cents from an exact amount."""
    return round(Fraction(amount))


def percent(base, rate):
    """``rate`` per cent of ``base`` cents, exactly."""
    return Fraction(base) * Fraction(rate) / 100
