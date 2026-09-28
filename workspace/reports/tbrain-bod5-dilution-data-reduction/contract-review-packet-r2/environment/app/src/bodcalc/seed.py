"""Seed factor from the seed-control bottles."""

from .bottles import depletion


def seed_factor(controls):
    """Oxygen taken up per mL of seed, in mg/L per mL."""
    taken = 0.0
    seed = 0.0
    for control in controls:
        taken += depletion(control)
        seed += control["seed_ml"]
    return taken / seed
