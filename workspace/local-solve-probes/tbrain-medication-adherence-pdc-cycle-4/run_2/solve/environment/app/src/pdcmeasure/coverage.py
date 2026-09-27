"""Days covered by a member's fills of one class."""

SUPPLY_LIMIT = 100


def length(fill):
    """How many days a fill covers (AM-2 3.1); a fill over the supply limit covers the limit."""
    return min(fill.days, SUPPLY_LIMIT)


def covered(fills):
    """The set of days the fills cover, each fill starting after the days its own drug already covers
    (AM-2 3.2)."""
    days = set()
    last_covered = {}
    for fill in sorted(fills, key=lambda f: (f.date, f.position)):
        if fill.days < 1:
            continue
        start = fill.date
        earlier = last_covered.get(fill.drug)
        if earlier is not None and earlier >= start:
            start = earlier + 1
        end = start + length(fill) - 1
        days.update(range(start, end + 1))
        last_covered[fill.drug] = end if earlier is None else max(earlier, end)
    return days
