"""Rate cards and storage tiers (billing schedule sections 3 and 4.3)."""

from .dates import parse


def current_revision(client):
    """The latest revision on the client's rate card."""
    return client["revisions"][-1]


def revision_in_force(client, day):
    """3.1: the latest revision effective on or before `day`, or None before the earliest one."""
    found = None
    for revision in client["revisions"]:
        if parse(revision["effective"]) <= day:
            found = revision
    return found


def rates_for(client, day):
    """The rates in force on `day`: {"storage": tiers, "handling": {...}}."""
    revision = revision_in_force(client, day)
    if revision is None:
        # 3.1 gives no rule here, so the package's own choice stands: the latest revision.
        revision = current_revision(client)
    return revision["rates"]


def tier_rate(number, tiers):
    """The rate of the tier that takes storage week `number` (1 is the first week)."""
    reached = 0
    for length, rate in tiers:
        if length is None or number <= reached + length:
            return rate
        reached += length
    return rate
