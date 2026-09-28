"""Expectation model for SOP QP-7, re-derived from the SOP text alone.

It never imports or runs the package under repair. Replicate and cut-off
decisions are made on exact hundredths of a cycle (1.1 gives Cts to two
decimals), everything else in floating point. Within the limits of section 1
the SOP gives a rule for every reported value, so no value is taken from the
shipped package.
"""

import math
from fractions import Fraction

CUTOFF = 3500  # 2.2, hundredths of a cycle
EARLIEST = 1000  # 2.2
OUTLIER = Fraction(1, 2)  # 4.1, cycles


def hundredths(ct):
    """A Ct as an exact count of hundredths of a cycle (1.1: two decimals at most)."""
    return int(Fraction(str(ct)) * 100)


def determined(ct):
    return ct != "Undetermined"


def reportable(cts):
    """2.2: determined unknown wells with a Ct from 10.00 up to and including 35.00."""
    return [ct for ct in cts if determined(ct) and EARLIEST <= hundredths(ct) <= CUTOFF]


def median(values):
    """4.1: for an even count, the lower of the middle two."""
    s = sorted(values)
    return s[(len(s) - 1) // 2]


def not_outliers(reps):
    """4.1: with three or more reportable replicates, drop those more than 0.50 from the median."""
    if len(reps) < 3:
        return list(reps)
    exact = [Fraction(hundredths(ct), 100) for ct in reps]
    mid = median(exact)
    return [ct for ct, x in zip(reps, exact) if abs(x - mid) <= OUTLIER]


def mean_ct(cts):
    """4.2 / 4.3: mean of the reportable replicates that are not outliers; None when not detected."""
    reps = reportable(cts)
    if not reps:
        return None
    kept = not_outliers(reps)  # never empty: the median is one of the replicates
    return math.fsum(float(ct) for ct in kept) / len(kept)


def curve_points(standards):
    """2.4: levels with two or more determined wells; (log10 quantity, mean Ct)."""
    levels = {}
    for quantity, ct in standards:
        levels.setdefault(float(quantity), []).append(ct)
    points = []
    for quantity in sorted(levels):
        cts = [float(ct) for ct in levels[quantity] if determined(ct)]
        if len(cts) >= 2:
            points.append((math.log10(quantity), math.fsum(cts) / len(cts)))
    return points


def fitted_slope(points):
    """2.5: least-squares slope of curve-point Ct against position."""
    n = len(points)
    xbar = math.fsum(x for x, _ in points) / n
    ybar = math.fsum(y for _, y in points) / n
    num = math.fsum((x - xbar) * (y - ybar) for x, y in points)
    den = math.fsum((x - xbar) * (x - xbar) for x, _ in points)
    return num / den


def factor_of(standards):
    """2.5/3.1: 10^(-1/s) through two or more curve points, no ceiling; 2 with fewer."""
    points = curve_points(standards)
    if len(points) >= 2:
        return 10.0 ** (-1.0 / fitted_slope(points))
    return 2.0


def is_contaminated(ntc_cts):
    """2.6: an NTC well with a Ct at or below the cut-off cycle (an early one included)."""
    return any(determined(ct) and hundredths(ct) <= CUTOFF for ct in ntc_cts)


def group(plate):
    unknowns, standards, ntcs = {}, {}, {}
    for w in plate["wells"]:
        if w["kind"] == "unknown":
            unknowns.setdefault((w["sample"], w["gene"]), []).append(w["ct"])
        elif w["kind"] == "standard":
            standards.setdefault(w["gene"], []).append((w["quantity"], w["ct"]))
        elif w["kind"] == "ntc":
            ntcs.setdefault(w["gene"], []).append(w["ct"])
    return unknowns, standards, ntcs


def report(plate):
    unknowns, standards, ntcs = group(plate)
    refs = list(plate["reference_genes"])
    targets = list(plate["target_genes"])
    genes = refs + targets
    cal = plate["calibrator"]
    factor = {g: factor_of(standards.get(g, [])) for g in genes}
    dirty = {g: is_contaminated(ntcs.get(g, [])) for g in genes}
    means = {key: mean_ct(cts) for key, cts in unknowns.items()}

    def mct(sample, gene):
        return means.get((sample, gene))

    samples = sorted({s for s, _ in unknowns})
    results = []
    for s in samples:
        for t in targets:
            flags = []
            if dirty[t] or any(dirty[g] for g in refs):
                flags.append("ntc")
            if any(mct(x, g) is None for g in refs for x in (s, cal)):
                flags.append("ref")
            if mct(s, t) is None or mct(cal, t) is None:
                flags.append("nd")
            fold = None
            if not flags:
                log_rq_target = (mct(cal, t) - mct(s, t)) * math.log(factor[t])
                log_nf = math.fsum((mct(cal, g) - mct(s, g)) * math.log(factor[g]) for g in refs) / len(refs)
                fold = math.exp(log_rq_target - log_nf)
            results.append({"sample": s, "gene": t, "mean_ct": mct(s, t), "fold_change": fold, "flags": flags})
    return {
        "plate": plate["plate"],
        "genes": [{"gene": g, "factor": factor[g], "contaminated": dirty[g]} for g in genes],
        "results": results,
    }


# ---- section 1 limits, as an executable predicate over a plate --------------------------


def within_limits(plate):
    """True when the plate keeps every limit of SOP section 1 (and follows the README)."""
    refs, targets = plate["reference_genes"], plate["target_genes"]
    genes = refs + targets
    if not (1 <= len(refs) <= 4 and 1 <= len(targets) <= 8 and len(set(genes)) == len(genes)):
        return False
    wells = plate["wells"]
    if not 1 <= len(wells) <= 384:
        return False
    for w in wells:
        ct = w["ct"]
        if determined(ct):
            h = Fraction(str(ct)) * 100
            if h.denominator != 1 or not 500 <= h <= 4500:
                return False
        if w["kind"] == "standard" and not 0.001 <= w["quantity"] <= 1e8:
            return False
    unknowns, standards, ntcs = group(plate)
    samples = {s for s, _ in unknowns}
    if not 1 <= len(samples) <= 48 or plate["calibrator"] not in samples:
        return False
    for s in samples:
        for g in genes:
            if not 1 <= len(unknowns.get((s, g), [])) <= 6:
                return False
    for g in genes:
        levels = {}
        for q, ct in standards.get(g, []):
            levels.setdefault(float(q), []).append(ct)
        if len(levels) > 8 or any(not 1 <= len(v) <= 4 for v in levels.values()):
            return False
        pts = curve_points(standards.get(g, []))
        if len(pts) >= 2 and not -4.20 <= fitted_slope(pts) <= -2.90:
            return False
        if len(ntcs.get(g, [])) > 4:
            return False
    for cts in unknowns.values():
        reps = reportable(cts)
        if not reps:
            continue
        exact = [Fraction(hundredths(ct), 100) for ct in reps]
        mid = median(exact)
        if any(abs(x - mid) == OUTLIER for x in exact):
            return False
    return True


def trap_inputs(plate):
    """Which trap inputs a plate carries.

    T1: a dilution level whose determined wells a replicate rule would change (a well outside
        10.00-35.00, or three or more wells with one more than 0.50 from their lower median).
    T2: an NTC well with a Ct earlier than 10.00.
    """
    _unknowns, standards, ntcs = group(plate)
    out = set()
    for pairs in standards.values():
        levels = {}
        for q, ct in pairs:
            if determined(ct):
                levels.setdefault(float(q), []).append(ct)
        for cts in levels.values():
            if len(cts) < 2:
                continue
            if any(not EARLIEST <= hundredths(ct) <= CUTOFF for ct in cts) or len(not_outliers(cts)) != len(cts):
                out.add("T1")
    if any(determined(ct) and hundredths(ct) < EARLIEST for cts in ntcs.values() for ct in cts):
        out.add("T2")
    return out
