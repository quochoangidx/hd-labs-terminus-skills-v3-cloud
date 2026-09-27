"""Source-station distance used by the magnitude."""


def station_distance_km(epi_km, depth_km):
    """Distance, in kilometres, a station's magnitude is corrected for.

    ``epi_km`` is the epicentral distance the locator gives for the station and
    ``depth_km`` the depth of the event.
    """
    return float(epi_km)
