"""Verifier for the four edition layouts in /app/layouts.

Each layout is read as data and checked with the verifier's own copy of the make-up
rules (check_layout.py) against the verifier's own copy of that edition; no code from
/app runs. A layout passes when it is valid under the rules and its cost is no
more than the edition's target.
"""

import json
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from check_layout import LayoutError, evaluate, load_layout  # noqa: E402

LAYOUTS = os.environ.get("AD_LAYOUTS", "/app/layouts")
with open(os.path.join(HERE, "targets.json")) as _fh:
    TARGETS = json.load(_fh)


def _edition(name):
    with open(os.path.join(HERE, "editions", name + ".json")) as fh:
        return json.load(fh)


def _cost(name):
    path = os.path.join(LAYOUTS, name + ".json")
    assert os.path.isfile(path), f"no layout at {path}"
    try:
        layout = load_layout(path)
        return evaluate(_edition(name), layout)
    except LayoutError as exc:
        pytest.fail(f"{name}: layout breaks the make-up rules: {exc}")


def check_target(name):
    cost = _cost(name)
    assert cost <= TARGETS[name], f"{name}: layout costs {cost}, target is {TARGETS[name]}"


def test_mon_layout_is_valid():
    _cost("mon")


def test_mon_layout_meets_target():
    check_target("mon")


def test_wed_layout_is_valid():
    _cost("wed")


def test_wed_layout_meets_target():
    check_target("wed")


def test_fri_layout_is_valid():
    _cost("fri")


def test_fri_layout_meets_target():
    check_target("fri")


def test_sat_layout_is_valid():
    _cost("sat")


def test_sat_layout_meets_target():
    check_target("sat")
