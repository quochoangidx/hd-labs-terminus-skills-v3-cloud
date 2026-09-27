"""Tax on a bill."""

RATE_BASIS_POINTS = 825
BASIS = 10000


def tax(taxable):
    """8.25 per cent of a taxable amount in cents, to the nearest cent.

    An exact half cent goes up (manual RC-3 rules 1.2 and 4.1).
    """
    return (taxable * RATE_BASIS_POINTS + BASIS // 2) // BASIS
