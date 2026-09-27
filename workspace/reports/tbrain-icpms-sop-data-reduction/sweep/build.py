"""build.py: write the Sound Verifier sweep (blueprint section 5, C1-C18) as Oracle mutants.

Each mutant is the reference fix plus one textual edit, written as a patch against the
shipped environment (paths app/src/..., the format wrong_path_runner.py applies).
Alternatives are contract-valid rewrites that must score reward 1.
Run: python3 build.py  -> sweep/<id>.patch and sweep/catalog.json
"""

import difflib
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
TASK = HERE.parents[2] / "tasks" / "tbrain-icpms-sop-data-reduction"
SRC = TASK / "environment" / "app" / "src"
T = "tests/test_outputs.py::"

# id -> (class, [(file, old, new)], expected failing witnesses, rationale)
MUTANTS = {
    # C1: every visible sentence is a promise
    "c1-ccv-recovery-reported-rounded": ("C1", [("report.py", '"recovery": recovery, "pass"', '"recovery": round(recovery, 1), "pass"')],
        ["test_ccv_pass_on_rounded_recovery_inclusive"], "SOP 6: the reported recovery is not rounded"),
    "c1-values-rounded": ("C1", [("report.py", '"value": None if mark == "ND" else value', '"value": None if mark == "ND" else round(value, 3)')],
        ["test_calibration_line_has_fitted_intercept"], "SOP 8: numbers are not rounded"),
    "c1-spike-recovery-null-for-nd": ("C1", [("report.py", 'spikes.append({"id": run["id"], "analyte": name, "recovery": recovery})',
        'spikes.append({"id": run["id"], "analyte": name, "recovery": recovery if detected[name][run["id"]] and detected[name][run["parent"]] else None})')],
        ["test_nondetect_spikes_keep_shipped_recovery"], "SOP 8: spike recovery is always a number"),
    "c1-blanks-before-first-sample-only": ("C1", [("blanks.py", 'results = [readings[run["id"]] for run in runs if run["kind"] == "blank" and readings[run["id"]] >= mdl]',
        'first = next((i for i, run in enumerate(runs) if run["kind"] in ("sample", "spike")), len(runs))\n    results = [readings[run["id"]] for run in runs[:first] if run["kind"] == "blank" and readings[run["id"]] >= mdl]')],
        ["test_blank_level_is_mean_of_results_anywhere"], "SOP 4: every blank wherever it sits in the run order"),
    # C2/C3/C5/C6: ceilings, bounds reached, cardinalities, parameter caps
    "c5-runs-capped-64": ("C5", [("report.py", '    runs = batch["runs"]', '    runs = batch["runs"][:64]')],
        ["test_capacity_batch"], "SOP 1: up to eighty runs"),
    "c5-analytes-capped-3": ("C5", [("report.py", '    analytes = batch["analytes"]', '    analytes = batch["analytes"][:3]')],
        ["test_capacity_batch"], "SOP 1: up to four analytes"),
    "c5-standards-capped-6": ("C5", [("calib.py", '    xs = [std["conc"][analyte] for std in standards]\n    ys = [response(std["counts"][analyte], std["is_counts"]) for std in standards]',
        '    standards = standards[:6]\n    xs = [std["conc"][analyte] for std in standards]\n    ys = [response(std["counts"][analyte], std["is_counts"]) for std in standards]')],
        ["test_capacity_batch"], "SOP 1: up to eight standards"),
    "c6-dilution-capped-500": ("C6", [("samples.py", "    return (reading - level) * dilution", "    return (reading - level) * min(dilution, 500)")],
        ["test_blank_comes_off_before_dilution"], "SOP 1: dilution up to 1000"),
    "c6-added-capped-500": ("C6", [("qc.py", "        return (spike_amount - parent_amount) / added * 100.0", "        return (spike_amount - parent_amount) / min(added, 500) * 100.0")],
        ["test_spike_recovery_of_results"], "SOP 1: added up to 1000"),
    "c3-mdl-capped-10": ("C3", [("report.py", '    analytes = batch["analytes"]', '    analytes = [dict(a, mdl=min(a["mdl"], 10.0)) for a in batch["analytes"]]')],
        ["test_section_one_limits_reached"], "SOP 1: mdl up to 100"),
    "c3-loq-capped-100": ("C3", [("report.py", '    analytes = batch["analytes"]', '    analytes = [dict(a, loq=min(a["loq"], 100.0)) for a in batch["analytes"]]')],
        ["test_section_one_limits_reached"], "SOP 1: loq up to 1000"),
    "c3-conc-capped-600": ("C3", [("calib.py", '    xs = [std["conc"][analyte] for std in standards]', '    xs = [min(std["conc"][analyte], 600.0) for std in standards]')],
        ["test_section_one_limits_reached"], "SOP 1: standard concentrations up to 1000"),
    "c3-counts-capped-1e8": ("C3", [("calib.py", "def response(counts, is_counts):\n    return counts / is_counts", "def response(counts, is_counts):\n    return min(counts, 1e8) / is_counts")],
        ["test_section_one_limits_reached"], "SOP 1: analyte counts up to 10^9"),
    "c3-is-counts-capped-1e7": ("C3", [("calib.py", "def response(counts, is_counts):\n    return counts / is_counts", "def response(counts, is_counts):\n    return counts / min(is_counts, 1e7)")],
        ["test_section_one_limits_reached"], "SOP 1: is_counts up to 10^9"),
    # C4: floors and zeros
    "c4-no-blank-level-none": ("C4", [("blanks.py", "    return 0.0", "    return None if not any(r['kind'] == 'blank' for r in runs) else 0.0")],
        ["test_batch_without_blank_results_keeps_shipped_level"], "a batch with no blank at all keeps the shipped level 0.0"),
    "c4-zero-counts-nd": ("C4", [("calib.py", "def response(counts, is_counts):\n    return counts / is_counts", "def response(counts, is_counts):\n    return counts / is_counts if counts else float('nan')")],
        ["test_readings_below_nought_are_not_clamped"], "counts of 0 are in the domain"),
    # C8: signs and rounding
    "c8-ccv-floor-one-decimal": ("C8", [("qc.py", "    return 90.0 <= round(recovery, 1) <= 110.0", "    return 90.0 <= math.floor(recovery * 10) / 10 <= 110.0"), ("qc.py", '"""CCV checks', 'import math\n"""CCV checks')],
        ["test_ccv_pass_on_rounded_recovery_inclusive"], "rounding, not truncation, at the lower limit"),
    "c8-ccv-ceil-one-decimal": ("C8", [("qc.py", "    return 90.0 <= round(recovery, 1) <= 110.0", "    return 90.0 <= math.ceil(recovery * 10) / 10 <= 110.0"), ("qc.py", '"""CCV checks', 'import math\n"""CCV checks')],
        ["test_ccv_pass_on_rounded_recovery_inclusive"], "rounding, not ceiling, at the upper limit"),
    "c8-spike-recovery-clamped": ("C8", [("qc.py", "        return (spike_amount - parent_amount) / added * 100.0", "        return max(0.0, (spike_amount - parent_amount) / added * 100.0)")],
        ["test_spike_recovery_of_results"], "a spike below its parent gives a negative recovery"),
    "c8-fallback-level-abs": ("C8", [("blanks.py", '            return readings[run["id"]]', '            return abs(readings[run["id"]])')],
        ["test_batch_without_blank_results_keeps_shipped_level"], "the shipped fallback level may be below nought"),
    "c8-amount-clamped": ("C8", [("samples.py", "    return (reading - level) * dilution", "    return max(0.0, reading - level) * dilution")],
        ["test_nondetect_spikes_keep_shipped_recovery"], "amounts below nought are not clamped (they feed non-detect spike recoveries)"),
    # C10: parameters never constant
    "c10-first-analyte-limits": ("C10", [("report.py", '            mark = samples.flag(readings[name][run["id"]], levels[name], run["dilution"], a)',
        '            mark = samples.flag(readings[name][run["id"]], levels[name], run["dilution"], analytes[0])')],
        ["test_flags_just_either_side_of_mdl_and_loq"], "each analyte has its own mdl and loq"),
    # C11: accumulators the repair separates
    "c11-blank-result-any-analyte": ("C11", [("report.py", '    levels = {a["name"]: blanks.blank_level(runs, a["name"], readings[a["name"]], a["mdl"]) for a in analytes}',
        '    hits = [r["id"] for r in runs if r["kind"] == "blank" and any(readings[b["name"]][r["id"]] >= b["mdl"] for b in analytes)]\n'
        '    levels = {a["name"]: (sum(readings[a["name"]][i] for i in hits) / len(hits) if hits else blanks.blank_level(runs, a["name"], readings[a["name"]], a["mdl"])) for a in analytes}')],
        ["test_nondetect_blanks_stay_out_of_the_mean"], "a blank is a result per analyte, not per run"),
    # C12: silent inputs / plausible guards
    "c12-nd-spike-uses-sop-formula": ("C12", [("qc.py", "    if both_results:", "    if True:")],
        ["test_nondetect_spikes_keep_shipped_recovery"], "no SOP rule for a non-detect spike or parent: shipped formula stays"),
    "c12-unbracketed-after-last-uses-last": ("C12", [("qc.py", "    if before and after:\n        return ccv_pass[before[-1]] and ccv_pass[after[0]]",
        "    if before and after:\n        return ccv_pass[before[-1]] and ccv_pass[after[0]]\n    if after:\n        return ccv_pass[after[0]]")],
        ["test_unbracketed_runs_keep_shipped_check"], "before the first CCV the shipped check (True) stays"),
    # C13: envelope cross-product
    "c13-fallback-level-keeps-shipped-amount": ("C13", [("report.py", '            value = samples.amount(readings[name][run["id"]], levels[name], run["dilution"])',
        '            fallback = not any(r["kind"] == "blank" and readings[name][r["id"]] >= a["mdl"] for r in runs)\n            value = readings[name][run["id"]] * run["dilution"] - levels[name] if fallback else samples.amount(readings[name][run["id"]], levels[name], run["dilution"])')],
        ["test_batch_without_blank_results_keeps_shipped_level"], "only the level falls back; the amount rule still applies"),
    # C14: rules computed in two consumers
    "c14-spike-detection-on-raw-reading": ("C14", [("report.py", '            detected[name][run["id"]] = samples.corrected(readings[name][run["id"]], levels[name]) >= a["mdl"]',
        '            detected[name][run["id"]] = readings[name][run["id"]] >= a["mdl"]')],
        ["test_nondetect_spikes_keep_shipped_recovery"], "detection for the spike rule uses the corrected reading, as the flag does"),
    "c14-bracket-uses-unrounded-pass": ("C14", [("report.py", "            passed = qc.ccv_passes(recovery)\n            ccv_pass[name][run[\"id\"]] = passed",
        "            passed = qc.ccv_passes(recovery)\n            ccv_pass[name][run[\"id\"]] = 90.0 < recovery < 110.0")],
        ["test_bracketed_runs_need_both_ccvs"], "the CCV verdict feeds both ccvs.pass and bracketing"),
    # C15: stated orders
    "c15-spikes-sorted-by-id": ("C15", [("report.py", '    return {"blank_levels": levels, "samples": reported, "ccvs": ccvs, "spikes": spikes}',
        '    spikes.sort(key=lambda e: e["id"])\n    return {"blank_levels": levels, "samples": reported, "ccvs": ccvs, "spikes": spikes}')],
        ["test_report_order_and_types"], "lists follow run order"),
    "c15-ccvs-grouped-by-analyte": ("C15", [("report.py", '    return {"blank_levels": levels, "samples": reported, "ccvs": ccvs, "spikes": spikes}',
        '    ccvs = [e for a in analytes for e in ccvs if e["analyte"] == a["name"]]\n    return {"blank_levels": levels, "samples": reported, "ccvs": ccvs, "spikes": spikes}')],
        ["test_report_order_and_types"], "within a run the order of analytes"),
    # v9 platform return: range edges and plausible guards the fixed families did not reach
    "p1-amount-capped-1e6": ("C2", [("samples.py", "    return (reading - level) * dilution", "    return min((reading - level) * dilution, 1e6)")],
        ["test_section_one_limits_reached"], "SOP 5: amounts are not capped; a reading of 10^4 at dilution 1000 reports 10^7"),
    "p2-standard-is-counts-floor-1024": ("C3", [("calib.py", '    ys = [response(std["counts"][analyte], std["is_counts"]) for std in standards]',
        '    ys = [response(std["counts"][analyte], max(std["is_counts"], 1024)) for std in standards]')],
        ["test_section_one_limits_reached"], "SOP 1: a standard's is_counts may be 1000"),
    "p4-three-distinct-levels": ("C5", [("calib.py", "    mean_x = sum(xs) / len(xs)", '    if len(set(xs)) < 3:\n        raise ValueError("need three calibration levels")\n    mean_x = sum(xs) / len(xs)')],
        ["test_section_one_limits_reached"], "SOP 1: two different concentrations are enough"),
    "p5-slope-floor-1e-9": ("C12", [("calib.py", "    slope = sxy / sxx\n", '    slope = sxy / sxx\n    if slope < 1e-9:\n        raise ValueError("slope too small")\n')],
        ["test_section_one_limits_reached"], "SOP 1: any slope above nought is valid"),
    "p6-spike-dilution-capped-250": ("C6", [("report.py", '            value = samples.amount(readings[name][run["id"]], levels[name], run["dilution"])',
        '            value = samples.amount(readings[name][run["id"]], levels[name], run["dilution"] if run["kind"] == "sample" else min(run["dilution"], 250))')],
        ["test_section_one_limits_reached"], "SOP 1: a spike's dilution runs to 1000"),
    "p7-reading-clamped-to-top-standard": ("C2", [("calib.py", "    return (response(run[\"counts\"][analyte], run[\"is_counts\"]) - intercept) / slope",
        "    return min((response(run[\"counts\"][analyte], run[\"is_counts\"]) - intercept) / slope, 1000.0)")],
        ["test_section_one_limits_reached"], "SOP 3: a reading above the top standard is not clamped"),
    "p8-run-is-counts-floor-1024": ("C3", [("calib.py", "    return (response(run[\"counts\"][analyte], run[\"is_counts\"]) - intercept) / slope",
        "    return (response(run[\"counts\"][analyte], max(run[\"is_counts\"], 1024)) - intercept) / slope")],
        ["test_section_one_limits_reached"], "SOP 1: a run's is_counts may be 1000"),
    "p9-limit-tolerance-1e-4": ("C12", [("samples.py", '    if value < analyte["mdl"]:', '    if value < analyte["mdl"] - 1e-4:')],
        ["test_flags_just_either_side_of_mdl_and_loq"], "SOP 5: no tolerance on the mdl comparison"),
    # v10 platform return: open ends of SOP section 1 (floors on "above nought" values, ceilings the SOP never set)
    "q1-mdl-floor-0.001": ("C3", [("samples.py", '    if value < analyte["mdl"]:', '    if value < max(analyte["mdl"], 0.001):')],
        ["test_section_one_limits_reached"], "SOP 1: mdl runs down to 0.0001"),
    "q2-loq-floor-0.01": ("C3", [("samples.py", '    if value < analyte["loq"]:', '    if value < max(analyte["loq"], 0.01):')],
        ["test_section_one_limits_reached"], "SOP 1: loq runs down to the mdl"),
    "q3-ccv-dropped-outside-70-130": ("C12", [("report.py", '            ccvs.append({"id": run["id"], "analyte": name, "recovery": recovery, "pass": passed})',
        '            if 70.0 <= recovery <= 130.0:\n                ccvs.append({"id": run["id"], "analyte": name, "recovery": recovery, "pass": passed})')],
        ["test_section_one_limits_reached"], "SOP 1: a CCV reading runs from half to one and a half times its true concentration"),
    "q5-added-floor-0.01": ("C3", [("qc.py", "        return (spike_amount - parent_amount) / added * 100.0", "        return (spike_amount - parent_amount) / max(added, 0.01) * 100.0")],
        ["test_section_one_limits_reached"], "SOP 1: added runs down to 0.001"),
    "q6-ccv-true-cap-100": ("C2", [("report.py", '            recovery = qc.ccv_recovery(readings[name][run["id"]], run["true"][name])',
        '            if run["true"][name] > 100:\n                raise ValueError("CCV true concentration above 100")\n            recovery = qc.ccv_recovery(readings[name][run["id"]], run["true"][name])')],
        ["test_section_one_limits_reached"], "SOP 1: a CCV true concentration runs to 10^4"),
    "q7-reading-floor-guard-100": ("C12", [("calib.py", "def reading(run, analyte, line):\n    slope, intercept = line\n",
        'def reading(run, analyte, line):\n    slope, intercept = line\n    if (response(run["counts"][analyte], run["is_counts"]) - intercept) / slope < -100:\n        raise ValueError("reading below -100")\n')],
        ["test_readings_below_nought_are_not_clamped"], "SOP 1: readings run down to -10^4"),
    "q8-slope-floor-1e-11": ("C3", [("calib.py", "    slope = sxy / sxx\n", '    slope = sxy / sxx\n    if slope < 1e-11:\n        raise ValueError("slope too small")\n')],
        ["test_section_one_limits_reached"], "SOP 1: the slope runs down to 10^-12"),
    "q9-slope-cap-1e5": ("C2", [("calib.py", "    slope = sxy / sxx\n", '    slope = sxy / sxx\n    if slope > 1e5:\n        raise ValueError("slope too large")\n')],
        ["test_section_one_limits_reached"], "SOP 1: the slope runs up to 10^6"),
    "q10-intercept-clamped-at-nought": ("C8", [("calib.py", "    return slope, mean_y - slope * mean_x", "    return slope, max(0.0, mean_y - slope * mean_x)")],
        ["test_section_one_limits_reached"], "a fitted intercept may be below nought"),
    "q11-ccv-true-floor-guard": ("C3", [("report.py", '            recovery = qc.ccv_recovery(readings[name][run["id"]], run["true"][name])',
        '            if run["true"][name] <= 10 * a["loq"]:\n                raise ValueError("CCV true concentration too low")\n            recovery = qc.ccv_recovery(readings[name][run["id"]], run["true"][name])')],
        ["test_ccv_pass_on_rounded_recovery_inclusive"], "SOP 1: a CCV true concentration may equal ten times the loq"),
    # v12 platform return
    "r1-no-reportable-runs-zero-level": ("C4", [("report.py", '    levels = {a["name"]: blanks.blank_level(runs, a["name"], readings[a["name"]], a["mdl"]) for a in analytes}',
        '    levels = {a["name"]: blanks.blank_level(runs, a["name"], readings[a["name"]], a["mdl"]) for a in analytes}\n    if not any(r["kind"] in REPORTED for r in runs):\n        levels = {a["name"]: 0.0 for a in analytes}')],
        ["test_blank_level_is_mean_of_results_anywhere"], "SOP 4: a batch of blanks alone still has its blank level"),
    # v13 platform return: derived minima of every value the package divides by or compares
    "s1-ccv-true-floor-1": ("C3", [("qc.py", "    return reading / true * 100.0", "    return reading / max(1.0, true) * 100.0")],
        ["test_section_one_limits_reached"], "SOP 1: a CCV true concentration runs down to ten times the smallest loq, 0.001"),
    "s2-loq-floor-0.00015": ("C3", [("samples.py", '    if value < analyte["loq"]:', '    if value < max(analyte["loq"], 0.00015):')],
        ["test_section_one_limits_reached"], "SOP 1: loq runs down to the smallest mdl, 0.0001"),
    "s3-ccv-reading-floor-0.01": ("C3", [("qc.py", "    return reading / true * 100.0", "    return max(reading, 0.01) / true * 100.0")],
        ["test_section_one_limits_reached"], "SOP 1: a CCV reading runs down to half of 0.001"),
}

