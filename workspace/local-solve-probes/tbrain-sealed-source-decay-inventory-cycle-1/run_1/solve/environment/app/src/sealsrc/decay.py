"""Decay correction of certificate activities (manual section 3)."""

from .nuclides import daughter_of, half_life_days


def activity_on(ref_bq, nuclide, days):
    """Activity of the parent nuclide `days` after the certificate's reference date."""
    return ref_bq * 2.0 ** (-days / half_life_days(nuclide))


def daughter_activity(nuclide, parent_bq):
    """Activity of the equilibrium daughter, 0.0 for a nuclide that has none."""
    daughter, branching = daughter_of(nuclide)
    if daughter is None:
        return 0.0
    return parent_bq * branching
