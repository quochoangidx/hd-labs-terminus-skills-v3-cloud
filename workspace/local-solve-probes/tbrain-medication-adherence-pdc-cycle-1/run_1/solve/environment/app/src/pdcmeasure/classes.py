"""Class rows of the report."""

from fractions import Fraction

from .rounding import tenth

REPORTABLE_MEMBERS = 10


def class_row(code, rows):
    """One class's counts and adherence rate, from the member rows of that class."""
    members = len(rows)
    measured = sum(1 for row in rows if row["in_measure"])
    adherent = sum(1 for row in rows if row["adherent"])
    # Rule 5.1 gives the rate of a reportable class (rule 2.7); for any other
    # class the rate stays the share of the members with a fill of it.
    denominator = measured if measured >= REPORTABLE_MEMBERS else members
    return {
        "class": code,
        "members": members,
        "in_measure": measured,
        "adherent": adherent,
        "rate": tenth(Fraction(100 * adherent, denominator)),
    }
