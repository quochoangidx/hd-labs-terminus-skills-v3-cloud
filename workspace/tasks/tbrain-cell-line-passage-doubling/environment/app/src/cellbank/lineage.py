"""Passage numbers, PDL and limit flags along the log (SOP sections 4 and 5)."""

from cellbank import growth

NEAR_BAND = 5.0


def flag(pdl, line):
    if pdl >= line["max_pdl"]:
        return "LIMIT"
    if pdl >= line["max_pdl"] - NEAR_BAND:
        return "NEAR"
    return ""


def walk(lines, records):
    """Return the culture rows, each freeze's (pdl, passage) and each record's line."""
    line_of = {}
    current = {}
    frozen = {}
    rows = []
    for rec in records:
        kind = rec["kind"]
        if kind == "thaw":
            line = lines[rec["line"]]
            line_of[rec["id"]] = rec["line"]
            current[rec["line"]] = [line["seed_pdl"], line["seed_passage"] + 1]
        elif kind == "culture":
            name = line_of[rec["source"]]
            line_of[rec["id"]] = name
            state = current[name]
            gained = growth.doublings(rec)
            state[0] += gained
            state[1] += 1
            rows.append(
                {
                    "id": rec["id"],
                    "line": name,
                    "passage": state[1],
                    "doublings": gained,
                    "pdl": state[0],
                    "flag": flag(state[0], lines[name]),
                }
            )
        elif kind == "freeze":
            name = line_of[rec["source"]]
            line_of[rec["id"]] = name
            frozen[rec["id"]] = (current[name][0], current[name][1])
    return rows, frozen, line_of
