"""Charging readings to the stability record's excursion bands."""


def band_of(temp, stability):
    """Name of the band a reading is charged to, or None for a reading in range."""
    if stability.low <= temp <= stability.high:  # 2.1: both labelled limits are in range
        return None
    if temp < stability.low:
        # 2.5: a band below the range holds its lower end up to but not including its upper end
        holding = [band for band in stability.bands if band.lower <= temp < band.upper]
    else:
        # 2.5: a band above the range holds above its lower end up to and including its upper end
        holding = [band for band in stability.bands if band.lower < temp <= band.upper]
    if holding:
        return holding[0].name
    # Outside the table's span, which 1.4 excludes: charge the nearest band of the record.
    return min(stability.bands, key=lambda band: min(abs(temp - band.lower), abs(temp - band.upper))).name


def band_minutes(readings, minutes, stability):
    """Minutes charged to each band of the record over one leg (3.1)."""
    totals = {band.name: 0 for band in stability.bands}
    for reading, spent in zip(readings, minutes):
        name = band_of(reading.temp, stability)
        if name is not None:
            totals[name] += spent
    return totals
