"""Days covered by a member's fills of one class."""

SUPPLY_LIMIT = 100


def covered(fills):
    """The set of days the fills cover.

    Rule 3.1 and 3.2: fills of one drug are taken in fill date order, and in
    file order within a fill date. A fill starts on its fill date unless an
    earlier fill of the same drug covers that date, in which case it starts on
    the day after the last day those earlier fills cover. Fills of different
    drugs never move one another.
    """
    days = set()
    last_day = {}
    for fill in sorted(fills, key=lambda f: (f.date, f.position)):
        earlier = last_day.get(fill.drug)
        if earlier is not None and earlier >= fill.date:
            start = earlier + 1
        else:
            start = fill.date
        length = min(fill.days, SUPPLY_LIMIT)
        days.update(range(start, start + length))
        end = start + length - 1
        last_day[fill.drug] = end if earlier is None else max(earlier, end)
    return days
