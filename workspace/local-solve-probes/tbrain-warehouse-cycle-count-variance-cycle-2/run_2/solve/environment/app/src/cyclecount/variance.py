"""Counts and variances."""


def final_count(line):
    """Rule 2.1: the recount when one was taken, the count otherwise."""
    recount = line["recount"]
    if recount is None:
        return line["count"]
    return recount


def variance(line):
    """Rule 2.2: the final count less the system quantity."""
    return final_count(line) - line["system"]
