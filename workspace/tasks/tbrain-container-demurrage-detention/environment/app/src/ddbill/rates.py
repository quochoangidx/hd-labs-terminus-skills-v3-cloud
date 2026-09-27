"""Rate sheets, scales and tier charges (tariff rules section 5)."""


def current_revision(contract):
    """The contract's revision in force: the latest one on its rate sheet."""
    return contract["revisions"][-1]


def scale_for(contract, stage_name, size):
    """The tier list [[length, rate], ...] a stage of this size is charged on."""
    return current_revision(contract)["scales"][stage_name][size]


def tier_charge(count, scale):
    """What `count` chargeable days cost on the scale, in cents."""
    if count <= 0:
        return 0
    reached = 0
    for length, rate in scale:
        if length is None or count <= reached + length:
            return rate * count
        reached += length
    return rate * count
