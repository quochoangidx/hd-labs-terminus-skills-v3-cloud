"""Rate cards and storage tiers (billing schedule sections 3 and 4.2)."""

from .dates import parse


def revision_on(client, day):
    """The client's revision in force on `day`: the latest one effective by then (3.1)."""
    found = None
    for revision in client["revisions"]:
        if parse(revision["effective"]) <= day:
            found = revision
    return found


def rates_for(client, day):
    """The rates in force on `day`: {"storage": tiers, "handling": {...}} (3.2)."""
    return revision_on(client, day)["rates"]


def tier_rate(number, tiers):
    """The rate of the tier that takes storage week `number` (1 is the first week)."""
    reached = 0
    for length, rate in tiers:
        if length is None or number <= reached + length:
            return rate
        reached += length
    return rate
