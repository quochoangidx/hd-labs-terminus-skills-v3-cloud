"""Overage and charge."""


def overage(megabytes, included):
    return megabytes - included


FULL_RATE_MB = 1024
LATER_RATE = 1


def charge(line, over):
    if over <= 0:
        return over * line["rate"]
    later = max(over - FULL_RATE_MB, 0)
    return (over - later) * line["rate"] + later * LATER_RATE
