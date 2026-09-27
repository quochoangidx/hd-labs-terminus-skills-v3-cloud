"""Days covered by a member's fills of one class."""

SUPPLY_LIMIT = 100


def covered(fills):
    """The set of days the fills cover (AM-2 3.1 to 3.3).

    Fills of one drug are taken in fill date order, and fills of one date in file order; a fill
    starts on its fill date unless earlier fills of the same drug cover that date, and then on the
    day after the last day those earlier fills cover. Fills of different drugs never move one
    another.
    """
    days = set()
    last_covered = {}
    dispensed = (fill for fill in fills if fill.days >= 1)
    for fill in sorted(dispensed, key=lambda f: (f.date, f.position)):
        end = last_covered.get(fill.drug)
        start = fill.date if end is None or end < fill.date else end + 1
        length = min(fill.days, SUPPLY_LIMIT)
        days.update(range(start, start + length))
        last_covered[fill.drug] = start + length - 1
    return days
