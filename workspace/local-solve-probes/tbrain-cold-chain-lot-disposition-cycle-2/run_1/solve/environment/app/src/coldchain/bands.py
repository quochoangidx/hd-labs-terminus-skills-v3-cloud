"""Charging readings to the stability record's excursion bands."""


def band_of(temp, stability):
    """Name of the band a reading is charged to, or None for a reading in range (2.1, 2.5, 2.6)."""
    if stability.low <= temp <= stability.high:
        return None
    below = [band for band in stability.bands if band.upper <= stability.low]
    above = [band for band in stability.bands if band.lower >= stability.high]
    if temp < stability.low:
        # A band below the range holds temperatures from its lower end up to but
        # not including its upper end.
        for band in sorted(below, key=lambda entry: entry.lower):
            if band.lower <= temp < band.upper:
                return band.name
        candidates = sorted(below, key=lambda entry: entry.lower)
    else:
        # A band above the range holds temperatures above its lower end up to and
        # including its upper end.
        for band in sorted(above, key=lambda entry: entry.lower):
            if band.lower < temp <= band.upper:
                return band.name
        candidates = sorted(above, key=lambda entry: entry.lower)
    if not candidates:
        return None
    # Outside the table's span, which section 1.4 does not provide for.
    return candidates[0].name if temp < stability.low else candidates[-1].name


def band_minutes(readings, minutes, stability):
    """Minutes charged to each band of the record over one leg (3.1)."""
    totals = {band.name: 0 for band in stability.bands}
    for reading, spent in zip(readings, minutes):
        name = band_of(reading.temp, stability)
        if name is not None:
            totals[name] += spent
    return totals
