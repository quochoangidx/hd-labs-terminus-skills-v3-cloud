"""wrong_paths.py [--run]: write one patch per wrong path (Oracle + one edit) and optionally run them all in parallel."""
import concurrent.futures as cf, json, os, shutil, subprocess, sys, tempfile
from pathlib import Path
HERE = Path(__file__).resolve().parent
R = HERE.parent
REPO = R.parents[2]
TASK = REPO / "workspace/tasks/tbrain-icpms-sop-data-reduction"
T = "test_outputs.py::"
ORACLE = Path(os.environ.get("ORACLE_APP", "/private/tmp/claude-501/-Users-quochoangdev-HDTechLS-hd-labs-terminus-skills-v3/7f99967c-92a4-460b-bbd7-2f832e7f7790/scratchpad/oracle/app"))
# id, kind, file (relative to app/), old, new, expected failing tests
WP = [
 ("cal-through-origin","semantic_partial","src/metalquant/calib.py","    slope = sxy / sxx\n    return slope, mean_y - slope * mean_x","    return sum(x * y for x, y in zip(xs, ys)) / sum(x * x for x in xs), 0.0",["test_calibration_line_has_fitted_intercept"]),
 ("blank-first-blank-only","semantic_partial","src/metalquant/blanks.py","    if results:\n        return sum(results) / len(results)\n","",["test_blank_level_is_mean_of_results_anywhere"]),
 ("blank-mean-of-all-blanks","over_repair","src/metalquant/blanks.py","run[\"kind\"] == \"blank\" and readings[run[\"id\"]] >= mdl]","run[\"kind\"] == \"blank\"]",["test_nondetect_blanks_stay_out_of_the_mean"]),
 ("blank-no-results-zero","over_repair","src/metalquant/blanks.py","        return sum(results) / len(results)\n","        return sum(results) / len(results)\n    return 0.0\n",["test_batch_without_blank_results_keeps_shipped_level"]),
 ("blank-level-floor-zero","over_repair","src/metalquant/blanks.py","            return readings[run[\"id\"]]","            return max(0.0, readings[run[\"id\"]])",["test_readings_below_nought_are_not_clamped"]),
 ("amount-dilute-then-subtract","semantic_partial","src/metalquant/samples.py","    return (reading - level) * dilution","    return reading * dilution - level",["test_blank_comes_off_before_dilution"]),
 ("flag-on-amount","semantic_partial","src/metalquant/samples.py","    value = corrected(reading, level)","    value = amount(reading, level, dilution)",["test_flags_judged_on_corrected_reading"]),
 ("ccv-exclusive-unrounded","semantic_partial","src/metalquant/qc.py","    return 90.0 <= round(recovery, 1) <= 110.0","    return 90.0 < recovery < 110.0",["test_ccv_pass_on_rounded_recovery_inclusive"]),
 ("ccv-inclusive-unrounded","over_repair","src/metalquant/qc.py","    return 90.0 <= round(recovery, 1) <= 110.0","    return 90.0 <= recovery <= 110.0",["test_ccv_pass_on_rounded_recovery_inclusive"]),
 ("bracket-preceding-only","semantic_partial","src/metalquant/qc.py","    if before and after:\n        return ccv_pass[before[-1]] and ccv_pass[after[0]]\n","",["test_bracketed_runs_need_both_ccvs"]),
 ("bracket-either-side","over_repair","src/metalquant/qc.py","    if before and after:\n        return ccv_pass[before[-1]] and ccv_pass[after[0]]\n","    if before or after:\n        return all(ccv_pass[i] for i in before[-1:] + after[:1])\n",["test_unbracketed_runs_keep_shipped_check"]),
 ("unbracketed-is-not-ok","over_repair","src/metalquant/qc.py","    if before and after:\n        return ccv_pass[before[-1]] and ccv_pass[after[0]]\n","    if before and after:\n        return ccv_pass[before[-1]] and ccv_pass[after[0]]\n    return False\n",["test_unbracketed_runs_keep_shipped_check"]),
 ("spike-dilution-in-denominator","semantic_partial","src/metalquant/qc.py","        return (spike_amount - parent_amount) / added * 100.0","        return (spike_amount - parent_amount) / (added * dilution) * 100.0",["test_spike_recovery_of_results"]),
 ("spike-added-for-every-spike","over_repair","src/metalquant/qc.py","    if both_results:\n","    if True:\n",["test_nondetect_spikes_keep_shipped_recovery"]),
 ("spike-nondetect-parent-as-zero","over_repair","src/metalquant/report.py","                amounts[name][run[\"parent\"]],","                amounts[name][run[\"parent\"]] if detected[name][run[\"parent\"]] else 0.0,",["test_nondetect_spikes_keep_shipped_recovery"]),
 ("spike-result-on-spike-only","semantic_partial","src/metalquant/report.py","detected[name][run[\"id\"]] and detected[name][run[\"parent\"]],","detected[name][run[\"id\"]],",["test_nondetect_spikes_keep_shipped_recovery"]),
 ("reads-expected-files","harness_bypass","src/metalquant/report.py","def reduce_batch(batch):\n","def reduce_batch(batch):\n    import glob\n    for path in glob.glob('/tests/expected/*'):\n        try:\n            open(path, 'rb').read()\n        except OSError:\n            pass\n    return {'blank_levels': {}, 'samples': [], 'ccvs': [], 'spikes': []}\n",["test_calibration_line_has_fitted_intercept","test_generated_batches"]),
]
def mkpatch(variant_app, out):
    subprocess.run([sys.executable, str(HERE / "mkpatch.py"), str(variant_app), str(out)], check=True, capture_output=True)
