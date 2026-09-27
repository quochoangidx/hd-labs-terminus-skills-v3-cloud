"""Days covered by a member's fills of one class."""

SUPPLY_LIMIT = 100


def within_limit(fill):
    """Whether the fill's days supply is no more than the supply limit (rule 2.2)."""
    return fill.days <= SUPPLY_LIMIT


def start_days(fills):
    """Each fill's start day, keyed by its position (rule 3.2).

    Fills of one drug are taken in the order of their fill dates, fills of one
    fill date in file order. A fill starts on its fill date unless an earlier
    fill of the same drug covers that date, in which case it starts the day
    after the last day the earlier fills of that drug cover. Fills of
    different drugs never move one another.
    """
    starts = {}
    last_covered = {}
    for fill in sorted(fills, key=lambda f: (f.date, f.position)):
        end = last_covered.get(fill.drug)
        if end is not None and fill.date <= end:
            start = end + 1
        else:
            start = fill.date
        starts[fill.position] = start
        if within_limit(fill):
            finish = start + fill.days - 1
            last_covered[fill.drug] = finish if end is None else max(end, finish)
    return starts


def covered(fills, starts):
    """The set of days the fills cover, given each fill's start day (rules 3.1, 3.3)."""
    days = set()
    for fill in fills:
        if within_limit(fill):
            start = starts[fill.position]
            days.update(range(start, start + fill.days))
    return days
