"""Step-4 checks on the skeleton: departures, kept steps, natural over-repairs, isolation.

    python3 departure_trap_checks.py TASK_DIR RECEIPT.json

- every departure: the unpatched package differs from solution/model.py on the rule's column,
  and reverting only that rule inside the Oracle differs too;
- TX (already-correct code): today's holds() gives every reading but the last the SOP 5.1
  weight, so the unpatched
  package matches the model on the column the kept step decides, in a job where the other
  departures cannot move that column;
- every trap: its natural over-repair (a mutant of the Oracle) differs from the model on the
  trap job and agrees with it on a trap-free sweep (no logger gaps, no certificate transients, every
  handover at the same minute), so the trap stays out of broad families;
- a corner stress job (20,000 readings, the extreme temperatures and ratios) agrees.
"""

import importlib.util
import json
import random
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

RECORD = {
    "product": "Ferivax 20 mg/mL",
    "labelled_range_c": [2.0, 8.0],
    "freeze_point_c": -5.0,
    "activation_ratio_k": 10000.0,
    "bands": [
        {"band": "cold", "lower_c": -5.0, "upper_c": 2.0, "allowance_h": 24},
        {"band": "warm", "lower_c": 8.0, "upper_c": 25.0, "allowance_h": 72},
        {"band": "hot", "lower_c": 25.0, "upper_c": 40.0, "allowance_h": 4},
    ],
}


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_job(path, legs, lots, record=RECORD):
    """legs: {name: [(offset_minutes, temp)]}, lots: [{lot, legs, certificate?}]"""
    (path / "loggers").mkdir(parents=True)
    base = datetime(2031, 5, 4, 6, 0)
    for name, rows in legs.items():
        with open(path / "loggers" / f"{name}.csv", "w", encoding="utf-8") as handle:
            handle.write("timestamp,temp_c\n")
            for offset, temp in rows:
                handle.write(f"{base + timedelta(minutes=offset):%Y-%m-%dT%H:%M},{temp:.1f}\n")
    (path / "stability.json").write_text(json.dumps(record), encoding="utf-8")
    (path / "lots.json").write_text(json.dumps(lots), encoding="utf-8")
    return path


def series(start, steps, temps):
    rows, moment = [], start
    for index, temp in enumerate(temps):
        if index:
            moment += steps[(index - 1) % len(steps)]
        rows.append((moment, temp))
    return rows


def run(app, job):
    out = subprocess.run([sys.executable, "-I", "-S", str(app / "tools" / "coldchain_run.py"), str(job)], capture_output=True, text=True)
    if out.returncode:
        return {"lots": [{"error": out.stderr.strip().splitlines()[-1]}]}
    return json.loads(out.stdout)


EDITS = {
    # departures reverted one at a time inside the Oracle
    "D1_last_reading_holds_60": ("attribution.py", "LAST_READING_MINUTES = 0", "LAST_READING_MINUTES = 60"),
    "D2_band_ends": ("bands.py", "    if stability.low <= temp <= stability.high:", "    if stability.low <= temp < stability.high:"),
    "D2b_above_lower_end": ("bands.py", "            if temp > band.lower:", "            if temp >= band.lower:"),
    "D3_worst_leg": ("disposition.py", "{band.name: sum(leg_totals[band.name]", "{band.name: max(leg_totals[band.name]"),
    "D4_no_prior": ("disposition.py", "band.allowance_h * 60 - prior[band.name] - band_time[band.name]", "band.allowance_h * 60 - band_time[band.name]"),
    "D5_gap_openers_charged": ("disposition.py", "band_minutes(leg.readings, logged_holds(held), stability)", "band_minutes(leg.readings, held, stability)"),
    "D7_rounded_compare": ("disposition.py", "    elif mkt > stability.high", "    elif round(mkt, 1) > stability.high"),
    "D8_truncate": ("report.py", "    return round(minutes / 60, 2)", "    return int(minutes / 60 * 100) / 100"),
    "D9_gap_60": ("attribution.py", "        if span > GAP_MINUTES:\n            total += span", "        if span > 60:\n            total += span"),
    # natural over-repairs of the traps
    "TX_hold_rule_written_into_holds": ("attribution.py", "            held.append(readings[index + 1].minute - reading.minute)", "            span = readings[index + 1].minute - reading.minute\n            held.append(span if span <= GAP_MINUTES else 0)"),
    "TX_weights_from_band_holds": ("disposition.py", "        weights += held", "        weights += logged_holds(held)"),
    "TY_transients_counted": ("disposition.py", " if entry >= EXCURSION_ENTRY_MINUTES)", ")"),
    # governed (2.3), recorded as a wrong path, not counted as a trap
    "G_flattened_weights": ("disposition.py", "    mkt = mean_kinetic_temperature(temps, weights, stability.ratio)", "    mkt = mean_kinetic_temperature([r.temp for r in lot.readings()], holds(lot.readings()), stability.ratio)"),
}


