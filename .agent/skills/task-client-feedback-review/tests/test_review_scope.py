from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "review_task.py"
sys.path.insert(0, str(SCRIPT.parent))
SPEC = importlib.util.spec_from_file_location("review_task_scope", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_mechanical_scope_skips_external_evidence(monkeypatch, tmp_path: Path) -> None:
    def forbidden(*_args, **_kwargs):
        raise AssertionError("external evidence checker ran")

    monkeypatch.setattr(MODULE, "check_instruction_sufficiency_evidence", forbidden)
    monkeypatch.setattr(MODULE, "check_semantic_coverage_evidence", forbidden)

    result = MODULE.review(tmp_path, include_external_evidence=False)

    assert result["evidence_scope"] == "mechanical_only"


def test_full_scope_runs_external_evidence(monkeypatch, tmp_path: Path) -> None:
    calls: list[str] = []

    monkeypatch.setattr(
        MODULE,
        "check_instruction_sufficiency_evidence",
        lambda *_args, **_kwargs: calls.append("sufficiency"),
    )
    monkeypatch.setattr(
        MODULE,
        "check_semantic_coverage_evidence",
        lambda *_args, **_kwargs: calls.append("semantic"),
    )

    result = MODULE.review(tmp_path)

    assert result["evidence_scope"] == "full"
    assert calls == ["sufficiency", "semantic"]
