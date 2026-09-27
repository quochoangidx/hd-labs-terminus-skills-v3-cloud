"""Days covered by a member's fills of one class."""

SUPPLY_LIMIT = 100


def length(fill):
    """How many days a fill covers."""
    return min(fill.days, SUPPLY_LIMIT)


def covered(fills):
    """The set of days the fills cover.

    Fills of one drug are taken in the order of their fill dates, and fills of
    one fill date in the order the file lists them.  A fill starts on its fill
    date unless an earlier fill of the same drug covers that date, in which case
    it starts the day after the last day those earlier fills cover.  Fills of
    different drugs never move one another.
    """
    days = set()
    last_covered = {}
    for fill in sorted(fills, key=lambda f: (f.date, f.position)):
        start = fill.date
        earlier = last_covered.get(fill.drug)
        if earlier is not None and earlier >= start:
            start = earlier + 1
        end = start + length(fill) - 1
        days.update(range(start, end + 1))
        last_covered[fill.drug] = end
    return days
