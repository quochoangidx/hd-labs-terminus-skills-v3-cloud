"""Price protection on the stock on hand when the supplier lowers a list price."""

from .dates import in_quarter, parse_day
from .rates import figure


def protection_credit(notices, quarter):
    """The price-protection credit in cents for the price notices of the quarter."""
    total = 0
    for effective, old_cents, new_cents, on_hand in notices:
        if not in_quarter(parse_day(effective), quarter):
            continue
        credit = (old_cents - new_cents) * on_hand
        total += credit
    return total
