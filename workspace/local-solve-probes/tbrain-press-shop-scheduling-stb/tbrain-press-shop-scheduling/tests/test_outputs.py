"""Verifier for the four weekly press schedules in /app/schedules.

Each schedule is read as data and run with the verifier's own copy of the press
rules (check_schedule.py) against the verifier's own copy of that week; no code
from /app runs. A schedule passes when every job is placed on a press that can
run it and its cost is no more than the week's target.
"""

import json
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from check_schedule import ScheduleError, evaluate  # noqa: E402

SCHEDULES = os.environ.get("PRESS_SCHEDULES", "/app/schedules")
with open(os.path.join(HERE, "targets.json")) as _fh:
    TARGETS = json.load(_fh)
MAX_BYTES = 2_000_000


def _week(name):
    with open(os.path.join(HERE, "weeks", name + ".json")) as fh:
        return json.load(fh)


def _cost(name):
    path = os.path.join(SCHEDULES, name + ".json")
    assert os.path.isfile(path), f"no schedule at {path}"
    assert os.path.getsize(path) <= MAX_BYTES, "schedule file is implausibly large"
    with open(path) as fh:
        schedule = json.load(fh)
    try:
        return evaluate(_week(name), schedule)
    except ScheduleError as exc:
        pytest.fail(f"{name}: schedule breaks the press rules: {exc}")


def check_target(name):
    cost = _cost(name)
    assert cost <= TARGETS[name], f"{name}: schedule costs {cost}, target is {TARGETS[name]}"


def test_week_36_schedule_is_valid():
    _cost("week-36")


def test_week_36_schedule_meets_target():
    check_target("week-36")


def test_week_37_schedule_is_valid():
    _cost("week-37")


def test_week_37_schedule_meets_target():
    check_target("week-37")


def test_week_38_schedule_is_valid():
    _cost("week-38")


def test_week_38_schedule_meets_target():
    check_target("week-38")


def test_week_39_schedule_is_valid():
    _cost("week-39")


def test_week_39_schedule_meets_target():
    check_target("week-39")
