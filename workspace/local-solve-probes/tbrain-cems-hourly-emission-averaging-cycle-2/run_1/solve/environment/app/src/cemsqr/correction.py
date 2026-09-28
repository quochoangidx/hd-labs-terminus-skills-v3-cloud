"""Oxygen correction and mass rate."""

from fractions import Fraction

from .rounding import half_up

AMBIENT_O2 = 210  # tenths of a per cent
O2_CAP = 200  # tenths of a per cent
LB_PER_SCF_PPM = Fraction(1194, 10**10)

DRP_AMBIENT_O2 = 209  # tenths of a per cent (DRP-4 rule 2.7)
FIRING_O2 = 190  # tenths of a per cent (DRP-4 rule 2.4)


def corrected(nox, o2, reference):
    """NOx (tenths of a ppm) corrected to the reference oxygen, in tenths of a ppm.

    Oxygen at or above O2_CAP is held at O2_CAP. No rule of the procedure
    settles a figure for a valid hour that is not a firing hour, so that hour
    keeps this calculation with the package's own constants.
    """
    if o2 < O2_CAP:
        ratio = Fraction(AMBIENT_O2 - reference) / (AMBIENT_O2 - o2)
    else:
        ratio = Fraction(AMBIENT_O2 - reference) / (AMBIENT_O2 - O2_CAP)
    return half_up(nox * ratio)


def firing_ratio(o2, reference):
    """(209 less the reference oxygen) over (209 less the hour's oxygen average)."""
    return Fraction(DRP_AMBIENT_O2 - reference, 1) / (DRP_AMBIENT_O2 - o2)


def firing_corrected(nox, o2, reference):
    """A firing hour's corrected concentration, rounded, in tenths of a ppm."""
    return half_up(nox * firing_ratio(o2, reference))


def mass_rate(nox, flow):
    """Pounds per hour, in tenths, from NOx in tenths of a ppm and flow in scfh."""
    return half_up(LB_PER_SCF_PPM * 10 * Fraction(nox, 10) * flow)
