"""wrong_paths.py: build each wrong-path patch (reference fix plus one slip, or a harness bypass) and score it with
wrong_path_runner.py through workspace/tools/score.sh. Receipts: ../wrong-paths/<id>.json."""
import difflib
import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
TASK = REPO / "workspace" / "tasks" / "tbrain-occupational-noise-dose-survey"
OUT = HERE.parent / "wrong-paths"
RUNNER = REPO / ".agent" / "skills" / "terminus-regular-task-authoring" / "scripts" / "wrong_path_runner.py"
spec = importlib.util.spec_from_file_location("cd", HERE / "check_departures.py")
cd = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cd)
T = "tests/test_outputs.py::"


def full_patch(app_root):
    base = TASK / "environment" / "app"
    out = []
    names = sorted({p.relative_to(base).as_posix() for p in base.rglob("*.py")} | {p.relative_to(app_root).as_posix() for p in app_root.rglob("*.py")})
    for rel in names:
        a = (base / rel).read_text().splitlines(keepends=True) if (base / rel).exists() else []
        b = (app_root / rel).read_text().splitlines(keepends=True) if (app_root / rel).exists() else []
        if a != b:
            out.append(f"diff --git a/app/{rel} b/app/{rel}\n")
            out.extend(difflib.unified_diff(a, b, f"a/app/{rel}", f"b/app/{rel}", n=3))
    return "".join(out)


def variant(edits, base="oracle", driver_edit=None):
    root = HERE / "wp-build"
    if root.exists():
        shutil.rmtree(root)
    shutil.copytree(TASK / "environment" / "app", root, ignore=shutil.ignore_patterns("__pycache__"))
    if base == "oracle":
        shutil.rmtree(root / "src")
        shutil.copytree(HERE / "oracle" / "src", root / "src", ignore=shutil.ignore_patterns("__pycache__"))
    for rel, old, new in edits:
        f = root / "src" / "noisedose" / rel
        t = f.read_text()
        assert t.count(old) == 1, (rel, old)
        f.write_text(t.replace(old, new))
    if driver_edit:
        f = root / "tools" / "noisedose_run.py"
        f.write_text(f.read_text() + driver_edit)
    return root


