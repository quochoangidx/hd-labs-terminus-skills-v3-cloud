"""Class rows of the report."""

from fractions import Fraction

from .rounding import tenth

REPORTABLE_MEMBERS = 10


def class_row(code, rows):
    """One class's counts and adherence rate, from the member rows of that class."""
    members = len(rows)
    measured = sum(1 for row in rows if row["in_measure"])
    adherent = sum(1 for row in rows if row["adherent"])
    # AM-2 2.7 gives a rate base only for a reportable class, one with ten or more members in the
    # measure; for any other class the rate is still worked out as the package has always worked it out.
    base = measured if measured >= REPORTABLE_MEMBERS else members
    return {
        "class": code,
        "members": members,
        "in_measure": measured,
        "adherent": adherent,
        "rate": tenth(Fraction(100 * adherent, base)),
    }
