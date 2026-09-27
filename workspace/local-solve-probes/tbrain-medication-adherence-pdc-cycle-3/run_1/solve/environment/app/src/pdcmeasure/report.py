"""The measure report."""

from .claims import by_class, member, stay_days
from .classes import class_row
from .days import text
from .pdc import figures


def build_report(claims):
    year = claims["year"]
    rows = []
    for record in claims["members"]:
        person = member(record)
        stays = stay_days(person.stays)
        groups = by_class(person.fills)
        for code in sorted(groups):
            row = figures(groups[code], stays, year)
            row["index"] = text(row["index"])
            rows.append({"id": person.id, "class": code, **row})
    classes = [class_row(code, [r for r in rows if r["class"] == code]) for code in sorted({r["class"] for r in rows})]
    return {"plan": claims["plan"], "year": year, "members": rows, "classes": classes}
