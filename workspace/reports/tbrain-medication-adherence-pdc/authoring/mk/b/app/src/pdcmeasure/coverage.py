"""Days covered by a member's fills of one class."""

SUPPLY_LIMIT = 100


def covered(fills):
    """The set of days the fills cover."""
    days = set()
    after_last = {}
    for fill in sorted(fills, key=lambda f: (f.date, f.position)):
        start = fill.date
        if fill.date < after_last.get(fill.drug, fill.date):
            start = after_last[fill.drug]
        end = start + min(fill.days, SUPPLY_LIMIT)
        days.update(range(start, end))
        after_last[fill.drug] = max(after_last.get(fill.drug, end), end)
    return days
