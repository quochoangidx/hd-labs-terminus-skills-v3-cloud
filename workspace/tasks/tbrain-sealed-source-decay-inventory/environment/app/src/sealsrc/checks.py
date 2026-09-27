"""Per-entry determinations: exemption, leak tests, decay-to-disposal (sections 4, 5 and 7)."""

from .dates import elapsed_days
from .nuclides import exempt_quantity, half_life_days, leak_class

LEAK_THRESHOLD_BQ = {"beta-gamma": 3.7e6, "alpha": 3.7e5}
LEAK_INTERVAL_DAYS = 182
SHORT_LIVED_DAYS = 120


def is_exempt(nuclide, activity_bq, daughter_bq):
    """True when the entry is at or below the exempt quantity of its nuclide."""
    return activity_bq <= exempt_quantity(nuclide)


def last_leak_test(entry):
    """Date of the entry's last leak test, or None when none is on record."""
    wipes = entry["leak_tests"]
    if not wipes:
        return None
    return wipes[-1]["date"]


def leak_test_due(entry, activity_bq, survey_date):
    """True when the entry has to be leak tested on the survey date."""
    cls = leak_class(entry["nuclide"])
    if cls is None:
        return False
    if entry["ref_bq"] < LEAK_THRESHOLD_BQ[cls]:
        return False
    last = last_leak_test(entry)
    if last is None:
        return True
    return elapsed_days(last, survey_date) > LEAK_INTERVAL_DAYS


def disposal_eligible(nuclide, ref_bq, activity_bq, days):
    """True when a short-lived entry has decayed far enough to be disposed of."""
    if half_life_days(nuclide) > SHORT_LIVED_DAYS:
        return False
    return activity_bq <= ref_bq / 1000.0
