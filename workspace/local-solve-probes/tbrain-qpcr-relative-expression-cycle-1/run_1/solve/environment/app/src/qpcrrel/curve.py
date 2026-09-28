"""Standard curves and amplification factors."""

import math

PERFECT_DOUBLING = 2.0

MIN_WELLS_PER_POINT = 2  # SOP 2.4: a curve point needs two or more determined wells
MIN_CURVE_POINTS = 3  # SOP 2.5: a standard curve is fitted through three or more points


def curve_points(standards):
    """(log10 quantity, mean Ct) of each curve point, lowest quantity first (SOP 2.4)."""
    levels = {}
    for quantity, ct in standards:
        determined = levels.setdefault(quantity, [])
        if ct is not None:
            determined.append(ct)
    return [
        (math.log10(quantity), sum(cts) / len(cts))
        for quantity, cts in sorted(levels.items())
        if len(cts) >= MIN_WELLS_PER_POINT
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
    if len(points) >= MIN_CURVE_POINTS:
        return 10 ** (-1.0 / slope(points))
    # The SOP defines no standard curve here, so the package's own reading stands.
    if len(points) < 2:
        return PERFECT_DOUBLING
    return min(10 ** (-1.0 / slope(points)), PERFECT_DOUBLING)
