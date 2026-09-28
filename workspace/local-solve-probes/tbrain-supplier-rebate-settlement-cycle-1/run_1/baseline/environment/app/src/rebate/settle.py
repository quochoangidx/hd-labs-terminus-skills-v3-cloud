"""Paying a settlement or carrying it forward."""

# Credits below this many cents are not worth paying out.
MINIMUM_CREDIT = 5000


def settle(total):
    """(paid, carried) in cents for a settlement total."""
    if total < MINIMUM_CREDIT:
        return 0, total
    return total, 0
