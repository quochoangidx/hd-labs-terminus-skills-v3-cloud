"""Verifier for thermostep.simulate against the TS-4 note.

Expected runs are in expected.json, written by regenerate.py from cases.py with
model.py, which solves the note's equations in 60-digit arithmetic without
importing the package. The expected values are read into memory and the file is
removed before any candidate code runs. The candidate package only ever runs in
a separate, unprivileged process through a driver owned by the verifier image.
"""

import json
import math
import os
import shutil
import signal
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cases  # noqa: E402
import model  # noqa: E402

CANDIDATE_SRC = "/app/src"
DRIVER = "/opt/driver/run_case.py"
if not os.path.exists(DRIVER):  # running outside the verifier image
    DRIVER = os.path.join(HERE, "driver", "run_case.py")
    CANDIDATE_SRC = os.environ.get("THERMOSTEP_SRC", CANDIDATE_SRC)
EXPECTED_PATH = os.path.join(HERE, "expected.json")

with open(EXPECTED_PATH) as _fh:
    EXPECTED = json.load(_fh)
if HERE == "/tests":
    try:
        os.unlink(EXPECTED_PATH)
    except OSError:
        pass

PYTHON = sys.executable
TEMP_TOL = 1e-6
TIME_TOL = 1e-6


def _run_candidate(case):
    """Run one case through the package in its own unprivileged process group."""
    scratch = tempfile.mkdtemp(prefix="thermostep-")
    os.chmod(scratch, 0o777)
    env = {"PATH": "/usr/local/bin:/usr/bin:/bin", "HOME": scratch, "LANG": "C.UTF-8"}
    command = [PYTHON, "-I", "-S", DRIVER, CANDIDATE_SRC]
    demote = os.geteuid() == 0
    proc = subprocess.Popen(
        ["setpriv", "--reuid=65534", "--regid=65534", "--clear-groups", "--no-new-privs"] + command
        if demote else command,
        cwd=scratch, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, text=True, start_new_session=True)
    try:
        out, err = proc.communicate(json.dumps(case), timeout=300)
    except subprocess.TimeoutExpired:
        out, err = "", "timed out after 300 s"
    finally:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        proc.wait()
        shutil.rmtree(scratch, ignore_errors=True)
    assert proc.returncode == 0, f"simulate failed:\n{err[-2000:]}"
    return json.loads(out)


def _number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def _compare(got, want):
    temps, heater, switches = got["temperatures"], got["heater"], got["switches"]
    assert len(temps) == len(want["temperatures"]), "one (T1, T2) pair is reported per sample"
    assert heater == want["heater"], f"heater states {heater} differ from {want['heater']}"
    assert len(switches) == len(want["switches"]), (
        f"{len(switches)} switches reported, {len(want['switches'])} expected; "
        f"first expected {want['switches'][:3]}, got {switches[:3]}")
    for index, ((t, on), (wt, won)) in enumerate(zip(switches, want["switches"])):
        assert on == won and _number(t) and abs(t - wt) <= TIME_TOL, (
            f"switch {index + 1}: got {(t, on)}, expected {(wt, won)}")
    for index, (pair, wpair) in enumerate(zip(temps, want["temperatures"])):
        for node, (a, b) in enumerate(zip(pair, wpair), start=1):
            assert _number(a) and abs(a - b) <= TEMP_TOL, (
                f"sample {index}: T{node} is {a!r}, expected {b!r}")


def check(name):
    _compare(_run_candidate(cases.CASES[name]), EXPECTED[name])


def test_expected_runs_come_from_the_model():
    """The frozen expectations are the model's answers (spot re-derivation)."""
    assert sorted(EXPECTED) == sorted(cases.CASES)
    for name in ("insulated_enclosure", "uncoupled_nodes_equal_rates", "coupled_heater_on_ambient_ramps"):
        c = cases.CASES[name]
        fresh = model.simulate(c["net"], c["times"], c["ambient"], c["power"], c["t1"], c["t2"],
                               c["on"], c["thermostat"])
        _compare(fresh, EXPECTED[name])


def test_coupled_heater_on_ambient_ramps():
    check("coupled_heater_on_ambient_ramps")


def test_heater_off_ambient_swings():
    check("heater_off_ambient_swings")


def test_unequal_intervals_and_power_changes():
    check("unequal_intervals_and_power_changes")


def test_wall_without_path_to_ambient():
    check("wall_without_path_to_ambient")


def test_chamber_without_path_to_ambient():
    check("chamber_without_path_to_ambient")


def test_insulated_enclosure():
    check("insulated_enclosure")


def test_uncoupled_nodes_equal_rates():
    check("uncoupled_nodes_equal_rates")


def test_uncoupled_nodes_different_rates():
    check("uncoupled_nodes_different_rates")


def test_nearly_uncoupled_equal_rates():
    check("nearly_uncoupled_equal_rates")


def test_heater_off_without_thermostat_stays_off():
    check("heater_off_without_thermostat_stays_off")


def test_thermostat_single_switch_off():
    check("thermostat_single_switch_off")


def test_thermostat_cycles_inside_one_interval():
    check("thermostat_cycles_inside_one_interval")


def test_thermostat_crossing_between_samples_heater_on():
    check("thermostat_crossing_between_samples_heater_on")


def test_thermostat_dip_between_samples_heater_off():
    check("thermostat_dip_between_samples_heater_off")


def test_thermostat_switches_off_at_start():
    check("thermostat_switches_off_at_start")


def test_thermostat_switches_on_at_start():
    check("thermostat_switches_on_at_start")


def test_thermostat_heater_on_without_power_does_not_switch():
    check("thermostat_heater_on_without_power_does_not_switch")


def test_thermostat_insulated_enclosure():
    check("thermostat_insulated_enclosure")


def test_thermostat_uncoupled_equal_rates():
    check("thermostat_uncoupled_equal_rates")


def test_oven_long_schedule():
    check("oven_long_schedule")
