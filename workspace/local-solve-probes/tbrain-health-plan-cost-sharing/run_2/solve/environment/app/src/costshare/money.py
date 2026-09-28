"""Whole-cent arithmetic."""

BASIS = 10_000


def share(amount: int, rate: int) -> int:
    """The share of ``amount`` cents at ``rate`` basis points, in whole cents."""
    if 0 <= rate <= BASIS:
        q, r = divmod(amount * rate, BASIS)
        if 2 * r > BASIS or (2 * r == BASIS and q % 2 == 1):
            q += 1
        return q
    return (amount * rate + BASIS // 2) // BASIS
