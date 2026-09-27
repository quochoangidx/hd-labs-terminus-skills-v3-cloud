"""Claims file decoding."""

from collections import namedtuple

from .days import day

Fill = namedtuple("Fill", "date drug klass days position")
Member = namedtuple("Member", "id fills stays")


def member(record):
    """A member's fills, in file order, and stays as (admission, discharge) ordinals."""
    fills = [
        Fill(day(line["date"]), line["drug"], line["class"], line["days"], position)
        for position, line in enumerate(record["fills"])
    ]
    stays = [(day(admission), day(discharge)) for admission, discharge in record["stays"]]
    return Member(record["id"], fills, stays)


def by_class(fills):
    """Claim lines grouped by class code, each group in file order; a class is listed once one of its lines
    dispensed a supply."""
    groups = {}
    for fill in fills:
        groups.setdefault(fill.klass, []).append(fill)
    return {code: group for code, group in groups.items() if any(fill.days for fill in group)}


def stay_days(stays):
    """Every stay day, as a set of ordinals."""
    out = set()
    for admission, discharge in stays:
        out.update(range(admission, discharge + 1))
    return out
