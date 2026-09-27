"""Independent model of specification AM-2 (/app/docs/adherence-measure-spec.md).

Worked out from the specification alone; it never imports the package under repair. Where the
specification gives no rule for a figure, the model mirrors the shipped package's step for it and
says so ("Shipped step"), feeding that step the figures the specification does define.
Percentages are worked in exact fractions and rounded to the tenth, an exact half going up (1.2).
"""

from datetime import date
from fractions import Fraction
import math

SUPPLY_LIMIT = 100  # 2.2
ADHERENT_PDC = Fraction(80)  # 4.2
REPORTABLE = 10  # 2.7


def ordinal(text):
    return date.fromisoformat(text).toordinal()


def year_end(year):
    return date(year, 12, 31).toordinal()


def tenth(value):
    """1.2: nearest tenth, an exact half going up; value is a Fraction."""
    return float(Fraction(math.floor(value * 10 + Fraction(1, 2)), 10))


def fill_length(days):
    """3.1: a fill within the limit covers its days supply.
    Shipped step for a fill above the supply limit (no rule): coverage.py counts min(days, SUPPLY_LIMIT)."""
    return days if days <= SUPPLY_LIMIT else SUPPLY_LIMIT


def covered_days(fills):
    """3.2-3.3: the days covered for one class. fills: (date, position, drug, days) tuples.
    Each drug is taken in fill-date order, then file order; a fill whose date an earlier fill of the
    drug covers starts the day after the last day those fills cover. Different drugs never move one another."""
    days = set()
    after_last = {}  # drug -> the day after the last day its fills taken so far cover
    for fill_date, _position, drug, supply in sorted(fills):
        start = fill_date
        if drug in after_last and fill_date < after_last[drug]:
            start = after_last[drug]
        end = start + fill_length(supply)
        days.update(range(start, end))
        after_last[drug] = max(after_last.get(drug, end), end)
    return days


def in_measure(fills, year):
    """2.4: fills on two or more different fill dates, index date no later than 2 October."""
    dates = {f[0] for f in fills}
    return len(dates) >= 2 and min(dates) <= date(year, 10, 2).toordinal()


def member_row(fills, stays, year):
    index = min(f[0] for f in fills)
    cover = covered_days(fills)
    measured = in_measure(fills, year)
    if measured:
        last = year_end(year)  # 2.5 treatment period
        period = sum(1 for d in range(index, last + 1) if d not in stays)  # 4.1 denominator
        covered = sum(1 for d in range(index, last + 1) if d in cover and d not in stays)  # 3.4
    else:
        # Shipped step (no rule for a member outside the measure): measure.period() takes the span from the
        # index date to the last covered day, no later than year end; pdc.figures() counts every day of it,
        # and counts covered days of it that are not stay days.
        last = min(max(cover), year_end(year))
        period = last - index + 1
        covered = sum(1 for d in range(index, last + 1) if d in cover and d not in stays)
    pdc = tenth(Fraction(100 * covered, period))
    return {
        "index": date.fromordinal(index).isoformat(),
        "in_measure": measured,
        "period": period,
        "covered": covered,
        "pdc": pdc,
        "adherent": measured and Fraction(pdc).limit_denominator(10) >= ADHERENT_PDC,  # 4.2, on the PDC as reported
    }


def class_row(code, rows):
    members = len(rows)
    measured = sum(1 for r in rows if r["in_measure"])
    adherent = sum(1 for r in rows if r["adherent"])
    if measured >= REPORTABLE:
        rate = tenth(Fraction(100 * adherent, measured))  # 5.1
    else:
        # Shipped step (no rule for a class that is not reportable): classes.class_row() divides by every
        # member with a fill of the class.
        rate = tenth(Fraction(100 * adherent, members))
    return {"class": code, "members": members, "in_measure": measured, "adherent": adherent, "rate": rate}


def report(claims):
    year = claims["year"]
    rows = []
    for record in claims["members"]:
        stays = set()
        for admission, discharge in record["stays"]:
            stays.update(range(ordinal(admission), ordinal(discharge) + 1))  # 2.6
        groups = {}
        for position, line in enumerate(record["fills"]):
            groups.setdefault(line["class"], []).append((ordinal(line["date"]), position, line["drug"], line["days"]))
        for code in sorted(groups):
            rows.append({"id": record["id"], "class": code, **member_row(groups[code], stays, year)})
    codes = sorted({r["class"] for r in rows})
    return {
        "plan": claims["plan"],
        "year": year,
        "members": rows,
        "classes": [class_row(code, [r for r in rows if r["class"] == code]) for code in codes],
    }


if __name__ == "__main__":
    import json
    import sys

    with open(sys.argv[1], encoding="utf-8") as handle:
        print(json.dumps(report(json.load(handle)), indent=1))
