"""The inverse geodesic problem: distance and azimuths between two points.

Vincenty (1975), iterating on the longitude on the auxiliary sphere.
"""

import math

from geodetic.ellipsoid import FLATTENING as F
from geodetic.ellipsoid import SEMI_MAJOR_AXIS as A
from geodetic.ellipsoid import SEMI_MINOR_AXIS as B


def inverse(lat1, lon1, lat2, lon2):
    """``(s12, azi1, azi2)``: metres, and degrees clockwise from north."""
    L = math.radians(lon2 - lon1)
    U1 = math.atan((1 - F) * math.tan(math.radians(lat1)))
    U2 = math.atan((1 - F) * math.tan(math.radians(lat2)))
    sin_u1, cos_u1 = math.sin(U1), math.cos(U1)
    sin_u2, cos_u2 = math.sin(U2), math.cos(U2)
    lam = L
    for _ in range(100):
        sin_lam, cos_lam = math.sin(lam), math.cos(lam)
        sin_sigma = math.hypot(cos_u2 * sin_lam, cos_u1 * sin_u2 - sin_u1 * cos_u2 * cos_lam)
        if sin_sigma == 0:
            return 0.0, 0.0, 0.0
        cos_sigma = sin_u1 * sin_u2 + cos_u1 * cos_u2 * cos_lam
        sigma = math.atan2(sin_sigma, cos_sigma)
        sin_alpha = cos_u1 * cos_u2 * sin_lam / sin_sigma
        cos2_alpha = 1 - sin_alpha * sin_alpha
        cos_2sm = cos_sigma - 2 * sin_u1 * sin_u2 / cos2_alpha if cos2_alpha else 0.0
        C = F / 16 * cos2_alpha * (4 + F * (4 - 3 * cos2_alpha))
        previous = lam
        lam = L + (1 - C) * F * sin_alpha * (
            sigma + C * sin_sigma * (cos_2sm + C * cos_sigma * (-1 + 2 * cos_2sm * cos_2sm))
        )
        if abs(lam - previous) < 1e-12:
            break
    else:
        raise ArithmeticError("Vincenty's iteration did not converge")
    u2 = cos2_alpha * (A * A - B * B) / (B * B)
    k_a = 1 + u2 / 16384 * (4096 + u2 * (-768 + u2 * (320 - 175 * u2)))
    k_b = u2 / 1024 * (256 + u2 * (-128 + u2 * (74 - 47 * u2)))
    delta = k_b * sin_sigma * (
        cos_2sm
        + k_b / 4 * (
            cos_sigma * (-1 + 2 * cos_2sm ** 2)
            - k_b / 6 * cos_2sm * (-3 + 4 * sin_sigma ** 2) * (-3 + 4 * cos_2sm ** 2)
        )
    )
    s12 = B * k_a * (sigma - delta)
    azi1 = math.degrees(math.atan2(cos_u2 * math.sin(lam), cos_u1 * sin_u2 - sin_u1 * cos_u2 * math.cos(lam)))
    azi2 = math.degrees(math.atan2(cos_u1 * math.sin(lam), -sin_u1 * cos_u2 + cos_u1 * sin_u2 * math.cos(lam)))
    return s12, azi1, azi2
