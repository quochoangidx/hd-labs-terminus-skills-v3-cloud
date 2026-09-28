"""Source-station distance used by the magnitude."""

import math


def station_distance_km(epi_km, depth_km):
    """Distance, in kilometres, a station's magnitude is corrected for.

    ``epi_km`` is the epicentral distance the locator gives for the station and
    ``depth_km`` the depth of the event.  The magnitude is corrected for the
    hypocentral distance at every range (rule 3.1); station elevation is not
    used.
    """
    return math.hypot(float(epi_km), float(depth_km))
