"""Oxygen correction and mass rate."""

from fractions import Fraction

from .rounding import half_up

AMBIENT_O2 = 210  # tenths of a per cent
O2_CAP = 190  # tenths of a per cent
LB_PER_SCF_PPM = Fraction(1194, 10**10)

FIRING_AIR_O2 = 209  # tenths of a per cent, rule 2.7
FIRING_O2 = 190  # tenths of a per cent, rule 2.4


def is_firing(o2_average):
    """Rule 2.4: a firing hour's oxygen average is below 190 tenths of a per cent."""
    return o2_average < FIRING_O2


def firing_ratio(o2_average, reference):
    """Rule 2.7: (209 less the reference oxygen) over (209 less the oxygen average)."""
    return Fraction(FIRING_AIR_O2 - reference, 1) / (FIRING_AIR_O2 - o2_average)


def corrected_firing(nox, o2, reference):
    """Rule 3.2: a firing hour's corrected concentration, in tenths of a ppm."""
    return half_up(nox * firing_ratio(o2, reference))


def corrected(nox, o2, reference):
    """NOx (tenths of a ppm) corrected to the reference oxygen, in tenths of a ppm."""
    o2 = min(o2, O2_CAP)
    return half_up(nox * Fraction(AMBIENT_O2 - reference) / (AMBIENT_O2 - o2))


def mass_rate(nox, flow):
    """Pounds per hour, in tenths, from NOx in tenths of a ppm and flow in scfh."""
    return half_up(LB_PER_SCF_PPM * 10 * Fraction(nox, 10) * flow)
