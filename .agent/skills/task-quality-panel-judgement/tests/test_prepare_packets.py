from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


SCRIPT = Path(__file__).parents[1] / "scripts" / "prepare_packets.py"
SPEC = importlib.util.spec_from_file_location("prepare_packets", SCRIPT)
assert SPEC and SPEC.loader
PACKETS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PACKETS)


def make_task(root: Path) -> Path:
    task = root / "tbrain-panel-fixture"
    task.mkdir()
    (task / "instruction.md").write_text("Implement the requested behavior.\n")
    (task / "task.toml").write_text('version = "1.0"\n')
    for directory in ("environment", "solution", "tests"):
        path = task / directory
        path.mkdir()
        (path / f"{directory}.txt").write_text(f"{directory}\n")
    return task


def test_builds_axis_specific_packets(tmp_path: Path) -> None:
    task = make_task(tmp_path)
    root_manifest = PACKETS.build_packets(task, tmp_path / "packets")
    root = root_manifest.parent
    manifest = json.loads(root_manifest.read_text())

    assert manifest["snapshot_sha256"] == root.parent.name
    coherent = root / "coherent_contract"
    reference = root / "correct_reference_solution"
    protected = root / "protected_ground_truth"
    sound = root / "sound_verifier"
    determinism = root / "deterministic_execution"

    # Guide: contract, ground-truth and verifier review see the candidate-visible
    # contract/environment plus the tests and never the reference; reference
    # review sees the contract/environment plus the reference and never the
    # tests; determinism review sees all three.
    for packet in (coherent, protected, sound):
        assert (packet / "instruction.md").is_file()
        assert (packet / "environment").is_dir()
        assert (packet / "tests").is_dir()
        assert not (packet / "solution").exists()
    assert (reference / "instruction.md").is_file()
    assert (reference / "environment").is_dir()
    assert (reference / "solution").is_dir()
    assert not (reference / "tests").exists()
    for surface in ("instruction.md", "task.toml", "environment", "solution", "tests"):
        assert (determinism / surface).exists()
    # `task.toml` can disclose the intended solution through its explanation
    # fields, so only the axes the guide places it in receive it.
    assert (coherent / "task.toml").is_file()
    for packet in (reference, protected, sound):
        assert not (packet / "task.toml").exists()
    for packet in (coherent, reference, protected, sound, determinism):
        assert (packet / "_panel_docs" / "quality-panel-judge-guide.md").is_file()
        assert (packet / "_panel_docs" / "quality-panel-examples.md").is_file()
        assert (packet / "packet-manifest.json").is_file()


def test_snapshot_is_stable_and_changes_with_task(tmp_path: Path) -> None:
    task = make_task(tmp_path)
    output = tmp_path / "packets"
    first = PACKETS.build_packets(task, output)
    second = PACKETS.build_packets(task, output)
    assert first == second

    (task / "instruction.md").write_text("Implement revised behavior.\n")
    third = PACKETS.build_packets(task, output)
    assert third != first
    assert third.parent.parent.name != first.parent.parent.name


def test_rejects_output_inside_task(tmp_path: Path) -> None:
    task = make_task(tmp_path)
    with pytest.raises(ValueError, match="outside the task"):
        PACKETS.build_packets(task, task / "packets")


def test_rejects_escaping_symlink(tmp_path: Path) -> None:
    task = make_task(tmp_path)
    outside = tmp_path / "outside.txt"
    outside.write_text("secret\n")
    (task / "tests" / "escape").symlink_to(outside)

    with pytest.raises(ValueError, match="symlink escapes"):
        PACKETS.build_packets(task, tmp_path / "packets")


def test_explicit_contract_closure_preserves_isolation_and_old_packets(tmp_path: Path) -> None:
    task = make_task(tmp_path)
    doc = task / "environment" / "contract.md"
    doc.write_text("Use the declared schema.\n")
    output = tmp_path / "packets"
    before = PACKETS.build_packets(task, output)
    after = PACKETS.build_packets(task, output, ("environment/contract.md",))
    assert before != after
    assert before.exists()
    for axis in ("correct_reference_solution", "sound_verifier", "deterministic_execution"):
        packet = after.parent / axis
        assert (packet / "environment/contract.md").read_text() == doc.read_text()
        manifest = json.loads((packet / "packet-manifest.json").read_text())
        assert "environment/contract.md" in manifest["files"]
    # Every axis now carries the whole environment, so an explicitly selected
    # contract file records the authority without widening visibility.
    for axis in ("correct_reference_solution", "sound_verifier", "deterministic_execution"):
        assert (after.parent / axis / "environment/environment.txt").exists()
    assert (after.parent / "deterministic_execution/environment/environment.txt").exists()
    assert not (after.parent / "correct_reference_solution/tests").exists()
    assert not (after.parent / "sound_verifier/solution").exists()


@pytest.mark.parametrize("relative", ["tests/tests.txt", "solution/solution.txt",
                                       "environment/../solution/solution.txt", "/etc/passwd",
                                       "environment/missing.md", "environment"])
def test_rejects_unsafe_contract_selection(tmp_path: Path, relative: str) -> None:
    task = make_task(tmp_path)
    with pytest.raises(ValueError, match="contract file"):
        PACKETS.build_packets(task, tmp_path / "packets", (relative,))


def test_contract_symlink_cannot_import_solution(tmp_path: Path) -> None:
    task = make_task(tmp_path)
    (task / "environment/contract.md").symlink_to("../solution/solution.txt")
    with pytest.raises(ValueError, match="contract file"):
        PACKETS.build_packets(task, tmp_path / "packets", ("environment/contract.md",))


def test_doc_change_gets_new_recipe(tmp_path: Path, monkeypatch) -> None:
    task = make_task(tmp_path)
    docs = tmp_path / "mirror/docs/testing-and-validation"
    docs.mkdir(parents=True)
    for name in PACKETS.PANEL_DOCS:
        (docs / name).write_text("guide v1\n")
    monkeypatch.setattr(PACKETS, "repo_root", lambda: tmp_path / "mirror")
    before = PACKETS.build_packets(task, tmp_path / "packets")
    (docs / PACKETS.PANEL_DOCS[0]).write_text("guide v2\n")
    after = PACKETS.build_packets(task, tmp_path / "packets")
    assert before != after
    assert before.exists()
