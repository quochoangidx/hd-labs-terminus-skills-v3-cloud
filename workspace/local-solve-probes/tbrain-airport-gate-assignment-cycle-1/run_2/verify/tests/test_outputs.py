"""Verifier for the four daily stand plans in /app/plans.

Each plan is read as data and checked with the verifier's own copy of the stand
rules (check_plan.py) against the verifier's own copy of that day; no code from
/app runs. A plan passes when it is valid under the rules and its cost is no
more than the day's target.
"""

import gzip
import hashlib
import json
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from check_plan import PlanError, evaluate, load_plan  # noqa: E402

PLANS = os.environ.get("STAND_PLANS", "/app/plans")
with open(os.path.join(HERE, "targets.json")) as _fh:
    TARGETS = json.load(_fh)


with open(os.path.join(HERE, "days", "roster.json")) as _fh:
    ROSTER = json.load(_fh)


def _day(name):
    """The verifier's copy of a day: /app/days/<day>.json byte for byte, stored
    gzip-compressed, checked against the roster's counts and SHA-256."""
    want = ROSTER[name]
    with gzip.open(os.path.join(HERE, "days", name + ".json.gz"), "rb") as fh:
        raw = fh.read()
    assert hashlib.sha256(raw).hexdigest() == want["sha256"], f"{name}: verifier copy does not match its roster"
    day = json.loads(raw)
    assert (len(day["stands"]), len(day["turns"]), len(day["transfers"])) == (
        want["stands"], want["turns"], want["transfers"]), f"{name}: verifier copy is incomplete"
    return day


def _cost(name):
    path = os.path.join(PLANS, name + ".json")
    assert os.path.isfile(path), f"no plan at {path}"
    try:
        plan = load_plan(path)
        return evaluate(_day(name), plan)
    except PlanError as exc:
        pytest.fail(f"{name}: plan breaks the stand rules: {exc}")


def check_target(name):
    cost = _cost(name)
    assert cost <= TARGETS[name], f"{name}: plan costs {cost}, target is {TARGETS[name]}"


def test_day_1_plan_is_valid():
    _cost("day-1")


def test_day_1_plan_meets_target():
    check_target("day-1")


def test_day_2_plan_is_valid():
    _cost("day-2")


def test_day_2_plan_meets_target():
    check_target("day-2")


def test_day_3_plan_is_valid():
    _cost("day-3")


def test_day_3_plan_meets_target():
    check_target("day-3")


def test_day_4_plan_is_valid():
    _cost("day-4")


def test_day_4_plan_meets_target():
    check_target("day-4")
