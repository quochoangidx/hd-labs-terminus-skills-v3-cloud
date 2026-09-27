"""Source-station distance used by the magnitude."""

import math


def station_distance_km(epi_km, depth_km):
    """Distance, in kilometres, a station's magnitude is corrected for.

    ``epi_km`` is the epicentral distance the locator gives for the station and
    ``depth_km`` the depth of the event.  Rule 3.1: the distance is the
    hypocentral one, at every range, and station elevation is not used.
    """
    return math.sqrt(float(epi_km) ** 2 + float(depth_km) ** 2)
