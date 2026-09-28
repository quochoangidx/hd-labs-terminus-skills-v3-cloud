"""Charging readings to the stability record's excursion bands."""


def band_of(temp, stability):
    """Name of the band a reading is charged to, or None for a reading in range."""
    if stability.low <= temp <= stability.high:
        return None  # in range (2.1)
    if temp < stability.low:
        # A band below the range holds [lower end, upper end) (2.5).
        for band in stability.bands:
            if band.upper <= stability.low and band.lower <= temp < band.upper:
                return band.name
        return None
    # A band above the range holds (lower end, upper end] (2.5).
    for band in stability.bands:
        if band.lower >= stability.high and band.lower < temp <= band.upper:
            return band.name
    return None


def band_minutes(readings, minutes, stability):
    """Minutes charged to each band of the record over one leg (3.1)."""
    totals = {band.name: 0 for band in stability.bands}
    for reading, spent in zip(readings, minutes):
        name = band_of(reading.temp, stability)
        if name is not None:
            totals[name] += spent
    return totals
