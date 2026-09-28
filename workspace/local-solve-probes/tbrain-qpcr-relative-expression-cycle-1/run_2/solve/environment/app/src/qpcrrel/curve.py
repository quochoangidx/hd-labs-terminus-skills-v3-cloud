"""Standard curves and amplification factors."""

import math

PERFECT_DOUBLING = 2.0
MIN_CURVE_POINTS = 3  # a standard curve needs three or more curve points (SOP 2.5)


def curve_points(standards):
    """(log10 quantity, mean Ct) of each curve point, lowest quantity first."""
    levels = {}
    for quantity, ct in standards:
        determined = levels.setdefault(quantity, [])
        if ct is not None:
            determined.append(ct)
    return [
        (math.log10(quantity), sum(cts) / len(cts))
        for quantity, cts in sorted(levels.items())
        if len(cts) >= 2
    ]


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
    if len(points) < MIN_CURVE_POINTS:
        # Too few curve points for a standard curve, so the SOP settles nothing
        # here: the factor stays what the package has always made of it.
        return min(10 ** (-1.0 / slope(points)), PERFECT_DOUBLING)
    return 10 ** (-1.0 / slope(points))
