"""Seed factor from the seed-control bottles."""

from .bottles import depletion, is_usable


def seed_factor(controls):
    """Oxygen taken up per mL of seed, in mg/L per mL."""
    reference = [c for c in controls if is_usable(c)] or list(controls)
    rates = [depletion(c) / c["seed_ml"] for c in reference]
    return sum(rates) / len(rates)
