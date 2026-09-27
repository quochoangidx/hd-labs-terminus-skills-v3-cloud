"""Usage and allowance."""

KB_PER_MB = 1024
ALLOWANCE_MB = 5120


def used(line):
    """Megabytes used over the cycle."""
    return sum(line["sessions"]) // KB_PER_MB


def allowance(line):
    return ALLOWANCE_MB
