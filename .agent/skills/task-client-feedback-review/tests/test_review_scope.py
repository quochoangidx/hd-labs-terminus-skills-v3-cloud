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


def test_cloud_builder_copy_syntax() -> None:
    digest = "a" * 64
    bad = (
        "FROM --platform=linux/amd64 image@sha256:" + digest + " AS builder\n"
        "COPY --chown=root:root src/ /app/\n"
        "COPY --from=golang:1.24@sha256:" + digest + " /usr/local/go /usr/local/go\n"
    )
    assert len(MODULE.cloud_builder_copy_issues(bad)) == 2

    good = (
        "FROM image@sha256:" + digest + " AS builder\n"
        "COPY --chown=1000:1000 src/ /app/\n"
        "COPY --from=builder /app/tool /usr/local/bin/tool\n"
        "COPY --from=golang@sha256:" + digest + " /usr/local/go /usr/local/go\n"
    )
    assert MODULE.cloud_builder_copy_issues(good) == []


def test_review_scans_nested_dockerfiles(tmp_path: Path) -> None:
    nested = tmp_path / "environment" / "repo" / "tools"
    nested.mkdir(parents=True)
    (nested / "Dockerfile").write_text(
        "FROM scratch\nCOPY --chown=appuser:appuser . /app\n"
    )

    result = MODULE.review(tmp_path, include_external_evidence=False)

    assert any(
        finding["check"] == "dockerfile-modal-syntax"
        and finding["path"] == "environment/repo/tools/Dockerfile"
        for finding in result["findings"]
    )
