"""Tax on a bill."""

RATE_BASIS_POINTS = 825


def tax(taxable):
    """8.25 per cent of a taxable amount in cents."""
    return taxable * RATE_BASIS_POINTS // 10000
