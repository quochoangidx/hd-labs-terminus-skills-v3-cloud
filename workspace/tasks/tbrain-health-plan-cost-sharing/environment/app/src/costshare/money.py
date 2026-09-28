"""Whole-cent arithmetic."""

BASIS = 10_000


def share(amount: int, rate: int) -> int:
    """The share of ``amount`` cents at ``rate`` basis points, in whole cents."""
    return (amount * rate + BASIS // 2) // BASIS
