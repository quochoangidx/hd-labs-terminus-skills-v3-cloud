"""Verifier for the four daily stand plans in /app/plans.

Each plan is read as data and checked with the verifier's own copy of the stand
rules (check_plan.py) against the verifier's own copy of that day; no code from
/app runs. A plan passes when it is valid under the rules and its cost is no
more than the day's target.
"""

import json
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from check_plan import PlanError, evaluate  # noqa: E402

PLANS = os.environ.get("STAND_PLANS", "/app/plans")
with open(os.path.join(HERE, "targets.json")) as _fh:
    TARGETS = json.load(_fh)
MAX_BYTES = 2_000_000


def _day(name):
    with open(os.path.join(HERE, "days", name + ".json")) as fh:
        return json.load(fh)


def _cost(name):
    path = os.path.join(PLANS, name + ".json")
    assert os.path.isfile(path), f"no plan at {path}"
    assert os.path.getsize(path) <= MAX_BYTES, "plan file is implausibly large"
    with open(path) as fh:
        plan = json.load(fh)
    try:
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
