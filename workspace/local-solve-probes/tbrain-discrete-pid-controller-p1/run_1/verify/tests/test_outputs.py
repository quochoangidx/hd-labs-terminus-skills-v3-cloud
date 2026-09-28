"""Verifier for the looptune controller.

Expected values come from model.py, which works each rule out from
/app/docs/control-note.md without importing the package. Where the note is
silent, model.py copies the shipped helper's expression, and one family of
cases is also compared directly against the shipped package.

The candidate package only ever runs in a separate, unprivileged process, through
a driver owned by the verifier image.
"""

import json
import math
import os
import shutil
import signal
import subprocess
import sys
import tempfile

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import model  # noqa: E402

CANDIDATE_SRC = "/app/src"
DRIVER = "/opt/driver/run_session.py"
SHIPPED_SRC = "/opt/shipped/src"
if not os.path.exists(DRIVER):  # running outside the verifier image
    DRIVER = os.path.join(HERE, "driver", "run_session.py")
    SHIPPED_SRC = os.path.join(HERE, "shipped")
    CANDIDATE_SRC = os.environ.get("LOOPTUNE_SRC", CANDIDATE_SRC)

PYTHON = sys.executable
FIELDS = ("u", "integral", "t_p", "t_i", "t_d", "t_f", "t_v", "t_u")
WIDE = {"low": -50.0, "high": 50.0}


def _run_candidate(session, src):
    """Replay a session through a package in its own unprivileged process group."""
    scratch = tempfile.mkdtemp(prefix="looptune-")
    os.chmod(scratch, 0o777)
    env = {"PATH": "/usr/local/bin:/usr/bin:/bin", "HOME": scratch, "LANG": "C.UTF-8"}
    command = [PYTHON, "-I", "-S", DRIVER, src]
    demote = os.geteuid() == 0
    proc = subprocess.Popen(
        ["setpriv", "--reuid=65534", "--regid=65534", "--clear-groups", "--no-new-privs"] + command
        if demote else command,
        cwd=scratch, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, text=True, start_new_session=True)
    try:
        out, err = proc.communicate(json.dumps(session), timeout=60)
    except subprocess.TimeoutExpired:
        out, err = "", "timed out"
    finally:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        proc.wait()
        shutil.rmtree(scratch, ignore_errors=True)
    assert proc.returncode == 0, f"session failed to run:\n{err[-2000:]}"
    return json.loads(out)


def _close(got, want):
    if isinstance(got, str) or isinstance(want, str) or got is None:
        return got == want
    return math.isclose(got, want, rel_tol=1e-9, abs_tol=1e-12)


def _compare(rows, expected, fields=FIELDS):
    assert len(rows) == len(expected), f"{len(rows)} steps reported, {len(expected)} expected"
    for index, (row, want) in enumerate(zip(rows, expected)):
        for key in fields:
            assert _close(row.get(key), want[key]), (
                f"step {index + 1}: {key} is {row.get(key)!r}, expected {want[key]!r}"
            )


def check(tuning, ops, fields=FIELDS):
    rows = _run_candidate({"tuning": tuning, "ops": ops}, CANDIDATE_SRC)
    _compare(rows, model.run(tuning, ops), fields)
    return rows


def steps(pairs, f=0.0):
    return [["step", r, y, f] for r, y in pairs]


# --- section 2: proportional term -------------------------------------------------

def test_proportional_weights_only_the_setpoint():
    tuning = {"gain": 2.0, "setpoint_weight": 0.4, **WIDE}
    check(tuning, steps([(1.0, 0.0), (1.0, 0.3), (0.5, 0.8), (-1.0, 0.2), (-1.0, -1.4)]))


def test_proportional_weight_of_nought_keeps_the_measurement():
    tuning = {"gain": 1.5, "setpoint_weight": 0.0, **WIDE}
    check(tuning, steps([(2.0, 0.5), (2.0, -0.25), (-3.0, 1.0)]))


def test_proportional_only_output_is_gain_times_error():
    tuning = {"gain": 2.5, "setpoint_weight": 1.0, **WIDE}
    ops = [["step", 1.0, 0.2, 0.0], ["step", 0.4, -0.6, 0.3], ["step", -2.0, 1.0, -0.8]]
    rows = check(tuning, ops)
    for (_, r, y, f), row in zip(ops, rows):
        assert _close(row["u"], 2.5 * (r - y) + f)


# --- section 3: integral term -----------------------------------------------------

def test_integral_uses_the_gain_and_the_full_error():
    tuning = {"gain": 3.0, "integral_time": 2.0, "setpoint_weight": 0.5, **WIDE}
    check(tuning, steps([(1.0, 0.0), (1.0, 0.25), (1.0, 0.5), (0.2, 0.9), (-0.5, 0.1)]))


