"""Calibration line and readings (SOP sections 2 and 3)."""


def response(counts, is_counts):
    return counts / is_counts


def fit_line(standards, analyte):
    """Return (slope, intercept) of the analyte's OLS calibration line."""
    xs = [std["conc"][analyte] for std in standards]
    ys = [response(std["counts"][analyte], std["is_counts"]) for std in standards]
    n = len(xs)
    mx = sum(xs) / n
    my = sum(ys) / n
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    sxx = sum((x - mx) * (x - mx) for x in xs)
    slope = sxy / sxx
    return slope, my - slope * mx


def reading(run, analyte, line):
    slope, intercept = line
    return (response(run["counts"][analyte], run["is_counts"]) - intercept) / slope
