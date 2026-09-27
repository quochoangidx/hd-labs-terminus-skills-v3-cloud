"""Storage-location postings (manual section 6)."""

from .nuclides import exempt_quantity


def location_rows(entries, locations):
    """One posting per storage location, in the order the inventory lists the locations."""
    held = {loc["id"]: 0.0 for loc in locations}
    count = {loc["id"]: 0 for loc in locations}
    for entry in entries:
        if entry["ref_bq"] <= exempt_quantity(entry["nuclide"]):
            continue
        held[entry["location"]] += entry["ref_bq"]
        count[entry["location"]] += 1
    rows = []
    for loc in locations:
        total = held[loc["id"]]
        limit = loc["limit_bq"]
        rows.append({
            "id": loc["id"],
            "held_bq": total,
            "sources": count[loc["id"]],
            "fraction_of_limit": total / limit,
            "over_limit": total > limit,
        })
    return rows
