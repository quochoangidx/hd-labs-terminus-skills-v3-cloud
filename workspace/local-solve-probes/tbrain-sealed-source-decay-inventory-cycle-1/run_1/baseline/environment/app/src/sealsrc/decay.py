"""Decay correction of certificate activities (manual section 3)."""

import math

from .nuclides import daughter_of, half_life_days


def activity_on(ref_bq, nuclide, days):
    """Activity of the parent nuclide `days` after the certificate's reference date."""
    return ref_bq * math.exp(-days / half_life_days(nuclide))


def daughter_activity(nuclide, parent_bq):
    """Activity of the equilibrium daughter, 0.0 for a nuclide that has none."""
    daughter, _branching = daughter_of(nuclide)
    if daughter is None:
        return 0.0
    return parent_bq
