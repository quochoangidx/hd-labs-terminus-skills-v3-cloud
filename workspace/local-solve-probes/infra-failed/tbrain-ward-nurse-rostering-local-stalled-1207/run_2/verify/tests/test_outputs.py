"""Verifier for the four ward rosters in /app/rosters.

Each roster is read as data and checked with the verifier's own copy of the
rostering rules (check_roster.py) against the verifier's own copy of that ward;
no code from /app runs. A roster passes when it is valid under the rules and its
penalty is no more than the ward's target.
"""

import json
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from check_roster import RosterError, evaluate, load_roster  # noqa: E402

ROSTERS = os.environ.get("WARD_ROSTERS", "/app/rosters")
with open(os.path.join(HERE, "targets.json")) as _fh:
    TARGETS = json.load(_fh)


def _ward(name):
    with open(os.path.join(HERE, "wards", name + ".json")) as fh:
        return json.load(fh)


def _penalty(name):
    path = os.path.join(ROSTERS, name + ".json")
    assert os.path.isfile(path), f"no roster at {path}"
    try:
        roster = load_roster(path)
        return evaluate(_ward(name), roster)
    except RosterError as exc:
        pytest.fail(f"{name}: roster breaks the rostering rules: {exc}")


def check_target(name):
    penalty = _penalty(name)
    assert penalty <= TARGETS[name], f"{name}: roster penalty {penalty}, target is {TARGETS[name]}"


def test_ash_roster_is_valid():
    _penalty("ash")


def test_ash_roster_meets_target():
    check_target("ash")


def test_birch_roster_is_valid():
    _penalty("birch")


def test_birch_roster_meets_target():
    check_target("birch")


def test_cedar_roster_is_valid():
    _penalty("cedar")


def test_cedar_roster_meets_target():
    check_target("cedar")


def test_dale_roster_is_valid():
    _penalty("dale")


def test_dale_roster_meets_target():
    check_target("dale")
