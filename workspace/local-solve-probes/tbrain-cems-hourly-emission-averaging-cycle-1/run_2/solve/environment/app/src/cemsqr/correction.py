"""Oxygen correction and mass rate."""

from fractions import Fraction

from .rounding import half_up

AMBIENT_O2 = 210  # tenths of a per cent
O2_CAP = 190  # tenths of a per cent
FIRING_AMBIENT_O2 = 209  # tenths of a per cent (procedure 2.7)
LB_PER_SCF_PPM = Fraction(1194, 10**10)


def firing_ratio(o2, reference):
    """(209 less the reference oxygen) over (209 less the oxygen average), DRP-4 2.7."""
    return Fraction(FIRING_AMBIENT_O2 - reference) / (FIRING_AMBIENT_O2 - o2)


def is_firing(o2):
    """A valid hour whose oxygen average is below 190 tenths is a firing hour (2.4)."""
    return o2 < O2_CAP


def corrected(nox, o2, reference):
    """NOx (tenths of a ppm) corrected to the reference oxygen, in tenths of a ppm."""
    if is_firing(o2):
        # procedure 3.2: the NOx average times the firing ratio
        return half_up(nox * firing_ratio(o2, reference))
    # No rule settles a non-firing hour's concentration: the package's own
    # calculation and constants stand, on the procedure's averages.
    o2 = min(o2, O2_CAP)
    return half_up(nox * Fraction(AMBIENT_O2 - reference) / (AMBIENT_O2 - o2))


def mass_rate(nox, flow):
    """Pounds per hour, in tenths, from NOx in tenths of a ppm and flow in scfh."""
    return half_up(LB_PER_SCF_PPM * Fraction(nox) * flow)
