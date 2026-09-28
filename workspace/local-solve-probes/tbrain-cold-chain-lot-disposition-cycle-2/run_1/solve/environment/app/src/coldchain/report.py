"""The disposition report the driver prints."""


def hours(minutes):
    """Minutes as hours, rounded to the nearest hundredth of an hour (1.2)."""
    if isinstance(minutes, int):
        # hundredths of an hour = minutes * 100 / 60 = minutes * 5 / 3, rounded to
        # the nearest whole hundredth; a whole number of minutes never lands halfway.
        numerator, denominator = minutes * 5, 3
        whole, rest = divmod(numerator, denominator)
        if 2 * rest >= denominator:
            whole += 1
        return whole / 100
    return round(minutes / 60, 2)


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
