"""Counts and variances."""


def final_count(line):
    return line["recount"] if line["recount"] is not None else line["count"]


def variance(line):
    return final_count(line) - line["system"]
