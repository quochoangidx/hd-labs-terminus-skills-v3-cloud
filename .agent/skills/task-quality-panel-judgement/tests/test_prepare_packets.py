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

    assert manifest["snapshot_sha256"] == root.name
    coherent = root / "coherent_contract"
    reference = root / "correct_reference_solution"
    protected = root / "protected_ground_truth"
    sound = root / "sound_verifier"

    assert (coherent / "tests").is_dir()
    assert not (coherent / "solution").exists()
    assert (reference / "solution").is_dir()
    assert not (reference / "tests").exists()
    assert not (reference / "task.toml").exists()
    assert not (reference / "environment").exists()
    assert (protected / "tests").is_dir()
    assert not (protected / "solution").exists()
    assert not (protected / "instruction.md").exists()
    assert not (protected / "task.toml").exists()
    assert (sound / "tests").is_dir()
    assert not (sound / "solution").exists()
    assert not (sound / "task.toml").exists()
    assert not (sound / "environment").exists()
    assert (coherent / "instruction.md").is_file()
    assert (coherent / "task.toml").is_file()
    assert (coherent / "environment").is_dir()
    assert (reference / "instruction.md").is_file()
    assert (protected / "environment").is_dir()
    assert (sound / "instruction.md").is_file()
    for packet in (coherent, reference, protected, sound):
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
    assert third.parent.name != first.parent.name


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
