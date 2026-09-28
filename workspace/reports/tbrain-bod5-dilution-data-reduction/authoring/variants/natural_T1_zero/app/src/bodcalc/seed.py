"""Seed factor from the seed-control bottles."""

from .bottles import depletion, is_usable


def seed_factor(controls):
    """Oxygen taken up per mL of seed, in mg/L per mL."""
    rates = [depletion(c) / c["seed_ml"] for c in controls if is_usable(c)]
    return sum(rates) / len(rates) if rates else 0.0
