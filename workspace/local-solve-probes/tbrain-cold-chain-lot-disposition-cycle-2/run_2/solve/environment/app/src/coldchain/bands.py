"""Charging readings to the stability record's excursion bands."""


def band_of(temp, stability):
    """Name of the band a reading is charged to, or None for a reading in range."""
    if stability.low <= temp <= stability.high:
        return None
    for band in stability.bands:
        if band.upper <= stability.low:  # a band below the labelled range: [lower, upper)
            if band.lower <= temp < band.upper:
                return band.name
        else:  # a band above the labelled range: (lower, upper]
            if band.lower < temp <= band.upper:
                return band.name
    return None


def band_minutes(readings, minutes, stability):
    """Minutes charged to each band of the record over one leg."""
    totals = {band.name: 0 for band in stability.bands}
    for reading, spent in zip(readings, minutes):
        name = band_of(reading.temp, stability)
        if name is not None:
            totals[name] += spent
    return totals
