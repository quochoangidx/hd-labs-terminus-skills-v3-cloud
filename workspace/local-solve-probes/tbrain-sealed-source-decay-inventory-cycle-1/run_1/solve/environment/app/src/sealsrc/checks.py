"""Per-entry determinations: exemption, leak tests, decay-to-disposal (sections 4, 5 and 7)."""

from .dates import elapsed_days
from .nuclides import exempt_quantity, half_life_days, leak_class

LEAK_THRESHOLD_BQ = {"beta-gamma": 3.7e6, "alpha": 3.7e5}
LEAK_INTERVAL_DAYS = 182
SHORT_LIVED_DAYS = 120
LEAK_TEST_MAX_REMOVABLE_BQ = 185.0
DISPOSAL_HALF_LIVES = 10


def is_exempt(nuclide, activity_bq, daughter_bq):
    """True when the entry's total activity is at or below the exempt quantity (4.1)."""
    return activity_bq + daughter_bq <= exempt_quantity(nuclide)


def last_leak_test(entry):
    """Date of the entry's last leak test, or None when none is on record.

    Only a wipe below 185 Bq is a leak test (1.7), and the last one is the
    latest by date, whatever order the counting room returned the wipes in.
    """
    dates = [
        wipe["date"]
        for wipe in entry["leak_tests"]
        if wipe["removable_bq"] < LEAK_TEST_MAX_REMOVABLE_BQ
    ]
    if not dates:
        return None
    return max(dates)


def leak_test_due(entry, activity_bq, survey_date):
    """True when the entry has to be leak tested on the survey date."""
    cls = leak_class(entry["nuclide"])
    if cls is None:
        return False
    if activity_bq < LEAK_THRESHOLD_BQ[cls]:
        return False
    last = last_leak_test(entry)
    if last is None:
        return True
    return elapsed_days(last, survey_date) > LEAK_INTERVAL_DAYS


def disposal_eligible(nuclide, ref_bq, activity_bq, days):
    """True when a short-lived entry has seen ten half-lives elapse (7.1)."""
    half_life = half_life_days(nuclide)
    if half_life > SHORT_LIVED_DAYS:
        return False
    return days >= DISPOSAL_HALF_LIVES * half_life