def test_integral_addition_is_seen_from_the_next_step():
    tuning = {"gain": 1.0, "integral_time": 0.5, **WIDE}
    rows = check(tuning, steps([(1.0, 0.0), (1.0, 0.0), (1.0, 0.0)]))
    assert _close(rows[0]["t_i"], 0.0)


# --- section 4: derivative term ---------------------------------------------------

def test_derivative_ignores_setpoint_steps():
    tuning = {"gain": 2.0, "derivative_time": 0.5, "filter_divisor": 10.0, **WIDE}
    rows = check(tuning, steps([(0.0, 0.2), (1.0, 0.2), (-1.0, 0.2), (0.5, 0.2)]))
    assert all(_close(row["t_d"], 0.0) for row in rows)


def test_derivative_uses_the_backward_difference():
    tuning = {"gain": 1.2, "derivative_time": 0.3, "filter_divisor": 8.0, **WIDE}
    check(tuning, steps([(0.0, 0.0), (0.0, 0.1), (0.0, 0.3), (0.0, 0.6), (0.0, 0.6), (0.0, 0.6), (0.0, 0.2)]))


def test_derivative_first_step_has_no_kick():
    tuning = {"gain": 2.0, "derivative_time": 0.5, "filter_divisor": 10.0, **WIDE}
    rows = check(tuning, steps([(0.0, 3.0), (0.0, 3.0), (0.0, 2.5)]))
    assert _close(rows[0]["t_d"], 0.0)


# --- section 5: forming the output ------------------------------------------------

def test_feedforward_is_inside_the_limits():
    tuning = {"gain": 1.0}
    check(tuning, [["step", 0.0, -0.5, 0.8], ["step", 0.0, 0.3, -0.9], ["step", 0.0, 0.0, 0.4],
                   ["step", 0.0, 1.5, -0.2]])


def test_limits_at_or_past_each_other_give_the_high_limit():
    tuning = {"gain": 1.0, "low": 1.0, "high": -1.0}
    check(tuning, steps([(0.0, 0.0), (3.0, 0.0), (-3.0, 0.0), (0.0, 0.5)]))
    tuning = {"gain": 1.0, "low": 0.25, "high": 0.25}
    check(tuning, steps([(0.0, 0.0), (3.0, 0.0), (-3.0, 0.0)]))


def test_slew_allowance_is_rate_times_period():
    tuning = {"gain": 1.0, "slew": 2.0, "period": 0.1, "low": -2.0, "high": 2.0}
    check(tuning, steps([(-0.5, 0.0), (0.9, 0.0), (0.9, 0.0), (0.9, 0.0), (0.9, 0.0),
                         (0.9, 0.0), (0.9, 0.0), (0.9, 0.0), (-1.5, 0.0), (-1.5, 0.0)]))


def test_first_step_is_not_slewed():
    tuning = {"gain": 1.0, "slew": 0.01, "period": 0.1}
    rows = check(tuning, steps([(0.7, 0.0), (0.7, 0.0), (-0.7, 0.0)]))
    assert _close(rows[0]["u"], 0.7)


def test_slew_acts_after_the_limits():
    tuning = {"gain": 1.0, "slew": 2.0, "period": 0.1}
    ops = [["manual", 3.0], ["step", 0.5, 0.0, 0.0], ["auto"]] + steps([(0.5, 0.0)] * 5)
    check(tuning, ops)
    ops = steps([(0.9, 0.0), (0.9, 0.0)]) + [["retune", {"high": 0.2}]] + steps([(0.9, 0.0)] * 5)
    check(tuning, ops)


# --- section 6: anti-windup tracking ----------------------------------------------

def test_tracking_pulls_the_integral_back_from_a_limit():
    tuning = {"gain": 2.0, "integral_time": 1.0, "tracking_time": 0.5}
    check(tuning, steps([(2.0, 0.0)] * 6 + [(0.0, 0.0)] * 4 + [(-2.0, 0.0)] * 3))


# --- section 7: manual mode -------------------------------------------------------

def test_manual_sets_the_integral_to_match_the_manual_output():
    tuning = {"gain": 1.5, "integral_time": 2.0, "derivative_time": 0.4, "filter_divisor": 5.0,
              "setpoint_weight": 0.6}
    ops = (steps([(0.5, 0.0), (0.5, 0.1)])
           + [["manual", 0.3], ["step", 0.5, 0.25, 0.2], ["step", 0.5, 0.45, 0.2],
              ["manual", -0.4], ["step", 0.5, 0.3, -0.1], ["auto"]]
           + steps([(0.5, 0.3), (0.5, 0.35), (0.6, 0.35)], f=-0.1))
    rows = check(tuning, ops)
    for row in rows[2:5]:
        assert row["t_v"] == row["u"]


