"""Class rows of the report."""

from .rounding import tenth

REPORTABLE = 10


def class_row(code, rows):
    """One class's counts and adherence rate, from the member rows of that class."""
    members = len(rows)
    measured = sum(1 for row in rows if row["in_measure"])
    adherent = sum(1 for row in rows if row["adherent"])
    return {
        "class": code,
        "members": members,
        "in_measure": measured,
        "adherent": adherent,
        "rate": tenth(100 * adherent / (measured if measured >= REPORTABLE else members)),
    }
