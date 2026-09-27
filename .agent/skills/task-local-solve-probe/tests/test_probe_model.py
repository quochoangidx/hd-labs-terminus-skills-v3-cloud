from __future__ import annotations

import importlib.util
import json
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "probe.py"
SPEC = importlib.util.spec_from_file_location("probe", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def write_jsonl(path: Path, models: list[str]) -> Path:
    lines = [json.dumps({"type": "user", "message": {"role": "user", "content": "go"}})]
    for model in models:
        lines.append(json.dumps({"type": "assistant", "message": {"role": "assistant", "model": model}}))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def test_served_models_reads_assistant_entries(tmp_path: Path) -> None:
    path = write_jsonl(tmp_path / "a.jsonl", ["claude-opus-5", "<synthetic>", "claude-opus-5"])
    assert MODULE.served_models(path) == ["claude-opus-5", "claude-opus-5"]


def test_opus5_run_is_accepted() -> None:
    assert MODULE.claude_probe_model_errors("claude-opus-5", ["claude-opus-5"]) == []
    assert MODULE.claude_probe_model_errors("claude-opus-5", ["claude-opus-5-20260101"]) == []


def test_opus55_served_run_is_rejected_even_when_declared_opus5() -> None:
    errors = MODULE.claude_probe_model_errors("claude-opus-5", ["claude-opus-5", "claude-opus-5-5"])
    assert any("claude-opus-5-5" in error for error in errors)


def test_alias_declaration_is_rejected() -> None:
    errors = MODULE.claude_probe_model_errors("opus", ["claude-opus-5"])
    assert any("--model must be claude-opus-5" in error for error in errors)


def test_transcript_without_model_is_rejected() -> None:
    assert MODULE.claude_probe_model_errors("claude-opus-5", [])


def test_record_accepts_a_cycle_folder_of_the_same_slug() -> None:
    assert MODULE.probe_dir_matches("tbrain-x", "tbrain-x")
    assert MODULE.probe_dir_matches("tbrain-x", "tbrain-x-cycle-2")
    assert MODULE.probe_dir_matches("tbrain-x", "tbrain-x-skeleton")
    assert not MODULE.probe_dir_matches("tbrain-x", "tbrain-xy-cycle-1")
    assert not MODULE.probe_dir_matches("", "tbrain-x")
