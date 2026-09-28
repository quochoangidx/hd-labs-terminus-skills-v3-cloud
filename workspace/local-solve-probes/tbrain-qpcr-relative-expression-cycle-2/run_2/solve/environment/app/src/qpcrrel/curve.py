"""Standard curves and amplification factors."""

import math

from .plate import determined
from .replicates import mean_ct

PERFECT_DOUBLING = 2.0


def curve_points(standards):
    """(log10 quantity, mean Ct) of each dilution level with two or more determined wells."""
    levels = {}
    for quantity, ct in standards:
        levels.setdefault(quantity, []).append(ct)
    points = []
    for quantity, cts in sorted(levels.items()):
        called_cts = determined(cts)
        if len(called_cts) >= 2:
            points.append((math.log10(quantity), mean_ct(called_cts)))
    return points


def slope(points):
    """Least-squares slope of Ct against log10 quantity, in cycles per decade."""
    n = len(points)
    mean_x = sum(x for x, _ in points) / n
    mean_y = sum(y for _, y in points) / n
    sxy = sum((x - mean_x) * (y - mean_y) for x, y in points)
    sxx = sum((x - mean_x) ** 2 for x, _ in points)
    return sxy / sxx


def amplification_factor(standards):
    """Amplification per cycle of one gene's assay (SOP 3.1)."""
    points = curve_points(standards)
    if len(points) < 2:
        return PERFECT_DOUBLING
    return 10 ** (-1.0 / slope(points))
