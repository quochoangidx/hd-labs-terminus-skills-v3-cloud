"""Paying a settlement or carrying it forward."""

# A settlement below this many cents is carried forward instead of paid.
MINIMUM_SETTLEMENT = 25000


def settle(total):
    """(paid, carried) in cents for a settlement total."""
    if total < MINIMUM_SETTLEMENT:
        return 0, total
    return total, 0
