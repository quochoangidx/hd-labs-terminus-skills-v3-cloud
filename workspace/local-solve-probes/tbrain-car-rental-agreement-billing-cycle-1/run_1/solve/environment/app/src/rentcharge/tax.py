"""Tax on a bill."""

RATE_BASIS_POINTS = 825


def tax(taxable):
    """8.25 per cent of a taxable amount in cents, half a cent rounding up."""
    return (taxable * RATE_BASIS_POINTS + 5000) // 10000
