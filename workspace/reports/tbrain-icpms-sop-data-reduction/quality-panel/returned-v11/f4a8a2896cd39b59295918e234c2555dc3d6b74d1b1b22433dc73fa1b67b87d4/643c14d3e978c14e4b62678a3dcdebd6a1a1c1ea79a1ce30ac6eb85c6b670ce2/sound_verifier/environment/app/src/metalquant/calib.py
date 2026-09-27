"""Calibration line and readings (SOP sections 2 and 3)."""


def response(counts, is_counts):
    return counts / is_counts


def fit_line(standards, analyte):
    """Return (slope, intercept) of the analyte's calibration line."""
    xs = [std["conc"][analyte] for std in standards]
    ys = [response(std["counts"][analyte], std["is_counts"]) for std in standards]
    sxy = sum(x * y for x, y in zip(xs, ys))
    sxx = sum(x * x for x in xs)
    return sxy / sxx, 0.0


def reading(run, analyte, line):
    slope, intercept = line
    return (response(run["counts"][analyte], run["is_counts"]) - intercept) / slope
