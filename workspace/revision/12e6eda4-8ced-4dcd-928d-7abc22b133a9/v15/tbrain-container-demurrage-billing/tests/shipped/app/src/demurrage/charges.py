"""Demurrage days and charge."""


def days(stood, free):
    return stood - free


def charge(box, chargeable):
    return chargeable * box["rate"]
