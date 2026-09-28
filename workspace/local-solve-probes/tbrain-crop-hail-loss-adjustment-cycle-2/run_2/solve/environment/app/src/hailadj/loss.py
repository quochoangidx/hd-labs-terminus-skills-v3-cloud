"""Field loss, minimum loss and the deductible options."""

from .figures import figure
from .rounding import half_up
from .sheet import UNITS


def field_loss(stand, leaf):
    """A field's loss from its stand loss and leaf loss, in tenths of a per cent.

    Leaf loss falls only on the plants the storm left standing (4.2), so it is
    taken of what remains once the stand loss is taken from 100 per cent.
    """
    whole = figure(UNITS["loss"], "whole")
    return stand + half_up(leaf * (whole - stand), whole)


def payable_loss(loss, option):
    """The payable loss of a field under its deductible option, in tenths of a per cent."""
    if loss < figure(UNITS["loss"], "minimum"):
        return 0
    if option == "full":
        return loss
    if option == "straight":
        return max(0, loss - figure(UNITS["payable"], "straight"))
    if option == "vanishing":
        return min(loss, max(0, 2 * (loss - figure(UNITS["loss"], "vanish"))))
    raise ValueError(f"unknown deductible option {option!r}")