def test_manual_output_is_returned_unlimited():
    tuning = {"gain": 1.0, "slew": 0.5, "low": -1.0, "high": 1.0}
    ops = steps([(0.2, 0.0)]) + [["manual", 2.5]] + steps([(0.2, 0.0)] * 3) + [["manual", -4.0]] + steps([(0.2, 0.0)])
    rows = check(tuning, ops)
    assert [row["u"] for row in rows[1:]] == [2.5, 2.5, 2.5, -4.0]


# --- section 8: retuning ----------------------------------------------------------

def test_retune_of_gain_and_weight_keeps_the_output_level():
    tuning = {"gain": 2.0, "integral_time": 1.5, "setpoint_weight": 0.5, **WIDE}
    ops = (steps([(1.0, 0.0), (1.0, 0.2), (1.0, 0.4)])
           + [["retune", {"gain": 4.0}]] + steps([(1.0, 0.4), (1.0, 0.5)])
           + [["retune", {"setpoint_weight": 0.8}]] + steps([(1.0, 0.5), (0.0, 0.5)])
           + [["retune", {"gain": 1.0, "setpoint_weight": 0.2}]] + steps([(0.0, 0.5)]))
    check(tuning, ops)


# --- where the note is silent: the package's present behaviour stands -------------

def test_weight_outside_nought_to_one_keeps_the_present_proportional():
    for weight in (1.5, -0.5):
        tuning = {"gain": 2.0, "setpoint_weight": weight, **WIDE}
        ops = steps([(1.0, 0.0), (1.0, 0.3), (-0.5, 0.8), (0.25, -1.0)])
        rows = check(tuning, ops)
        shipped = _run_candidate({"tuning": tuning, "ops": ops}, SHIPPED_SRC)
        _compare(rows, shipped)


def test_integral_time_below_nought_keeps_the_present_addition():
    tuning = {"gain": 3.0, "integral_time": -2.0, "setpoint_weight": 0.5, **WIDE}
    check(tuning, steps([(1.0, 0.0), (1.0, 0.25), (0.4, 0.5), (-1.0, 0.5)]))


def test_filter_divisor_below_nought_keeps_the_present_derivative():
    tuning = {"gain": 2.0, "derivative_time": 0.5, "filter_divisor": -0.5, **WIDE}
    check(tuning, steps([(1.0, 0.0), (1.0, 0.0), (1.0, 0.4), (0.5, 0.5), (0.0, 0.5)]))


def test_derivative_time_below_nought_keeps_the_present_derivative():
    tuning = {"gain": 1.0, "derivative_time": -0.4, "filter_divisor": 10.0, **WIDE}
    check(tuning, steps([(0.5, 0.0), (0.5, 0.1), (0.0, 0.1), (0.0, 0.3)]))


def test_slew_below_nought_keeps_the_present_limit():
    tuning = {"gain": 1.0, "slew": -0.5, "period": 0.1, **WIDE}
    check(tuning, steps([(0.3, 0.0), (0.3, 0.0), (0.3, 0.0), (-0.2, 0.0)]))


def test_tracking_time_below_nought_keeps_the_present_feedback():
    tuning = {"gain": 2.0, "integral_time": 1.0, "tracking_time": -1.0}
    check(tuning, steps([(2.0, 0.0)] * 5 + [(0.0, 0.0)] * 3))


# --- whole runs -------------------------------------------------------------------

def test_closed_loop_run_follows_the_note():
    tuning = {"gain": 1.8, "integral_time": 4.0, "derivative_time": 0.6, "filter_divisor": 8.0,
              "tracking_time": 2.0, "setpoint_weight": 0.7, "period": 0.1, "low": -1.0,
              "high": 1.0, "slew": 2.0}
    plant = {"y0": 0.1, "pole": 0.12, "gain": 1.3}
    plan = [["hold", 0.5, 0.0, 60], ["retune", {"gain": 2.4, "setpoint_weight": 0.9}],
            ["hold", 0.9, 0.1, 50], ["manual", 0.2], ["hold", 0.9, 0.1, 20], ["auto"],
            ["hold", -0.4, -0.05, 70], ["retune", {"slew": 0.7, "tracking_time": 0.8}],
            ["hold", 0.3, 0.0, 60]]
    check(tuning, model.closed_loop_ops(tuning, plan, plant))
