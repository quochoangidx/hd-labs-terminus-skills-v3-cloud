"""The disposition report the driver prints."""

import math
from fractions import Fraction


def hours(minutes):
    """Minutes as hours, rounded to the nearest hundredth of an hour (1.2)."""
    hundredths = Fraction(int(minutes) * 100, 60)
    nearest = math.floor(hundredths + Fraction(1, 2))
    return nearest / 100


def build_report(stability, results):
    lots = []
    for result in results:
        lots.append(
            {
                "lot": result["lot"],
                "disposition": result["disposition"],
                "band_hours": {name: hours(value) for name, value in result["band_minutes"].items()},
                "remaining_hours": {name: hours(value) for name, value in result["remaining_minutes"].items()},
                "unlogged_hours": hours(result["unlogged_minutes"]),
                "mkt_c": round(result["mkt_c"], 1),
            }
        )
    return {"product": stability.product, "lots": lots}
