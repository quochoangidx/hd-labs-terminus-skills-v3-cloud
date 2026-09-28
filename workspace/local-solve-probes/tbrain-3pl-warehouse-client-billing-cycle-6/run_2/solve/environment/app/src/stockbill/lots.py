"""Lots and the pallets they have on hand (billing schedule section 2)."""

from .dates import parse


def dispatches(lot):
    """The lot's dispatches as (date, pallets) pairs."""
    return [(parse(entry["date"]), entry["pallets"]) for entry in lot["dispatches"]]


def on_hand(lot, day):
    """How many of the lot's pallets are in the warehouse on `day` (2.2)."""
    if day < parse(lot["received"]):
        return 0
    left = lot["pallets"]
    for when, pallets in dispatches(lot):
        # A dispatched pallet is still on hand on the day it is dispatched (2.2);
        # any other entry changes the pallets on hand on its own date.
        if when < day or (pallets < 1 and when == day):
            left -= pallets
    return left
