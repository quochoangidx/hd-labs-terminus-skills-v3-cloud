"""Standard curves and amplification factors."""

import math

from .replicates import NO_CALL_CT

PERFECT_DOUBLING = 2.0


def curve_points(standards):
    """(log10 quantity, mean Ct) of each dilution level, lowest quantity first."""
    levels = {}
    for quantity, ct in standards:
        levels.setdefault(quantity, []).append(NO_CALL_CT if ct is None else ct)
    return [(math.log10(quantity), sum(cts) / len(cts)) for quantity, cts in sorted(levels.items())]


def slope(points):
    """Least-squares slope of Ct against log10 quantity, in cycles per decade."""
    n = len(points)
    mean_x = sum(x for x, _ in points) / n
    mean_y = sum(y for _, y in points) / n
    sxy = sum((x - mean_x) * (y - mean_y) for x, y in points)
    sxx = sum((x - mean_x) ** 2 for x, _ in points)
    return sxy / sxx


def amplification_factor(standards):
    """Amplification per cycle of one gene's assay."""
    points = curve_points(standards)
    if len(points) < 2:
        return PERFECT_DOUBLING
    return min(10 ** (-1.0 / slope(points)), PERFECT_DOUBLING)
