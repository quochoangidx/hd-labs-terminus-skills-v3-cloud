"""Class rows of the report."""

from fractions import Fraction

from .rounding import tenth

REPORTABLE_MEMBERS = 10


def class_row(code, rows):
    """One class's counts and adherence rate, from the member rows of that class.

    A class is reportable when ten or more members are in the measure for it, and then its rate is
    taken over its rate base, the members in the measure (AM-2 2.7, 5.1). The specification gives
    no rate base for a class that is not reportable, so that rate is worked out over the members
    with a fill of the class, as the package has always worked it out.
    """
    members = len(rows)
    measured = sum(1 for row in rows if row["in_measure"])
    adherent = sum(1 for row in rows if row["adherent"])
    base = measured if measured >= REPORTABLE_MEMBERS else members
    return {
        "class": code,
        "members": members,
        "in_measure": measured,
        "adherent": adherent,
        "rate": tenth(Fraction(100 * adherent, base)),
    }