dep = {name.split("_")[0]: edits for name, _r, edits, _s in cd.DEPARTURES}
trap = {name.split("_")[0]: repairs for name, _r, _site, repairs, _s in cd.TRAPS}
CHEAT = '''

def _sealed_answer(survey):
    """Harness bypass: look the answer up in the verifier's sealed expectations."""
    import json as _json, pathlib as _pathlib
    for path in _pathlib.Path("/tests/expected").glob("*.jsonl"):
        for line in path.read_text().splitlines():
            row = _json.loads(line)
            if row.get("survey") == survey:
                return row["report"]
    return None


_shipped_build_report = build_report


def build_report(survey):  # noqa: F811
    try:
        answer = _sealed_answer(survey)
    except OSError:
        answer = None
    return answer if answer is not None else _shipped_build_report(survey)
'''
WRONG = {
    "W01-federal-reference-duration": ("core", ["REFERENCE_DURATION"], dep["D1"], [T + "test_rule_3_1_reference_duration_uses_85_dba_and_3_db"]),
    "W02-threshold-strict": ("core", ["COUNTED_READING"], dep["D2"], [T + "test_rule_2_3_reading_at_the_threshold_counts"]),
    "W03-sampled-counted-only": ("core", ["SAMPLED_TIME"], dep["D3"], [T + "test_rule_2_4_sampled_time_includes_readings_below_threshold"]),
    "W04-sampled-every-run": ("core", ["SAMPLED_TIME"], trap["T1"][0][1], [T + "test_rule_2_2_run_logged_at_nought_is_not_a_reading"]),
    "W05-project-to-eight-hours": ("core", ["SHIFT_DOSE"], dep["D4"], [T + "test_rule_3_3_partial_survey_projected_to_own_shift"]),
    "W06-three-quarters-exclusive": ("core", ["SHIFT_DOSE"], dep["D10"], [T + "test_rule_2_5_partial_survey_at_exactly_three_quarters"]),
    "W07-project-every-short-survey": ("core", ["SHIFT_DOSE"], trap["T3"][0][1], [T + "test_survey_below_three_quarters_keeps_todays_projection"]),
    "W08-short-survey-unprojected": ("core", ["SHIFT_DOSE"], trap["T3"][1][1], [T + "test_survey_below_three_quarters_keeps_todays_projection"]),
    "W09-nothing-measured-divides": ("core", ["SHIFT_DOSE"], [("shift.py", "    if sampled == 0:\n        return 0.0\n", "")], [T + "test_survey_that_measured_nothing_keeps_todays_dose"]),
    "W10-federal-twa": ("core", ["TWA"], dep["D5"], [T + "test_rule_4_1_twa_formula"]),
    "W11-twa-truncated": ("core", ["TWA"], dep["D6"], [T + "test_rule_1_2_twa_rounded_to_nearest_tenth"]),
    "W12-impulse-strict": ("core", ["FLAGS"], dep["D8"], [T + "test_rule_5_2_impulse_at_140_dbc"]),
    "W13-ceiling-inclusive": ("core", ["FLAGS"], [("flags.py", "level > CEILING_DBA", "level >= CEILING_DBA")], [T + "test_rule_5_1_reading_at_the_ceiling_level_is_not_flagged"]),
    "W14-federal-status-bands": ("core", ["STATUS"], dep["D7"], [T + "test_rule_5_3_status_bands_at_82_and_85"]),
    "W15-group-mean-of-twas": ("core", ["GROUP_DOSE"], dep["D9"], [T + "test_rule_6_1_group_dose_is_mean_of_shift_doses"]),
    "W16-group-drops-quiet-members": ("core", ["GROUP_DOSE"], dep["D9b"], [T + "test_rule_6_1_quiet_member_counts_in_group_mean"]),
    "W18-kept-step-counted-minutes": ("core", ["SHIFT_DOSE", "SAMPLED_TIME"], [("shift.py", "    if sampled == 0:\n        return 0.0\n    if sampled < EIGHT_HOURS:\n", "    sampled = sum(m for m, lv in log if lv >= 80.0)\n    if sampled == 0:\n        return 0.0\n    if sampled < EIGHT_HOURS:\n")], [T + "test_survey_below_three_quarters_keeps_todays_projection"]),
    "W17-count-above-ceiling-at-own-level": ("core", ["REFERENCE_DURATION"], trap["T4"][0][1], [T + "test_reading_above_ceiling_keeps_todays_counted_level"]),
}


def score(wid, patch_text, expect):
    OUT.mkdir(exist_ok=True)
    p = OUT / f"{wid}.patch"
    p.write_text(patch_text)
    ctrf = OUT / f"{wid}.ctrf.json"
    args = [sys.executable, str(RUNNER), str(TASK), "--id", wid, "--patch", str(p), "--verifier", str(REPO / "workspace" / "tools" / "score.sh"),
            "--ctrf", str(ctrf), "--receipt", str(OUT / f"{wid}.json")]
    for e in expect:
        args += ["--expect-failing", e]
    r = subprocess.run(args, cwd=REPO, capture_output=True, text=True, env={**__import__("os").environ, "CTRF_OUT": str(ctrf)})
    rec = json.loads((OUT / f"{wid}.json").read_text())
    print(wid, rec["status"], rec["reward"], len(rec["failed_test_ids"]), "failed", r.stdout.strip().splitlines()[-1:] if rec["status"] != "pass" else "")
    return rec


def main():
    results = {}
    for wid, (_kind, _obs, edits, expect) in WRONG.items():
        results[wid] = score(wid, full_patch(variant(edits)), expect)
    results["H01-driver-tampered"] = score("H01-driver-tampered", full_patch(variant([], driver_edit="# local tweak\n")),
                                           [T + "test_submitted_driver_unchanged"])
    shipped_cheat = variant([])
    shutil.rmtree(shipped_cheat / "src")
    shutil.copytree(TASK / "environment" / "app" / "src", shipped_cheat / "src", ignore=shutil.ignore_patterns("__pycache__"))
    rp = shipped_cheat / "src" / "noisedose" / "report.py"
    rp.write_text(rp.read_text() + CHEAT)
    results["H02-read-sealed-expectations"] = score("H02-read-sealed-expectations", full_patch(shipped_cheat),
                                                    [T + "test_rule_3_1_reference_duration_uses_85_dba_and_3_db", T + "test_generated_surveys"])
    shutil.rmtree(HERE / "wp-build", ignore_errors=True)
    print("all pass:", all(r["status"] == "pass" for r in results.values()))


if __name__ == "__main__":
    main()
