"""Rate cards and storage tiers (billing schedule sections 3 and 4.3)."""


def current_revision(client):
    """The client's revision in force: the latest one on its rate card."""
    return client["revisions"][-1]


def rates_for(client):
    """The rates a client is billed on: {"storage": tiers, "handling": {...}}."""
    return current_revision(client)["rates"]


def tier_rate(number, tiers):
    """The rate of the tier that takes storage week `number` (1 is the first week)."""
    reached = 0
    for length, rate in tiers:
        if length is None or number <= reached + length:
            return rate
        reached += length
    return rate
