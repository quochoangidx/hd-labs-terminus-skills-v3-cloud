"""Lots and the pallets they have on hand (billing schedule section 2)."""

from .dates import parse


def dispatches(lot):
    """The lot's dispatches as (date, pallets) pairs."""
    return [(parse(entry["date"]), entry["pallets"]) for entry in lot["dispatches"]]


def on_hand(lot, day):
    """How many of the lot's pallets are in the warehouse on `day` (2.2).

    A dispatched pallet is still on hand on the day of its entry and gone from
    the next day, so only entries dated before `day` have taken effect.
    """
    left = lot["pallets"]
    for when, pallets in dispatches(lot):
        if when < day:
            left -= pallets
    return left
