"""Days covered by a member's fills of one class."""

SUPPLY_LIMIT = 100


def covered(fills):
    """The set of days the fills cover."""
    days = set()
    for fill in sorted(fills, key=lambda f: (f.date, f.position)):
        start = fill.date + 1
        days.update(range(start, start + min(fill.days, SUPPLY_LIMIT)))
    return days
