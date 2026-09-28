"""Fuel surcharge percentage from the weekly diesel price."""


def fuel_percentage(table, price):
    """Basis points for a diesel price (cents per gallon)."""
    for (low, percentage), (high, _next) in zip(table, table[1:]):
        if low < price <= high:
            return percentage
    return table[-1][1] if table else 0