def build(wp):
    wid, kind, rel, old, new, exp = wp
    tmp = Path(tempfile.mkdtemp()) / "app"
    shutil.copytree(ORACLE, tmp)
    p = tmp / rel
    s = p.read_text()
    assert s.count(old) == 1, (wid, old)
    p.write_text(s.replace(old, new))
    mkpatch(tmp, R / "wrong-paths" / f"{wid}.patch")
    shutil.rmtree(tmp.parent)
def driver_shim():
    # harness bypass: package left as shipped, driver computes through a private fixed copy
    tmp = Path(tempfile.mkdtemp())
    (tmp / "a/app/tools").mkdir(parents=True); (tmp / "b/app/tools/_fixed").mkdir(parents=True)
    drv = (TASK / "environment/app/tools/metalquant_run.py").read_text()
    shim = drv.replace('"..", "src"', '"_fixed"')
    import difflib
    lines = [f"diff --git a/app/tools/metalquant_run.py b/app/tools/metalquant_run.py\n"]
    lines += difflib.unified_diff(drv.splitlines(True), shim.splitlines(True), "a/app/tools/metalquant_run.py", "b/app/tools/metalquant_run.py")
    for f in sorted((ORACLE / "src/metalquant").glob("*.py")):
        body = f.read_text().splitlines(True)
        lines.append(f"diff --git a/app/tools/_fixed/metalquant/{f.name} b/app/tools/_fixed/metalquant/{f.name}\nnew file mode 100644\n")
        lines += difflib.unified_diff([], body, "/dev/null", f"b/app/tools/_fixed/metalquant/{f.name}")
    (R / "wrong-paths/driver-shim.patch").write_text("".join(lines))
    shutil.rmtree(tmp)
