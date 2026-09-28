"""Assemble the quarterly NOx report."""

from fractions import Fraction

from .correction import corrected, corrected_firing, is_firing, mass_rate
from .hours import classify, group_hours
from .rolling import operating_days, rolling_days
from .rounding import half_up
from .substitute import fill


def build_report(job):
    reference = job["unit"]["ref_o2"]
    limit = job["unit"]["limit"]
    hours = [classify(hour) for hour in group_hours(job["readings"])]
    for hour in hours:
        if hour["valid"]:
            if is_firing(hour["o2"]):
                # Rule 3.2.
                hour["conc"] = corrected_firing(hour["nox"], hour["o2"], reference)
            else:
                # No rule settles a valid hour that is not a firing hour.
                hour["conc"] = corrected(hour["nox"], hour["o2"], reference)
            # Rule 3.3: the measured NOx average, never a corrected concentration.
            hour["rate"] = mass_rate(hour["nox"], hour["flow"])
    fill(hours)
    operating = [hour for hour in hours if hour["operating"]]
    # Rule 5.1: tenths of a pound per hour times the operating time, to hundredths
    # of a ton of 2,000 pounds.
    mass = sum((Fraction(hour["rate"] * hour["quarters"], 4) for hour in operating),
               Fraction(0))
    return {
        "hours": [{"hour": hour["hour"],
                   "kind": "valid" if hour["valid"] else "substitute",
                   "nox": hour["conc"], "lb": hour["rate"]} for hour in operating],
        "days": rolling_days(operating_days(hours), limit),
        "operating_hours": len(operating),
        "valid_hours": sum(1 for hour in operating if hour["valid"]),
        "nox_tons": half_up(mass / 200),
    }
