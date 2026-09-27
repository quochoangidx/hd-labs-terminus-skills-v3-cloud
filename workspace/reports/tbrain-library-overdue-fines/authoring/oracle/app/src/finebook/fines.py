"""Fines."""


def fine(loan, late):
    if late <= 0:
        return late * loan["daily_fine"]
    return min(late * loan["daily_fine"], loan["replacement"])
