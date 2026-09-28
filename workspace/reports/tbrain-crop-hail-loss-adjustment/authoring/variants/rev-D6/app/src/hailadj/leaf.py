"""Leaf loss from defoliation, by growth stage."""

from .rounding import half_up

# Per cent of defoliation that becomes lost yield, by growth stage on the storm day.
CHART = {
    "V6": 5,
    "V10": 15,
    "V14": 35,
    "VT": 100,
    "R2": 75,
    "R4": 40,
    "R5": 15,
}


def leaf_loss(defoliation, stage):
    """The leaf loss of a field, in tenths of a per cent."""
    return half_up(defoliation * CHART[stage], 100)
