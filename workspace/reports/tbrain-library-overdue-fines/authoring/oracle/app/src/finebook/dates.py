"""Due days and late days."""

LOAN_DAYS = 14
KIND_LOAN_DAYS = {"BOOK": 21, "DVD": 7}


def due(loan):
    return loan["borrowed"] + KIND_LOAN_DAYS.get(loan["kind"], LOAN_DAYS)


def closed(day):
    """Sundays: every day whose number leaves 6 when divided by 7."""
    return day % 7 == 6


def late_days(loan, due_day):
    if loan["returned"] <= due_day:
        return loan["returned"] - due_day
    return sum(1 for day in range(due_day + 1, loan["returned"] + 1) if not closed(day))
