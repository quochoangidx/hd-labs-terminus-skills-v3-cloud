"""Field loss, minimum loss and the deductible options."""

from .figures import figure
from .rounding import half_up

# One hundred per cent, in tenths of a per cent.
WHOLE = 1000


def field_loss(stand, leaf):
    """A field's loss from its stand loss and leaf loss, in tenths of a per cent.

    Leaf loss falls only on the stand the storm left standing (4.2).
    """
    return stand + half_up(leaf * (WHOLE - stand), WHOLE)


def payable_loss(loss, option):
    """The payable loss of a field under its deductible option, in tenths of a per cent."""
    if loss < figure("minimum_loss"):
        return 0
    if option == "full":
        return loss
    if option == "straight":
        return max(0, loss - figure("straight_deductible"))
    if option == "vanishing":
        return min(loss, max(0, 2 * (loss - figure("vanishing_start"))))
    raise ValueError(f"unknown deductible option {option!r}")
