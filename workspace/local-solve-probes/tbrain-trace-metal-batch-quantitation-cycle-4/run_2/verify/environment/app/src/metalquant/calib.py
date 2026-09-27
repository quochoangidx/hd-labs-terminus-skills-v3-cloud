"""Calibration line and readings (SOP sections 2 and 3)."""


def response(counts, is_counts):
    return counts / is_counts


def fit_line(standards, analyte):
    """Return (slope, intercept) of the analyte's calibration line.

    Ordinary least squares of response on concentration through every
    standard's point, unweighted, with the intercept fitted (SOP section 2).
    """
    xs = [std["conc"][analyte] for std in standards]
    ys = [response(std["counts"][analyte], std["is_counts"]) for std in standards]
    n = len(xs)
    sx = sum(xs)
    sy = sum(ys)
    sxy = sum(x * y for x, y in zip(xs, ys))
    sxx = sum(x * x for x in xs)
    slope = (n * sxy - sx * sy) / (n * sxx - sx * sx)
    intercept = (sy - slope * sx) / n
    return slope, intercept


def reading(run, analyte, line):
    slope, intercept = line
    return (response(run["counts"][analyte], run["is_counts"]) - intercept) / slope
