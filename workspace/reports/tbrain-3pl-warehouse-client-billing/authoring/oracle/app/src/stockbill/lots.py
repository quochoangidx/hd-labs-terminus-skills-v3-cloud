"""Lots and the pallets they have on hand (billing schedule section 2)."""

from .dates import parse


def dispatches(lot):
    """The lot's dispatches as (date, pallets) pairs."""
    return [(parse(entry["date"]), entry["pallets"]) for entry in lot["dispatches"]]


def on_hand(lot, day):
    """How many of the lot's pallets are in the warehouse on `day`."""
    left = lot["pallets"]
    for when, pallets in dispatches(lot):
        # 2.2: a dispatched pallet is gone from the day after its dispatch; the schedule says
        # nothing of other entries, so they keep the package's own timing.
        if when < day or (when == day and pallets < 1):
            left -= pallets
    return left
