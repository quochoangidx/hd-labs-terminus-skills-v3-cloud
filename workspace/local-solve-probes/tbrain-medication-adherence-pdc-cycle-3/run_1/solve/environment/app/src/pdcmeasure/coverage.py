"""Days covered by a member's fills of one class."""

SUPPLY_LIMIT = 100


def _length(fill):
    """How many days a fill covers: its days supply when it is within the supply limit (AM-2 2.2, 3.1)."""
    return min(fill.days, SUPPLY_LIMIT)


def covered(fills):
    """The set of days the fills cover, refills of one drug starting after the supply before them (AM-2 3.2)."""
    days = set()
    drugs = {}
    for fill in sorted((f for f in fills if f.days >= 1), key=lambda f: (f.date, f.position)):
        seen, last = drugs.get(fill.drug, (set(), None))
        start = last + 1 if fill.date in seen else fill.date
        length = _length(fill)
        span = range(start, start + length)
        seen.update(span)
        days.update(span)
        end = start + length - 1
        drugs[fill.drug] = (seen, end if last is None else max(last, end))
    return days
