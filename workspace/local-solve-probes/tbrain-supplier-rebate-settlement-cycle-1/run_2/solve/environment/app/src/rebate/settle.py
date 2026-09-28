"""Paying a settlement or carrying it forward."""

# Schedule R 6.2: a settlement of this many cents or more is paid in full.
MINIMUM_CREDIT = 25000


def settle(total):
    """(paid, carried) in cents for a settlement total."""
    if total < MINIMUM_CREDIT:
        return 0, total
    return total, 0
