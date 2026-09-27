"""check_departures.py: departure and trap evidence before any verifier exists.

For every departure: the Oracle matches the model on the departure's fixture, while the shipped package and the
Oracle with that one hunk reverted both differ from it. For every trap: the natural wrong repair differs from the
model on the trap's fixture, the Oracle matches, and the shipped package matches the model on the quantity the
trap decides (its silent case). Writes ../receipts/departure-trap-checks.json.
"""
import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TASK = HERE.parents[2] / "tasks" / "tbrain-occupational-noise-dose-survey"
SHIPPED = TASK / "environment" / "app" / "src"
ORACLE = HERE / "patched" / "app" / "src"
VARIANTS = HERE / "variants"
spec = importlib.util.spec_from_file_location("model", TASK / "solution" / "model.py")
model = importlib.util.module_from_spec(spec)
spec.loader.exec_module(model)

RUNNER = "import json,sys; sys.path.insert(0, sys.argv[1]); import noisedose; print(json.dumps(noisedose.build_report(json.load(sys.stdin))))"


def run(src, survey):
    p = subprocess.run([sys.executable, "-I", "-S", "-B", "-c", RUNNER, str(src)], input=json.dumps(survey), capture_output=True, text=True, timeout=60)
    if p.returncode:
        return {"error": p.stderr.strip().splitlines()[-1]}
    return json.loads(p.stdout)


def close(a, b):
    if type(a) is not type(b):
        return False
    if isinstance(b, dict):
        return list(a) == list(b) and all(close(a[k], b[k]) for k in b)
    if isinstance(b, list):
        return len(a) == len(b) and all(close(x, y) for x, y in zip(a, b))
    if isinstance(b, float):
        return abs(a - b) <= (1e-9 * abs(b) if abs(b) >= 1 else 1e-9)
    return a == b


def variant(name, edits):
    root = VARIANTS / name
    if root.exists():
        shutil.rmtree(root)
    shutil.copytree(ORACLE, root / "src")
    for rel, old, new in edits:
        path = root / "src" / "noisedose" / rel
        text = path.read_text()
        assert text.count(old) == 1, (name, rel, old)
        path.write_text(text.replace(old, new))
    return root / "src"


def W(wid, group, shift, log, peaks=()):
    return {"id": wid, "group": group, "shift_minutes": shift, "log": [list(r) for r in log], "peaks": list(peaks)}


def S(name, *workers):
    return {"survey": name, "workers": list(workers)}


GROUP_MEAN = """        doses = [row["dose"] for row in members[code]]
"""