def main():
    task = Path(sys.argv[1]).resolve()
    model = load_module(task / "solution" / "model.py", "sop_model")
    jobgen = load_module(task / "solution" / "jobgen.py", "sop_jobgen")
    results = {"departures": {}, "kept_steps": {}, "traps": {}, "isolation": {}, "stress": {}}
    ok = True
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        shipped = tmp / "shipped" / "app"
        shutil.copytree(task / "environment" / "app", shipped)
        oracle_root = tmp / "oracle"
        shutil.copytree(task / "environment" / "app", oracle_root / "app")
        subprocess.run(["patch", "-s", "-p1", "-i", str(task / "solution" / "fix.patch")], cwd=oracle_root, check=True)
        oracle = oracle_root / "app"
        mutants = {}
        for name, (file, old, new) in EDITS.items():
            root = tmp / "m" / name
            shutil.copytree(oracle, root)
            path = root / "src" / "coldchain" / file
            text = path.read_text()
            assert text.count(old) == 1, (name, old)
            path.write_text(text.replace(old, new))
            mutants[name] = root

        jobs = {}
        # D1: the last reading of the export is warm; it holds nought
        jobs["D1"] = write_job(tmp / "D1", {"a": series(0, [10], [5.0, 5.0, 12.0])}, [{"lot": "L101", "legs": ["a"]}])
        # D2: readings exactly on the labelled limits and on band ends
        jobs["D2"] = write_job(tmp / "D2", {"a": series(0, [10], [8.0, 25.0, 2.0, -5.0, 40.0, 5.0, 8.0, 5.0])}, [{"lot": "L102", "legs": ["a"]}])
        # D3: three legs with 30 warm minutes each against a one-hour allowance
        record3 = json.loads(json.dumps(RECORD))
        record3["bands"][1]["allowance_h"] = 1
        warm_leg = [5.0, 12.0, 12.0, 12.0, 5.0, 5.0]
        jobs["D3"] = write_job(tmp / "D3", {"a": series(0, [10], warm_leg), "b": series(50, [10], warm_leg), "c": series(100, [10], warm_leg)}, [{"lot": "L103", "legs": ["a", "b", "c"]}], record3)
        # D4: a certificate excursion entry that exhausts the hot allowance
        jobs["D4"] = write_job(tmp / "D4", {"a": series(0, [10], [5.0, 30.0, 5.0])}, [{"lot": "L104", "legs": ["a"], "certificate": {"hot": [231]}}])
        # D5: a warm reading that opens a 90-minute gap, in a lot of one temperature (MKT cannot move)
        jobs["D5"] = write_job(tmp / "D5", {"a": series(0, [10, 90, 10], [12.0, 12.0, 12.0, 12.0])}, [{"lot": "L105", "legs": ["a"]}])
        # D7: MKT a few thousandths above the upper limit that rounds onto it
        jobs["D7"] = write_job(tmp / "D7", {"a": series(0, [30, 30, 30, 5], [8.0, 8.0, 8.0, 8.1, 8.0])}, [{"lot": "L106", "legs": ["a"]}])
        # D8: 55 minutes is 0.9166... hours
        jobs["D8"] = write_job(tmp / "D8", {"a": series(0, [25, 30], [12.0, 12.0, 5.0])}, [{"lot": "L107", "legs": ["a"]}])
        # D9: a 45-minute spacing beside a logged one, one temperature in range
        jobs["D9"] = write_job(tmp / "D9", {"a": series(0, [45, 10], [5.0, 5.0, 5.0])}, [{"lot": "L108", "legs": ["a"]}])
        # TX: readings of different temperatures opening gaps of 90 and 45 minutes
        jobs["TX"] = write_job(tmp / "TX", {"a": series(0, [10, 90, 10, 45, 10], [5.0, 12.0, 5.0, 30.0, 5.0, 5.0])}, [{"lot": "L109", "legs": ["a"]}])
        # TY: certificate transients (under 15 minutes) beside excursion entries
        jobs["TY"] = write_job(tmp / "TY", {"a": series(0, [10], [5.0, 12.0, 5.0])}, [{"lot": "L110", "legs": ["a"], "certificate": {"warm": [10, 14, 15, 30], "hot": [1, 14]}}])
        # G: three legs, logged intervals only, handovers of 20 and 400 minutes
        jobs["G"] = write_job(
            tmp / "G",
            {"a": series(0, [10], [5.0, 7.0, 12.0]), "b": series(40, [10], [3.0, 30.0, 4.0]), "c": series(460, [15], [20.0, 6.0])},
            [{"lot": "L111", "legs": ["a", "b", "c"]}],
        )

        expected = {name: model.expected_report(job)["lots"][0] for name, job in jobs.items()}
        unpatched = {name: run(shipped, job)["lots"][0] for name, job in jobs.items()}
        oracle_out = {name: run(oracle, job)["lots"][0] for name, job in jobs.items()}
        for name in jobs:
            if oracle_out[name] != expected[name]:
                ok = False
                results.setdefault("oracle_mismatch", {})[name] = [oracle_out[name], expected[name]]

        columns = {"D1": "mkt_c", "D2": "band_hours", "D3": "band_hours", "D4": "remaining_hours", "D5": "band_hours", "D7": "disposition", "D8": "band_hours", "D9": "unlogged_hours"}
        revert = {"D1": ["D1_last_reading_holds_60"], "D2": ["D2_band_ends", "D2b_above_lower_end"], "D3": ["D3_worst_leg"], "D4": ["D4_no_prior"], "D5": ["D5_gap_openers_charged"], "D7": ["D7_rounded_compare"], "D8": ["D8_truncate"], "D9": ["D9_gap_60"]}
        for name, column in columns.items():
            row = {"column": column, "model": expected[name][column], "unpatched": unpatched[name][column], "unpatched_differs": unpatched[name][column] != expected[name][column]}
            for mutant in revert[name]:
                got = run(mutants[mutant], jobs[name])["lots"][0]
                row[f"revert_{mutant}_differs"] = got.get(column) != expected[name][column]
                ok &= row[f"revert_{mutant}_differs"]
            ok &= row["unpatched_differs"]
            results["departures"][name] = row

        # TX kept figure: today's holds() already gives every reading but the last the minutes to the
        # next reading of its export, which is the SOP 5.1 weight (already-correct code)
        probe = subprocess.run(
            [sys.executable, "-I", "-S", "-c",
             "import sys, json; sys.path.insert(0, sys.argv[1]); from coldchain.records import load_job; from coldchain.attribution import holds;"
             "s, lots = load_job(sys.argv[2]); print(json.dumps([holds(leg.readings)[:-1] for leg in lots[0].legs]))",
             str(shipped / "src"), str(jobs["TX"])], capture_output=True, text=True, check=True)
        record_tx, lots_tx, exports_tx = model.load(jobs["TX"])
        want_w = [model.weight(exports_tx[name])[:-1] for name in lots_tx[0]["legs"]]
        same = json.loads(probe.stdout) == want_w
        results["kept_steps"]["TX"] = {"figure": "SOP 5.1 weights of every reading but the last", "model": want_w, "unpatched_holds": json.loads(probe.stdout), "unpatched_matches": same}
        ok &= same

        trap_mutants = {"TX": ["TX_hold_rule_written_into_holds", "TX_weights_from_band_holds"], "TY": ["TY_transients_counted"], "G": ["G_flattened_weights"]}
        for trap, names in trap_mutants.items():
            for mutant in names:
                got = run(mutants[mutant], jobs[trap])["lots"][0]
                differs = got != expected[trap]
                results["traps"][mutant] = {"job": trap, "differs_from_model": differs, "fields": sorted(k for k in got if got[k] != expected[trap].get(k))}
                ok &= differs

        rng = random.Random(7)
        sweep_lots = 0
        disagreements = {name: 0 for name in [m for names in trap_mutants.values() for m in names]}
        for index in range(40):
            job = jobgen.write_job(tmp / f"s{index}", rng, lots=4, max_legs=5, max_readings=30, gaps=False, handover=0, transients=False, inside=0.8)
            want = model.expected_report(job)
            sweep_lots += len(want["lots"])
            for mutant in disagreements:
                if run(mutants[mutant], job) != want:
                    disagreements[mutant] += 1
        results["isolation"] = {"trap_free_sweep_jobs": 40, "lots": sweep_lots, "jobs_where_trap_mutant_differs": disagreements}
        ok &= not any(disagreements.values())

        # corner stress: 20,000 readings one minute apart, extremes of temperature and ratio
        stress_rng = random.Random(11)
        temps = [stress_rng.choice([-40.0, 60.0, 2.0, 8.0, 25.0, stress_rng.randint(-400, 600) / 10]) for _ in range(20000)]
        for ratio in (5000.0, 20000.0):
            record = json.loads(json.dumps(RECORD))
            record["activation_ratio_k"] = ratio
            record["bands"][0]["lower_c"] = -40.0
            record["freeze_point_c"] = -40.0
            record["bands"][2]["upper_c"] = 60.0
            job = write_job(tmp / f"stress{int(ratio)}", {"big": series(0, [1, 30, 7, 60, 5, 1440, 1, 1, 1, 1], temps)}, [{"lot": "L999", "legs": ["big"], "certificate": {"warm": [10080] * 12 + [14] * 38}}], record)
            want = model.expected_report(job)
            got = run(oracle, job)
            results["stress"][str(ratio)] = {"agree": want == got, "mkt_c": want["lots"][0]["mkt_c"]}
            ok &= want == got

    results["status"] = "pass" if ok else "fail"
    Path(sys.argv[2]).write_text(json.dumps(results, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(results, indent=1))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
