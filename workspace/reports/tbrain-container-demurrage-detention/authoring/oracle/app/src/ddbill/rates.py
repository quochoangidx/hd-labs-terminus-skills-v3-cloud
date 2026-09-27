"""Rate sheets, scales and tier charges (tariff rules section 5)."""

from .dates import parse


def current_revision(contract):
    """The latest revision on the contract's rate sheet."""
    return contract["revisions"][-1]


def revision_in_force(contract, day):
    """5.1: the latest revision effective on or before `day`, or None before the earliest one."""
    found = None
    for revision in contract["revisions"]:
        if parse(revision["effective"]) <= day:
            found = revision
    return found


def scale_for(contract, stage_name, size, first_chargeable):
    """The tier list [[length, rate], ...] a stage of this size is charged on."""
    revision = revision_in_force(contract, first_chargeable)
    if revision is None:
        # 5.1 gives no rule here, so the package's own choice stands: the latest revision.
        revision = current_revision(contract)
    return revision["scales"][stage_name][size]


def tier_charge(count, scale):
    """What `count` chargeable days cost on the scale, in cents, each day at its own tier's rate."""
    total, left = 0, count
    for length, rate in scale:
        take = left if length is None else min(left, length)
        total += take * rate
        left -= take
        if left <= 0:
            break
    return total
