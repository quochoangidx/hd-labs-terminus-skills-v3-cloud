"""Days covered by a member's fills of one class."""

SUPPLY_LIMIT = 100


def length(fill):
    """How many days a fill covers (rule 3.1)."""
    return min(fill.days, SUPPLY_LIMIT)


def covered(fills):
    """The set of days the fills cover (rules 3.1 to 3.3).

    A fill's start day is its fill date unless an earlier fill of the same drug
    covers that date, in which case it is the day after the last day the
    earlier fills of that drug cover. Fills of different drugs never move one
    another.
    """
    days = set()
    per_drug = {}
    for fill in sorted(fills, key=lambda f: (f.date, f.position)):
        if fill.days < 1:
            continue
        drug_days, last = per_drug.get(fill.drug, (set(), None))
        start = last + 1 if fill.date in drug_days else fill.date
        span = range(start, start + length(fill))
        drug_days.update(span)
        days.update(span)
        end = start + length(fill) - 1
        per_drug[fill.drug] = (drug_days, end if last is None else max(last, end))
    return days
