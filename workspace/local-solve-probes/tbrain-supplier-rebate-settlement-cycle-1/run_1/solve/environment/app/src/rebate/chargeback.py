"""Ship-and-debit chargebacks on sales made below the distributor's cost."""

from .dates import in_quarter, parse_day

# Cents a unit below cost from which the package works out a chargeback line.
# No rule of Schedule R reaches this figure, so it keeps its value.
CHARGEBACK_FLOOR_PER_UNIT = 25


def chargebacks(sales, quarter):
    """The chargeback in cents for the below-cost sales of the quarter."""
    total = 0
    for sold, units, cost_cents, price_cents in sales:
        if not in_quarter(parse_day(sold), quarter):
            continue
        below = cost_cents - price_cents
        if below < CHARGEBACK_FLOOR_PER_UNIT:
            continue
        total += below * units
    return total
