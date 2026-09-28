"""The survey report: one row per inventory entry and one posting per storage location."""

from .checks import disposal_eligible, is_exempt, leak_test_due
from .dates import elapsed_days
from .decay import activity_on, daughter_activity
from .locations import location_rows


def entry_row(entry, survey_date):
    """Report row of one inventory entry."""
    nuclide = entry["nuclide"]
    days = elapsed_days(entry["ref_date"], survey_date)
    activity = activity_on(entry["ref_bq"], nuclide, days)
    daughter = daughter_activity(nuclide, activity)
    return {
        "id": entry["id"],
        "nuclide": nuclide,
        "location": entry["location"],
        "activity_bq": activity,
        "daughter_bq": daughter,
        "exempt": is_exempt(nuclide, activity, daughter),
        "leak_test_due": leak_test_due(entry, activity, survey_date),
        "disposal_eligible": disposal_eligible(nuclide, entry["ref_bq"], activity, days),
    }


def survey(inventory):
    """Survey report for an inventory (a dict read from the inventory JSON file)."""
    survey_date = inventory["survey_date"]
    rows = [entry_row(entry, survey_date) for entry in inventory["sources"]]
    return {
        "survey_date": survey_date,
        "sources": rows,
        "locations": location_rows(
            inventory["sources"],
            inventory["locations"],
            [row["activity_bq"] for row in rows],
        ),
    }
