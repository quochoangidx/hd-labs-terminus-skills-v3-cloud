"""Counts and variances."""


def final_count(line):
    return line["count"]


def variance(line):
    return final_count(line) - line["system"]
