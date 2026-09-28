"""Storage-location postings (manual section 6)."""

from .nuclides import exempt_quantity


def is_licensed_material(entry):
    """True when the certificate's parent figure is above the exempt quantity (1.8)."""
    return entry["ref_bq"] > exempt_quantity(entry["nuclide"])


def location_rows(entries, locations, activities):
    """One posting per storage location, in the order the inventory lists the locations.

    `activities` gives the current activity of each entry, in inventory order.
    Held activity sums the current activities of the licensed material kept at
    the location (6.1); daughter activity is no part of it.
    """
    held = {loc["id"]: 0.0 for loc in locations}
    count = {loc["id"]: 0 for loc in locations}
    for entry, activity in zip(entries, activities):
        if not is_licensed_material(entry):
            continue
        held[entry["location"]] += activity
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
