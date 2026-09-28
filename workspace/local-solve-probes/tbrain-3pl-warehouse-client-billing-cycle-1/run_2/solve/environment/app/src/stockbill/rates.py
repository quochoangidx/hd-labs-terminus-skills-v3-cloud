"""Rate cards and storage tiers (billing schedule sections 3 and 4.3)."""

from .dates import parse


def revision_in_force(client, day):
    """The client's latest revision whose effective date is on or before `day` (3.1)."""
    found = None
    for revision in client["revisions"]:
        if parse(revision["effective"]) <= day:
            found = revision
    return found


def current_revision(client):
    """The latest revision on the client's rate card."""
    return client["revisions"][-1]


def rates_on(client, day):
    """The rates of the revision in force on `day`: {"storage": tiers, "handling": {...}}.

    Before the client's earliest effective date no revision is in force and the
    schedule gives no rule for the value, so the package keeps the rates it used
    for such a day: those of the latest revision.
    """
    revision = revision_in_force(client, day)
    if revision is None:
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
