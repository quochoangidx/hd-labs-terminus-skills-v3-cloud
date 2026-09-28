"""Whole-cent arithmetic."""

BASIS = 10_000


def share(amount: int, rate: int) -> int:
    """The share of ``amount`` cents at ``rate`` basis points, in whole cents.

    For a rate from 0 to 10000 the result is rounded to the nearest cent, with
    an exact half going to the even cent.
    """
    if 0 <= rate <= BASIS:
        quotient, remainder = divmod(amount * rate, BASIS)
        twice = 2 * remainder
        if twice > BASIS or (twice == BASIS and quotient % 2 == 1):
            quotient += 1
        return quotient
    return (amount * rate + BASIS // 2) // BASIS
