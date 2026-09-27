"""Fines."""


def fine(loan, late):
    return late * loan["daily_fine"]