DEPARTURES = [
    ("D1_reference_duration_85_3", "3.1", [("levels.py", "CRITERION_DBA = 85.0", "CRITERION_DBA = 90.0"), ("levels.py", "EXCHANGE_DB = 3.0", "EXCHANGE_DB = 5.0")],
     S("D1", W("A1", "G1", 480, [(480, 91.0)]))),
    ("D2_reading_at_threshold_counts", "2.3", [("levels.py", "return level >= THRESHOLD_DBA", "return level > THRESHOLD_DBA")],
     S("D2", W("A1", "G1", 480, [(240, 80.0), (240, 90.0)]))),
    ("D3_sampled_time_counts_below_threshold_readings", "2.4", [("runs.py", "        sampled += minutes\n        counted = min(level, CEILING_DBA)\n        if adds_dose(counted):\n", "        counted = min(level, CEILING_DBA)\n        if not adds_dose(counted):\n            continue\n        sampled += minutes\n        if adds_dose(counted):\n")],
     S("D3", W("A1", "G1", 480, [(200, 92.0), (200, 70.0)]))),
    ("D4_full_shift_projection_to_own_shift", "3.3", [("shift.py", "        return measured * shift_minutes / sampled\n", "        return measured * 480 / sampled if sampled < 480 else measured\n"), ("shift.py", "    if sampled >= shift_minutes:\n        return measured\n", "")],
     S("D4", W("A1", "G1", 720, [(600, 90.0)]), W("A2", "G1", 360, [(420, 88.0)]), W("A3", "G2", 480, [(360, 89.0)]))),
    ("D5_twa_formula", "4.1", [("twa.py", "return 85.0 + 3.0 * math.log2(dose / 100.0)", "return 90.0 + 16.61 * math.log10(dose / 100.0)")],
     S("D5", W("A1", "G1", 480, [(480, 91.0)]))),
    ("D6_twa_rounded_to_nearest", "1.2", [("twa.py", "math.floor(value * 10.0 + 0.5) / 10.0", "math.floor(value * 10.0) / 10.0")],
     S("D6", W("A1", "G1", 480, [(300, 90.0), (180, 83.0)]))),
    ("D7_status_bands_82_85", "5.3", [("twa.py", "ACTION_LEVEL_DB = 82.0\nEXPOSURE_LIMIT_DB = 85.0", "ACTION_LEVEL_DB = 85.0\nEXPOSURE_LIMIT_DB = 90.0"), ("twa.py", "if twa > EXPOSURE_LIMIT_DB:", "if twa >= EXPOSURE_LIMIT_DB:")],
     S("D7", W("A1", "G1", 480, [(480, 82.0)]), W("A2", "G2", 480, [(480, 85.0)]), W("A3", "G3", 480, [(480, 86.0)]))),
    ("D8_impulse_at_140", "5.2, 2.6", [("flags.py", "peak >= IMPULSE_DBC", "peak > IMPULSE_DBC")],
     S("D8", W("A1", "G1", 480, [(480, 84.0)], [139.9, 140.0]))),
    ("D9_group_dose_mean_of_doses", "6.1", [("groups.py", 'doses = [row["dose"] for row in members[code]]\n        dose = sum(doses) / len(doses)\n        twa = twa_for(dose)\n        if twa is not None:\n            twa = to_tenth(twa)',
                                              'levels = [row["twa"] for row in members[code] if row["twa"] is not None]\n        twa = to_tenth(sum(levels) / len(levels)) if levels else None\n        dose = 100.0 * 2.0 ** ((twa - 85.0) / 3.0) if twa is not None else 0.0')],
     S("D9", W("A1", "G1", 480, [(480, 95.0)]), W("A2", "G1", 480, [(480, 83.0)]), W("A3", "G1", 480, [(480, 84.0)]))),
    ("D9b_quiet_member_counts_in_group_mean", "6.1", [("groups.py", GROUP_MEAN, """        doses = [row["dose"] for row in members[code] if row["twa"] is not None]
""")],
     S("D9b", W("A1", "G1", 480, [(480, 90.0)]), W("Q1", "G1", 480, [(300, 64.0), (180, 71.5)]))),
    ("D10_full_shift_boundary_at_three_quarters", "2.5", [("shift.py", "if 4 * sampled >= 3 * shift_minutes:", "if 4 * sampled > 3 * shift_minutes:")],
     S("D10", W("A1", "G1", 600, [(450, 90.0)]))),
]

TRAPS = [
    ("T1_run_logged_at_0_stays_out_of_sampled_time", "2.2, 2.4 via 3.3 (governed; kept as a family, not counted as a trap)", "runs.py",
     [("move the sampled-time sum ahead of every test, so every run's minutes are sampled time",
       [("runs.py", "        if not is_reading(level):\n            continue\n        sampled += minutes\n", "        sampled += minutes\n        if not is_reading(level):\n            continue\n")])],
     S("T1", W("B1", "G1", 480, [(200, 91.0), (60, 0.0), (170, 86.5), (45, 0.0)]), W("B2", "G1", 480, [(30, 0.0), (400, 93.0)]))),
    ("T3_survey_below_three_quarters_keeps_todays_projection", "2.5 'partial survey' bounds 3.3; value-level silence", "shift.py",
     [("project every survey shorter than the shift to the shift", [("shift.py", "    if 4 * sampled >= 3 * shift_minutes:  # a partial survey (manual 2.5, 3.3)\n", "    if sampled > 0:\n")]),
      ("give a survey the manual does not cover its measured dose unprojected", [("shift.py", "    if sampled < EIGHT_HOURS:\n        return measured * EIGHT_HOURS / sampled\n    return measured\n", "    return measured\n")])],
     S("T3", W("X1", "G1", 720, [(300, 90.0)]), W("X2", "G2", 1440, [(600, 88.0)]), W("X3", "G3", 360, [(120, 92.0), (60, 85.5)]))),
    ("T4_reading_above_ceiling_counted_at_the_ceiling", "2.3 'counted at its own level' bounded by 5.1 ceiling level, used by 3.2; value-level silence", "runs.py",
     [("count every counted reading at its own level (the 3.1 formula everywhere)", [("runs.py", "        counted = min(level, CEILING_DBA)\n", "        counted = level\n")])],
     S("T4", W("Y1", "G1", 480, [(400, 90.0), (20, 118.5)]), W("Y2", "G2", 480, [(470, 84.0), (10, 131.2)]))),
]


