"""The disposition report the driver prints."""

from fractions import Fraction

MINUTES_PER_HOUR = 60


def hours(minutes):
    """Minutes as hours, rounded to the nearest hundredth."""
    return round(Fraction(int(minutes) * 100, MINUTES_PER_HOUR)) / 100


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
