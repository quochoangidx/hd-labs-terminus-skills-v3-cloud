"""Paying a settlement or carrying it forward."""

from .rates import figure


def settle(total):
    """(paid, carried) in cents for a settlement total."""
    if total < figure("settlement_minimum"):
        return 0, total
    return total, 0