ALTERNATIVES = {
    "alt-blank-levels-reversed-keys": [("report.py", '    return {"blank_levels": levels,', '    levels = dict(reversed(list(levels.items())))\n    return {"blank_levels": levels,')],
    "alt-fsum-closed-form-fit": [("calib.py", "    mean_x = sum(xs) / len(xs)\n    mean_y = sum(ys) / len(ys)\n    sxy = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))\n    sxx = sum((x - mean_x) ** 2 for x in xs)\n    slope = sxy / sxx\n    return slope, mean_y - slope * mean_x",
        "    import math\n    n = len(xs)\n    sx, sy = math.fsum(xs), math.fsum(ys)\n    slope = (n * math.fsum(x * y for x, y in zip(xs, ys)) - sx * sy) / (n * math.fsum(x * x for x in xs) - sx * sx)\n    return slope, (sy - slope * sx) / n")],
}


def reference_tree(dest):
    shutil.copytree(TASK / "environment" / "app", dest / "app")
    subprocess.run(["git", "apply", str(TASK / "solution" / "fix.patch")], cwd=dest, check=True)
    return dest / "app" / "src" / "metalquant"


def write_patch(variant_src, out):
    lines = []
    for path in sorted((SRC / "metalquant").glob("*.py")):
        a = path.read_text().splitlines(keepends=True)
        b = (variant_src / path.name).read_text().splitlines(keepends=True)
        if a != b:
            rel = f"app/src/metalquant/{path.name}"
            lines.append(f"diff --git a/{rel} b/{rel}\n")
            lines.extend(difflib.unified_diff(a, b, f"a/{rel}", f"b/{rel}", n=3))
    out.write_text("".join(lines))


def build(name, edits):
    with tempfile.TemporaryDirectory() as tmp:
        pkg = reference_tree(Path(tmp))
        for file, old, new in edits:
            text = (pkg / file).read_text()
            assert text.count(old) == 1, f"{name}: anchor not unique in {file}: {old[:60]!r}"
            (pkg / file).write_text(text.replace(old, new))
        write_patch(pkg, HERE / f"{name}.patch")


catalog = {"mutants": {}, "alternatives": sorted(ALTERNATIVES)}
for name, (cls, edits, witnesses, why) in MUTANTS.items():
    build(name, edits)
    catalog["mutants"][name] = {"class": cls, "expect_failing": [T + w for w in witnesses], "rationale": why}
for name, edits in ALTERNATIVES.items():
    build(name, edits)
(HERE / "catalog.json").write_text(json.dumps(catalog, indent=1) + "\n")
print(len(MUTANTS), "mutants,", len(ALTERNATIVES), "alternatives")
