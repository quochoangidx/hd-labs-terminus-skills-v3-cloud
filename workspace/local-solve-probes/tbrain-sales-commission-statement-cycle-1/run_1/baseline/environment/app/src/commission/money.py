"""Whole-cent arithmetic."""


def share_of(amount, bp):
    """bp basis points of a whole-cent amount, to the nearest cent, an exact half going up."""
    return (2 * amount * bp + 10000) // 20000


def rep_share(amount, split):
    """The rep's split, in per cent, of a whole-cent amount."""
    return share_of(amount, 100 * split)
