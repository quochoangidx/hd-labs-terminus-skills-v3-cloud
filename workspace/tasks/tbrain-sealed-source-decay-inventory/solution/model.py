"""Expected survey reports worked out from manual RPO-7, independently of the package.

This module never imports or runs `sealsrc`. Every figure the manual defines is
written here from the manual's own sentences. The manual gives no elapsed time for
a source whose certificate is dated after the survey date (1.3 speaks only of a
survey on or after the reference date), so the instruction keeps the step the
shipped package takes for it: the shipped day count stops at nought, which leaves
the certificate figure undecayed. The model mirrors that shipped step and says so.
"""

import datetime

YEAR_DAYS = 365.25  # 1.4
SHORT_LIVED_MAX_DAYS = 120  # 1.6
LEAK_INTERVAL_DAYS = 182  # 5.2
LEAK_THRESHOLD = {"beta-gamma": 3.7e6, "alpha": 3.7e5}  # 5.1
WIPE_LEAK_BQ = 185  # 1.7: a wipe below this is a leak test

# Table 2: half-life value, unit, exempt quantity (Bq), leak-test class, branching fraction
# of the listed equilibrium daughter (None when Table 2 lists no daughter).
TABLE_2 = {
    "H-3": ("12.32", "y", 1.0e9, None, None),
    "Na-22": ("2.6018", "y", 1.0e6, "beta-gamma", None),
    "P-32": ("14.268", "d", 1.0e5, "beta-gamma", None),
    "S-35": ("87.37", "d", 1.0e8, "beta-gamma", None),
    "Co-57": ("271.74", "d", 1.0e6, "beta-gamma", None),
    "Co-60": ("5.2713", "y", 1.0e5, "beta-gamma", None),
    "Ni-63": ("101.2", "y", 1.0e8, "beta-gamma", None),
    "Ge-68": ("270.95", "d", 1.0e5, "beta-gamma", 1.0),
    "Sr-90": ("28.79", "y", 1.0e4, "beta-gamma", 1.0),
    "Cd-109": ("461.9", "d", 1.0e6, "beta-gamma", None),
    "I-125": ("59.49", "d", 1.0e6, "beta-gamma", None),
    "Ba-133": ("10.551", "y", 1.0e6, "beta-gamma", None),
    "Cs-137": ("30.08", "y", 1.0e4, "beta-gamma", 0.944),
    "Ir-192": ("73.829", "d", 1.0e4, "beta-gamma", None),
    "Po-210": ("138.376", "d", 1.0e4, "alpha", None),
    "Am-241": ("432.6", "y", 1.0e4, "alpha", None),
    "Cf-252": ("2.645", "y", 1.0e4, "alpha", None),
}


def half_life_days(nuclide):
    # 1.4: a year of half-life is 365.25 days
    value, unit = float(TABLE_2[nuclide][0]), TABLE_2[nuclide][1]
    return value * YEAR_DAYS if unit == "y" else value


def day_number(text):
    # 1.2: actual Gregorian days
    return datetime.date.fromisoformat(text).toordinal()


def days_between(earlier, later):
    return day_number(later) - day_number(earlier)


def elapsed_time(ref_date, survey_date):
    # 1.3: defined for a survey on or after the reference date
    t = days_between(ref_date, survey_date)
    if t < 0:
        # Shipped step: the manual gives no elapsed time here; the shipped day count
        # stops at nought (max(days, 0)), so the certificate figure stands undecayed.
        return 0
    return t


def entry_row(entry, survey_date):
    nuclide = entry["nuclide"]
    _hl, _unit, exempt_q, leak_cls, branching = TABLE_2[nuclide]
    T = half_life_days(nuclide)
    t = elapsed_time(entry["ref_date"], survey_date)
    current = float(entry["ref_bq"]) * 2.0 ** (-t / T)  # 3.1
    daughter = current * branching if branching is not None else 0.0  # 3.2
    total = current + daughter  # 3.3
    exempt = total <= exempt_q  # 4.1
    # 5.1 leak-testable, 5.2 due
    testable = leak_cls is not None and current >= LEAK_THRESHOLD[leak_cls]
    # 1.7 only a wipe below 185 Bq is a leak test; 5.2 the last one is the latest by date
    tests = [day_number(w["date"]) for w in entry["leak_tests"] if w["removable_bq"] < WIPE_LEAK_BQ]
    due = testable and (not tests or day_number(survey_date) - max(tests) > LEAK_INTERVAL_DAYS)
    # 1.6 short-lived, 7.1 eligible once t >= 10 T
    eligible = T <= SHORT_LIVED_MAX_DAYS and t >= 10 * T
    return {
        "id": entry["id"],
        "nuclide": nuclide,
        "location": entry["location"],
        "activity_bq": current,
        "daughter_bq": daughter,
        "exempt": exempt,
        "leak_test_due": due,
        "disposal_eligible": eligible,
    }


def survey(inventory):
    survey_date = inventory["survey_date"]
    entries = inventory["sources"]
    rows = [entry_row(e, survey_date) for e in entries]
    postings = []
    for loc in inventory["locations"]:
        # 1.8 licensed material: certificate (parent) figure above the exempt quantity,
        # however far it has decayed since; 6.1 parent current activity only, inventory order
        stored = [r for e, r in zip(entries, rows)
                  if r["location"] == loc["id"] and float(e["ref_bq"]) > TABLE_2[e["nuclide"]][2]]
        held = 0.0
        for r in stored:
            held += r["activity_bq"]
        limit = loc["limit_bq"]
        postings.append({
            "id": loc["id"],
            "held_bq": held,
            "sources": len(stored),
            "fraction_of_limit": held / limit,  # 6.2
            "over_limit": held > limit,
        })
    return {"survey_date": survey_date, "sources": rows, "locations": postings}


if __name__ == "__main__":
    import json
    import sys

    with open(sys.argv[1], encoding="utf-8") as handle:
        json.dump(survey(json.load(handle)), sys.stdout)
    sys.stdout.write("\n")
