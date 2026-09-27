"""Usage and allowance."""

KB_PER_MB = 1024
ALLOWANCE_MB = 5120
PLAN_ALLOWANCE_MB = {"BASIC": 2048, "PLUS": 10240}


def used(line):
    """Megabytes used over the cycle."""
    return sum(-(-kilobytes // KB_PER_MB) for kilobytes in line["sessions"])


def allowance(line):
    return PLAN_ALLOWANCE_MB.get(line["plan"], ALLOWANCE_MB)
