"""Counts and variances."""


def has_recount(line):
    """Whether a recount was taken for this line (CC-2 rule 2.1)."""
    return line.get("recount") is not None


def final_count(line):
    """The line's final count: its recount when one was taken (CC-2 2.1)."""
    if has_recount(line):
        return line["recount"]
    return line["count"]


def variance(line):
    """Final count less system quantity (CC-2 2.2)."""
    return final_count(line) - line["system"]
