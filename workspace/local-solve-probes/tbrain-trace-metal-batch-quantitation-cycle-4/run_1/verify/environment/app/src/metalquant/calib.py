"""Calibration line and readings (SOP sections 2 and 3)."""


def response(counts, is_counts):
    return counts / is_counts


def fit_line(standards, analyte):
    """Return (slope, intercept) of the analyte's calibration line.

    Ordinary least squares of response on concentration, unweighted, with the
    intercept fitted (SOP section 2).
    """
    xs = [std["conc"][analyte] for std in standards]
    ys = [response(std["counts"][analyte], std["is_counts"]) for std in standards]
    n = len(xs)
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    sxy = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    sxx = sum((x - mean_x) ** 2 for x in xs)
    slope = sxy / sxx
    intercept = mean_y - slope * mean_x
    return slope, intercept


def reading(run, analyte, line):
    slope, intercept = line
    return (response(run["counts"][analyte], run["is_counts"]) - intercept) / slope
