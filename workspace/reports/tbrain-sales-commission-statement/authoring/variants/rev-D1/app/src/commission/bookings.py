"""A rep's bookings for the quarter."""

from .dates import in_quarter, parse_day
from .money import rep_share


def quarter_orders(orders, quarter):
    """The orders booked in the quarter, as (value, split, first) triples."""
    counted = []
    for booked, value, split, first in orders:
        if in_quarter(parse_day(booked), quarter):
            counted.append((value, split, first))
    return counted


def bookings(orders, quarter):
    """The rep's bookings in cents."""
    total = 0
    for value, split, _first in quarter_orders(orders, quarter):
        total += rep_share(value, split)
    return total
