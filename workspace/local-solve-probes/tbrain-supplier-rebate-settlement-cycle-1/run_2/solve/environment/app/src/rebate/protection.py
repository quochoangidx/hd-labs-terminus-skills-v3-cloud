"""Price protection on the stock on hand when the supplier lowers a list price."""

from .dates import in_quarter, parse_day

# Schedule R 2.4: a price notice that lowers the unit price by this much is a price drop.
PRICE_DROP_CENTS = 250

# A tidy-up is reached by no rule of the schedule, so its credit line keeps the figure
# the package works out today, at the constant the package carries today.
TIDY_UP_MINIMUM = 5000


def protection_credit(notices, quarter):
    """The price-protection credit in cents for the price notices of the quarter."""
    total = 0
    for effective, old_cents, new_cents, on_hand in notices:
        if not in_quarter(parse_day(effective), quarter):
            continue
        lowered = old_cents - new_cents
        credit = lowered * on_hand
        if lowered < PRICE_DROP_CENTS and credit < TIDY_UP_MINIMUM:
            credit = 0
        total += credit
    return total