ALL = [(w[0], w[1], w[5]) for w in WP] + [("driver-shim", "harness_bypass", ["test_driver_is_unchanged"])]
# adversarial pass (step 5b) submissions, kept as a regression suite; patches apply to the shipped tree
ADV = {"W01_counts_key_order": ["test_report_order_and_types"], "W02_dedupe_standards": ["test_calibration_line_has_fitted_intercept"],
       # W03 (strict > at the mdl) and W16 (a 1e-7 tolerance) are contract-equivalent since the v9 SOP margin keeps
       # every judged value 10^-5 from a limit; kept as files, no longer graded as wrong
       "W03_spike_result_strict": [], "W16_epsilon_guard": [],
       "W04_blank_median": ["test_blank_level_is_mean_of_results_anywhere"], "W05_std_is_first": ["test_calibration_line_has_fitted_intercept"], "W06_ccv_ok_any_analyte": ["test_report_order_and_types"], "W07_blank_result_per_run": ["test_report_order_and_types"], "W08_ccv_truncate": ["test_ccv_pass_on_rounded_recovery_inclusive"],
       "W09_nd_parent_dilution": ["test_nondetect_spikes_keep_shipped_recovery"], "W10_noresult_zero": ["test_batch_without_blank_results_keeps_shipped_level"],
       "W11_after_last_true": ["test_unbracketed_runs_keep_shipped_check"], "W12_nd_uses_sop_formula": ["test_nondetect_spikes_keep_shipped_recovery"],
       "W13_ccv_blank_corrected": ["test_report_order_and_types"], "W14_result_by_amount": ["test_nondetect_spikes_keep_shipped_recovery"], "W15_bracket_last_ccv": ["test_bracketed_runs_need_both_ccvs"], "H01_read_expected": ["test_generated_batches"], "H02_driver_tamper": ["test_driver_is_unchanged"]}
ADV_DIR = R / "adversarial"
# Sound Verifier sweep (blueprint section 5, C1-C18): Oracle mutants from sweep/build.py; witness = the test
# that owns the broken rule (per-analyte and interaction mutants land on the families that carry them)
SWEEP_DIR = R / "sweep"
SWEEP_WITNESS = {"c10-first-analyte-limits": ["test_report_order_and_types"], "c11-blank-result-any-analyte": ["test_report_order_and_types"],
                 "c14-bracket-uses-unrounded-pass": ["test_generated_batches"], "c4-zero-counts-nd": ["test_generated_batches"],
                 "c6-added-capped-500": ["test_generated_batches"], "c15-spikes-sorted-by-id": ["test_spike_recovery_of_results"]}
SWEEP = {k: SWEEP_WITNESS.get(k, [e.split("::")[-1] for e in v["expect_failing"]]) for k, v in json.load(open(SWEEP_DIR / "catalog.json"))["mutants"].items()}
def run(item):
    wid, kind, exp = item
    ctrf = R / "wrong-paths" / f"{wid}.ctrf.json"
    env = dict(os.environ, WP_CTRF=str(ctrf))
    cmd = [sys.executable, str(REPO / ".agent/skills/terminus-regular-task-authoring/scripts/wrong_path_runner.py"), str(TASK), "--id", wid,
           "--patch", str((ADV_DIR if wid in ADV else SWEEP_DIR if wid in SWEEP else R / "wrong-paths") / f"{wid}.patch"), "--verifier", str(HERE / "score_variant.sh"), "--ctrf", str(ctrf),
           "--receipt", str(R / "wrong-paths" / f"{wid}.json")] + sum([["--expect-failing", T + e] for e in exp], [])
    p = subprocess.run(cmd, capture_output=True, text=True, env=env)
    return wid, p.returncode, (p.stdout + p.stderr).strip().splitlines()[-1:]
if __name__ == "__main__":
    for wp in WP: build(wp)
    driver_shim()
    print("patches written:", len(ALL))
    if "--run" in sys.argv:
        items = ALL + [(k, "harness_bypass" if k.startswith("H") else "semantic_partial", v) for k, v in ADV.items() if v] + [(k, "semantic_partial", v) for k, v in SWEEP.items()]
        with cf.ThreadPoolExecutor(max_workers=int(os.environ.get("JOBS", "6"))) as ex:
            for wid, rc, msg in ex.map(run, items):
                print(("OK  " if rc == 0 else "BAD ") + wid, msg)
