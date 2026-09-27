"""Demurrage days and charge."""


def days(stood, free):
    return stood - free


FULL_RATE_DAYS = 4


def charge(box, chargeable):
    if chargeable <= 0:
        return chargeable * box["rate"]
    later = max(chargeable - FULL_RATE_DAYS, 0)
    return (chargeable - later) * box["rate"] + later * 2 * box["rate"]