def main():
    VARIANTS.mkdir(exist_ok=True)
    rows, ok = [], True
    for name, rule, edits, survey in DEPARTURES:
        exp = model.report(survey)
        v = variant(name, edits)
        res = {"id": name, "rule": rule, "oracle_matches_model": close(run(ORACLE, survey), exp),
               "shipped_differs": not close(run(SHIPPED, survey), exp), "one_hunk_revert_differs": not close(run(v, survey), exp)}
        res["pass"] = all(res[k] for k in ("oracle_matches_model", "shipped_differs", "one_hunk_revert_differs"))
        ok &= res["pass"]
        rows.append(res)
    trap_rows = []
    for name, rule, site, repairs, survey in TRAPS:
        exp = model.report(survey)
        res = {"id": name, "rule": rule, "site": site, "oracle_matches_model": close(run(ORACLE, survey), exp), "natural_repairs": []}
        for i, (desc, edits) in enumerate(repairs):
            v = variant(f"{name}__natural_{i}", edits)
            res["natural_repairs"].append({"repair": desc, "differs_from_model": not close(run(v, survey), exp)})
        trap_rows.append(res)
    # Silent-case match with the shipped package, on the quantity each trap decides.
    sys.path.insert(0, str(SHIPPED))
    import noisedose.runs as shipped_runs  # shipped package, authoring check only
    import noisedose.shift as shipped_shift
    t1_logs = [[(200, 91.0), (60, 0.0), (170, 86.5), (45, 0.0)], [(30, 0.0), (400, 93.0)], [(10, 0.0), (1, 115.1), (5, 0.0)]]
    trap_rows[0]["shipped_matches_model_on_silent_case"] = all(shipped_runs.measure(log)[0] == model.sampled_time(log) for log in t1_logs)
    trap_rows[0]["silent_case"] = "sampled time of logs whose runs are 0.0 or above 80.0 dBA: shipped measure() equals model sampled_time()"
    # T3: the kept step is the shipped projection factor; compare shift dose / measured dose on partial surveys whose
    # runs are all above 80.0 dBA (so shipped and manual sampled time agree and the constants cancel in the ratio).
    t3 = [([(300, 90.0)], 720), ([(600, 88.0)], 1440), ([(120, 92.0), (60, 85.5)], 360), ([(1, 99.0)], 60), ([(479, 81.0)], 1440), ([], 480)]
    match = True
    for log, shift in t3:
        s_sampled, s_measured = shipped_runs.measure(log)
        s_dose = shipped_shift.shift_dose(log, shift)
        m_dose, m_measured = model.shift_dose(log, shift), model.measured_dose(log)
        assert not model.is_full_shift(model.sampled_time(log), shift)
        s_factor = s_dose / s_measured if s_measured else s_dose
        m_factor = m_dose / m_measured if m_measured else m_dose
        match &= abs(s_factor - m_factor) <= 1e-12 * max(1.0, abs(m_factor))
    trap_rows[1]["shipped_matches_model_on_silent_case"] = match
    trap_rows[1]["silent_case"] = "projection factor (shift dose / measured dose; the dose itself when nothing is measured) on surveys below three quarters of the shift, shifts 60-1440 and an empty log"
    # T4: the kept step is the level an above-ceiling reading is counted at; shipped and model both count it at 115.0:
    # the measured dose of a run above the ceiling equals that of the same run at the ceiling, in both.
    t4 = [(20, 118.5), (1, 140.0), (300, 115.1)]
    trap_rows[2]["shipped_matches_model_on_silent_case"] = all(
        shipped_runs.measure([(m, lvl)])[1] == shipped_runs.measure([(m, 115.0)])[1]
        and model.measured_dose([(m, lvl)]) == model.measured_dose([(m, 115.0)]) for m, lvl in t4)
    trap_rows[2]["silent_case"] = "a run above the ceiling level adds what the same run at 115.0 dBA adds, in the shipped package and in the model"
    for r in trap_rows:
        r["pass"] = r["oracle_matches_model"] and all(x["differs_from_model"] for x in r["natural_repairs"]) and r["shipped_matches_model_on_silent_case"]
        ok &= r["pass"]
    receipt = {"status": "pass" if ok else "fail", "departures": rows, "traps": trap_rows,
               "model_sha256": hashlib.sha256((TASK / "solution" / "model.py").read_bytes()).hexdigest(),
               "fix_patch_sha256": hashlib.sha256((TASK / "solution" / "fix.patch").read_bytes()).hexdigest()}
    (HERE.parent / "receipts" / "departure-trap-checks.json").write_text(json.dumps(receipt, indent=1) + "\n")
    print(json.dumps(receipt, indent=1))


if __name__ == "__main__":
    main()
