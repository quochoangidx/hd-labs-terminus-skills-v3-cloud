"""Due days and late days."""

LOAN_DAYS = 14


def due(loan):
    return loan["borrowed"] + LOAN_DAYS


def late_days(loan, due_day):
    return loan["returned"] - due_day
