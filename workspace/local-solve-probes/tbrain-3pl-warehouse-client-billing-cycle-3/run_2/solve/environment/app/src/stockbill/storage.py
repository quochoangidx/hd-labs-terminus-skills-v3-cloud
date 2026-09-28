"""Storage weeks, storage and peak stock (billing schedule sections 2.4 and 4)."""

from datetime import timedelta

from .dates import parse
from .lots import on_hand
from .rates import rates_on, tier_rate

WEEK = 7


def week_starts(lot, start, end):
    """(week number, first day) of the lot's storage weeks starting within the period (2.4)."""
    received = parse(lot["received"])
    out = []
    number = 1
    day = received
    if start > received:
        skipped = (start - received).days // WEEK
        number += skipped
        day += timedelta(days=skipped * WEEK)
        while day < start:
            number += 1
            day += timedelta(days=WEEK)
    while day <= end:
        out.append((number, day))
        number += 1
        day += timedelta(days=WEEK)
    return out


def billed_weeks(lot, start, end):
    """(week number, first day, pallets on hand) of the lot's billed weeks (2.4, 4.1)."""
    out = []
    for number, first in week_starts(lot, start, end):
        pallets = on_hand(lot, first)
        if pallets > 0:
            out.append((number, first, pallets))
    return out


def storage(lot, client, start, end):
    """(billed weeks, storage in cents) for the lot over the period (4.1-4.3)."""
    weeks, total = 0, 0
    for number, first, pallets in billed_weeks(lot, start, end):
        tiers = rates_on(client, first)["storage"]
        total += pallets * tier_rate(number, tiers)
        weeks += 1
    return weeks, total


def peak(lot, start, end):
    """The most pallets the lot held on the first day of one of its billed weeks (4.5)."""
    most = 0
    for _number, _first, pallets in billed_weeks(lot, start, end):
        if pallets > most:
            most = pallets
    return most
