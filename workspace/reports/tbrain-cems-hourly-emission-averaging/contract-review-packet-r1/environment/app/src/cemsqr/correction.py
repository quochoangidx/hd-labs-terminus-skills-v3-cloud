"""Oxygen correction and mass rate."""

from fractions import Fraction

from .rounding import half_up

AMBIENT_O2 = 210  # tenths of a per cent
O2_CAP = 190  # tenths of a per cent
LB_PER_SCF_PPM = Fraction(1194, 10**10)


def corrected(nox, o2, reference):
    """NOx (tenths of a ppm) corrected to the reference oxygen, in tenths of a ppm."""
    o2 = min(o2, O2_CAP)
    return half_up(nox * Fraction(AMBIENT_O2 - reference) / (AMBIENT_O2 - o2))


def mass_rate(nox, flow):
    """Pounds per hour, in tenths, from NOx in tenths of a ppm and flow in scfh."""
    return half_up(LB_PER_SCF_PPM * 10 * Fraction(nox, 10) * flow)
