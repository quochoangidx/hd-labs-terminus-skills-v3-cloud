"""The volume tier table and the volume rebate."""

from .money import half_up


def load_tiers(rows):
    """Tier rows as (threshold in cents, rate in basis points), in table order."""
    return [(row["from"], row["bp"]) for row in rows]


def tier_rate(amount, tiers):
    """The rate in basis points of the tier an amount reaches, nought when it reaches none.

    The tier an amount reaches is the last row whose threshold the amount is at or above;
    an amount below nought reaches no tier.
    """
    if amount < 0:
        return 0
    rate = 0
    for threshold, bp in tiers:
        if amount >= threshold:
            rate = bp
    return rate


def volume_rebate(net, bp):
    """The volume rebate in cents: the rate in basis points of the net purchases."""
    return half_up(net * bp, 10000)
