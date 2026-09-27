"""Verifier for the four production plans in /app/plans.

Each plan is read as data and checked with the verifier's own copy of the
production rules (check_plan.py) against the verifier's own copy of that site;
no code from /app runs. A plan passes when it is valid under the rules and its
cost is no more than the site's target.
"""

import json
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from check_plan import PlanError, evaluate, load_plan  # noqa: E402

PLANS = os.environ.get("SITE_PLANS", "/app/plans")
with open(os.path.join(HERE, "targets.json")) as _fh:
    TARGETS = json.load(_fh)


def _site(name):
    with open(os.path.join(HERE, "sites", name + ".json")) as fh:
        return json.load(fh)


def _cost(name):
    path = os.path.join(PLANS, name + ".json")
    assert os.path.isfile(path), f"no plan at {path}"
    try:
        plan = load_plan(path)
        return evaluate(_site(name), plan)
    except PlanError as exc:
        pytest.fail(f"{name}: plan breaks the production rules: {exc}")


def check_target(name):
    cost = _cost(name)
    assert cost <= TARGETS[name], f"{name}: plan costs {cost}, target is {TARGETS[name]}"


def test_dorset_plan_is_valid():
    _cost("dorset")


def test_dorset_plan_meets_target():
    check_target("dorset")


def test_kent_plan_is_valid():
    _cost("kent")


def test_kent_plan_meets_target():
    check_target("kent")


def test_fife_plan_is_valid():
    _cost("fife")


def test_fife_plan_meets_target():
    check_target("fife")


def test_tyne_plan_is_valid():
    _cost("tyne")


def test_tyne_plan_meets_target():
    check_target("tyne")
