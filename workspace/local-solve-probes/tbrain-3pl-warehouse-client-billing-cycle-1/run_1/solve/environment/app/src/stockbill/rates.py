"""Rate cards and storage tiers (billing schedule sections 3 and 4.3)."""

from .dates import parse


def revision_in_force(client, day):
    """The client's latest revision whose effective date is on or before `day` (3.1).

    On a day before the client's earliest effective date no revision is in force
    and the schedule gives no rule for the value; the package keeps its own
    reading of the rate card there, the latest revision on it.
    """
    revisions = client["revisions"]
    in_force = None
    for revision in revisions:
        if parse(revision["effective"]) <= day:
            in_force = revision
    if in_force is None:
        return revisions[-1]
    return in_force


def rates_for(client, day):
    """The rates in force on `day`: {"storage": tiers, "handling": {...}}."""
    return revision_in_force(client, day)["rates"]


def tier_rate(number, tiers):
    """The rate of the tier that takes storage week `number` (1 is the first week)."""
    reached = 0
    for length, rate in tiers:
        if length is None or number <= reached + length:
            return rate
        reached += length
    return rate
