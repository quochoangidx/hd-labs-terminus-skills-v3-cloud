"""Counts and variances."""


def final_count(line):
    """Rule 2.1: the recount when one was taken, the count otherwise."""
    recount = line.get("recount")
    if recount is None:
        return line["count"]
    return recount


def variance(line):
    """Rule 2.2."""
    return final_count(line) - line["system"]
