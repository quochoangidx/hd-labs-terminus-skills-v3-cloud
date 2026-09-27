"""The disposition report the driver prints."""

def hours(minutes):
    """Minutes as hours, rounded to the nearest hundredth of an hour (1.2).

    A whole number of minutes never falls halfway between two hundredths.
    """
    hundredths, rest = divmod(int(minutes) * 100, 60)
    if rest * 2 > 60:
        hundredths += 1
    return hundredths / 100


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
