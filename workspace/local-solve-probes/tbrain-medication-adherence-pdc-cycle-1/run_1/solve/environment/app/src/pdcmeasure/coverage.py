"""Days covered by a member's fills of one class."""

SUPPLY_LIMIT = 100


def covered(fills):
    """The set of days the fills cover."""
    days = set()
    last_covered = {}
    for fill in sorted(fills, key=lambda f: (f.date, f.position)):
        if fill.days > SUPPLY_LIMIT:
            continue
        end = last_covered.get(fill.drug)
        start = end + 1 if end is not None and end >= fill.date else fill.date
        days.update(range(start, start + fill.days))
        last_covered[fill.drug] = start + fill.days - 1
    return days
