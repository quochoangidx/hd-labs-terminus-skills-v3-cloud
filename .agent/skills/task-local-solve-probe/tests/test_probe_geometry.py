from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "probe.py"
SPEC = importlib.util.spec_from_file_location("probe", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_one_of_three_accepts_distinct_multi_node_failures() -> None:
    result = MODULE.semantic_failure_geometry(
        [
            ({"b", "c"}, {"a"}),
            ({"a"}, {"b", "c"}),
            ({"a", "b", "c"}, set()),
        ],
        {
            "a": {"M:a", "I:ab"},
            "b": {"M:b"},
            "c": {"I:bc"},
        },
        total=3,
        passed=1,
    )
    assert result["advanced_geometry_pass"] is True


def test_fixture_replication_cannot_create_multi_node_geometry() -> None:
    result = MODULE.semantic_failure_geometry(
        [
            ({"a3"}, {"a1", "a2"}),
            ({"a1"}, {"a2", "a3"}),
            ({"a1", "a2", "a3"}, set()),
        ],
        {"a1": {"M:a"}, "a2": {"M:a"}, "a3": {"M:a"}},
        total=3,
        passed=1,
    )
    assert result["advanced_geometry_pass"] is False
    assert result["semantic_decorrelated"] is False


def test_core_plus_accepts_zero_or_one_of_two_without_geometry_gate() -> None:
    for passed in (0, 1):
        assert MODULE.core_plus_recommendation(
            total=2,
            passed=passed,
            evidence_complete=True,
            failures={"semantic": 2 - passed},
            mode="counted",
        ) == "core_plus_shortlist"


def test_core_plus_rejects_all_pass_and_third_run() -> None:
    assert MODULE.core_plus_recommendation(
        total=2,
        passed=2,
        evidence_complete=True,
        failures={},
        mode="counted",
    ) == "rework_or_replace"
    assert MODULE.core_plus_recommendation(
        total=3,
        passed=1,
        evidence_complete=True,
        failures={"semantic": 2},
        mode="counted",
    ) == "unsupported_campaign_sample"
