"""Geodesics on the WGS84 ellipsoid."""

from geodetic.ellipsoid import FLATTENING, SEMI_MAJOR_AXIS
from geodetic.inverse import inverse

__all__ = ["FLATTENING", "SEMI_MAJOR_AXIS", "inverse"]
