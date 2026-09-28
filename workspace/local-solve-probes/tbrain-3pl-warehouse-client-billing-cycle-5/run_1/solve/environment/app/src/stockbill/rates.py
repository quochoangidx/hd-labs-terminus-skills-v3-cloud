"""Rate cards and storage tiers (billing schedule sections 3 and 4.2)."""

from .dates import parse


def current_revision(client, day):
    """The client's revision in force on `day`: its latest one effective by then (3.1)."""
    found = None
    for revision in client["revisions"]:
        if parse(revision["effective"]) <= day:
            found = revision
        else:
            break
    if found is None:
        found = client["revisions"][0]
    return found


def rates_for(client, day):
    """The rates in force on `day`: {"storage": tiers, "handling": {...}}."""
    return current_revision(client, day)["rates"]


def tier_rate(number, tiers):
    """The rate of the tier that takes storage week `number` (1 is the first week)."""
    reached = 0
    for length, rate in tiers:
        if length is None or number <= reached + length:
            return rate
        reached += length
    return rate
