"""Verifier for the four morning plans in /app/plans.

Each plan is read as data and checked with the verifier's own copy of the
dispatch rules (check_plan.py) against the verifier's own copy of that morning's
orders; no code from /app runs. A plan passes when every rule holds and its cost
is no more than the morning's target.
"""

import json
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from check_plan import PlanError, evaluate, load_plan  # noqa: E402

PLANS = os.environ.get("DISPATCH_PLANS", "/app/plans")
with open(os.path.join(HERE, "targets.json")) as _fh:
    TARGETS = json.load(_fh)


def _orders(morning):
    with open(os.path.join(HERE, "orders", morning + ".json")) as fh:
        return json.load(fh)


def _plan(morning):
    path = os.path.join(PLANS, morning + ".json")
    assert os.path.isfile(path), f"no plan at {path}"
    return load_plan(path)


def _cost(morning):
    try:
        return evaluate(_orders(morning), _plan(morning))
    except PlanError as exc:
        pytest.fail(f"{morning}: plan breaks the dispatch rules: {exc}")


def check_feasible(morning):
    _cost(morning)


def check_target(morning):
    cost = _cost(morning)
    assert cost <= TARGETS[morning], f"{morning}: plan costs {cost}, target is {TARGETS[morning]}"


def test_harbour_lanes_plan_is_runnable():
    check_feasible("harbour-lanes")


def test_harbour_lanes_plan_meets_target():
    check_target("harbour-lanes")


def test_old_town_plan_is_runnable():
    check_feasible("old-town")


def test_old_town_plan_meets_target():
    check_target("old-town")


def test_riverside_plan_is_runnable():
    check_feasible("riverside")


def test_riverside_plan_meets_target():
    check_target("riverside")


def test_north_ring_plan_is_runnable():
    check_feasible("north-ring")


def test_north_ring_plan_meets_target():
    check_target("north-ring")
