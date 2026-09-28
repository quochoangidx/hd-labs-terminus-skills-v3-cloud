"""Ship-and-debit chargebacks on sales made below the distributor's cost."""

from .dates import in_quarter, parse_day

# Schedule R 2.5: a sale below cost is a contract sale when the price charged is this
# many cents or more below the distributor's unit cost.
CONTRACT_BELOW_CENTS = 100

# A counter sale is reached by no rule of the schedule, so it keeps the figure the
# package works out today, at the constant the package carries today.
COUNTER_MINIMUM = 25


def chargebacks(sales, quarter):
    """The chargeback in cents for the below-cost sales of the quarter."""
    total = 0
    for sold, units, cost_cents, price_cents in sales:
        if not in_quarter(parse_day(sold), quarter):
            continue
        below = cost_cents - price_cents
        if below >= CONTRACT_BELOW_CENTS:
            # Schedule R 5.2.
            total += below * units
            continue
        if below < COUNTER_MINIMUM:
            continue
        total += below * units
    return total
