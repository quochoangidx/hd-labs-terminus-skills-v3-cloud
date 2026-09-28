"""The volume tier table and the volume rebate."""

from .money import half_up


def load_tiers(rows):
    """Tier rows as (threshold in cents, rate in basis points), in table order."""
    return [(row["from"], row["bp"]) for row in rows]


def tier_rate(amount, tiers):
    """The rate in basis points of the tier an amount of purchases reaches."""
    rate = 0
    for threshold, bp in tiers:
        if amount >= threshold:
            rate = bp
    return rate


def volume_rebate(net, bp):
    """The volume rebate in cents on net purchases at a rate in basis points."""
    return half_up(net * bp, 10000)
