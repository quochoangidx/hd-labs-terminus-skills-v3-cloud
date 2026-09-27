"""Expected reports worked out from SOP TM-07, independently of the package.

This module never imports or runs `metalquant`. Every rule the SOP states is
written here from the SOP's own sentences. Where the SOP gives no rule (a blank
level with no blank result, a sample without a CCV on both sides, a
spike or parent that is a non-detect), the instruction keeps the step the shipped
code takes, so the model mirrors that shipped expression and says so; the
verifier also checks those cases against a sealed copy of the shipped package.
"""

from fractions import Fraction


def _line(standards, name):
    # SOP 2: unweighted least squares of response on concentration, intercept fitted
    xs = [std["conc"][name] for std in standards]
    ys = [std["counts"][name] / std["is_counts"] for std in standards]
    n = len(xs)
    mx = sum(xs) / n
    my = sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    slope = sxy / sxx
    return slope, my - slope * mx


def _reading(run, name, line):
    # SOP 3
    slope, intercept = line
    return (run["counts"][name] / run["is_counts"] - intercept) / slope


def reduce_batch(batch):
    analytes = batch["analytes"]
    runs = batch["runs"]
    by_id = {run["id"]: run for run in runs}
    names = [a["name"] for a in analytes]
    limits = {a["name"]: (a["mdl"], a["loq"]) for a in analytes}
    lines = {n: _line(batch["standards"], n) for n in names}
    reading = {n: {r["id"]: _reading(r, n, lines[n]) for r in runs} for n in names}

    levels = {}
    for n in names:
        mdl = limits[n][0]
        blanks = [reading[n][r["id"]] for r in runs if r["kind"] == "blank"]
        results = [value for value in blanks if value >= mdl]
        if results:
            # SOP 4: the mean of the batch's method-blank results
            levels[n] = sum(results) / len(results)
        else:
            # SOP silent (no blank result, so no mean): shipped blanks.blank_level takes
            # the first blank's reading, else 0.0
            levels[n] = blanks[0] if blanks else 0.0

    def corrected(run_id, n):
        return reading[n][run_id] - levels[n]

    def amount(run_id, n):
        # SOP 5: corrected reading times the dilution
        return corrected(run_id, n) * by_id[run_id]["dilution"]

    def is_result(run_id, n):
        return corrected(run_id, n) >= limits[n][0]

    ccv_pass = {n: {} for n in names}
    ccvs = []
    for run in runs:
        if run["kind"] != "ccv":
            continue
        for n in names:
            recovery = reading[n][run["id"]] / run["true"][n] * 100.0
            passed = 90.0 <= round(recovery, 1) <= 110.0  # SOP 6: rounded to one decimal, inclusive
            ccv_pass[n][run["id"]] = passed
            ccvs.append({"id": run["id"], "analyte": n, "recovery": recovery, "pass": passed})

    ccv_positions = [i for i, run in enumerate(runs) if run["kind"] == "ccv"]

    def ccv_ok(index, n):
        before = [i for i in ccv_positions if i < index]
        after = [i for i in ccv_positions if i > index]
        if before and after:
            # SOP 6: both nearest CCVs must have passed
            return ccv_pass[n][runs[before[-1]]["id"]] and ccv_pass[n][runs[after[0]]["id"]]
        # SOP silent: shipped qc.bracket_ok looks only at the nearest CCV before, else True
        return ccv_pass[n][runs[before[-1]]["id"]] if before else True

    samples = []
    for index, run in enumerate(runs):
        if run["kind"] not in ("sample", "spike"):
            continue
        for n in names:
            mdl, loq = limits[n]
            c = corrected(run["id"], n)
            if c < mdl:
                flag, value = "ND", None
            elif c < loq:
                flag, value = "J", amount(run["id"], n)
            else:
                flag, value = "", amount(run["id"], n)
            samples.append(
                {"id": run["id"], "analyte": n, "value": value, "flag": flag, "ccv_ok": ccv_ok(index, n)}
            )

    spikes = []
    for run in runs:
        if run["kind"] != "spike":
            continue
        for n in names:
            s_amt = amount(run["id"], n)
            p_amt = amount(run["parent"], n)
            added = run["added"][n]
            if is_result(run["id"], n) and is_result(run["parent"], n):
                recovery = (s_amt - p_amt) / added * 100.0  # SOP 7
            else:
                # SOP silent: shipped qc.spike_recovery divides by added * dilution
                recovery = (s_amt - p_amt) / (added * run["dilution"]) * 100.0
            spikes.append({"id": run["id"], "analyte": n, "recovery": recovery})

    return {"blank_levels": levels, "samples": samples, "ccvs": ccvs, "spikes": spikes}


def exact_line(standards, name):
    """The calibration line in exact arithmetic, for checking boundary fixtures."""
    xs = [Fraction(std["conc"][name]) for std in standards]
    ys = [Fraction(std["counts"][name]) / Fraction(std["is_counts"]) for std in standards]
    n = len(xs)
    mx = sum(xs) / n
    my = sum(ys) / n
    slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sum((x - mx) ** 2 for x in xs)
    return slope, my - slope * mx
