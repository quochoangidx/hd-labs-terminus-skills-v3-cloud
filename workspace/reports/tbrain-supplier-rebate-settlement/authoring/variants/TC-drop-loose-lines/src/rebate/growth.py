"""The growth bonus against the same quarter a year before."""

from .money import half_up

GROWTH_TARGET = (110, 100)
GROWTH_SHARE_BP = 200


def growth_bonus(net, prior):
    """The growth bonus in cents for net purchases against last year's net purchases."""
    if prior <= 0:
        return 0
    if net * GROWTH_TARGET[1] < prior * GROWTH_TARGET[0]:
        return 0
    return half_up((net - prior) * GROWTH_SHARE_BP, 10000)
