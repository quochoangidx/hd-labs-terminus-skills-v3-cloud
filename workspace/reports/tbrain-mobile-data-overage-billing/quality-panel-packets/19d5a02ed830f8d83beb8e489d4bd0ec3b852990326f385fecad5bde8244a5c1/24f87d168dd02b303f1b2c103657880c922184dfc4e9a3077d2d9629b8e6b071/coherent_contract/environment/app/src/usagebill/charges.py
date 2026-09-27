"""Overage and charge."""


def overage(megabytes, included):
    return megabytes - included


def charge(line, over):
    return over * line["rate"]
