from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


REPO = Path(__file__).resolve().parents[3].parent
SKILLS = REPO / ".agent" / "skills"
IMPLEMENTATIONS = {
    "panel_precheck": SKILLS / "terminus-regular-task-authoring/scripts/panel_precheck.py",
    "wrong_path_runner": SKILLS / "terminus-regular-task-authoring/scripts/wrong_path_runner.py",
    "revision_ledger_check": SKILLS / "terminus-regular-task-authoring/scripts/revision_ledger_check.py",
    "independence_check": SKILLS / "terminus-regular-task-authoring/scripts/independence_check.py",
    "semantic_coverage_check": SKILLS / "terminus-regular-task-authoring/scripts/semantic_coverage_check.py",
    "preprobe_check": SKILLS / "task-local-solve-probe/scripts/preprobe_check.py",
}


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(f"_snap_{name}", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_every_gate_computes_the_same_snapshot_hash(tmp_path: Path) -> None:
    """A receipt binds to this digest, so a second spelling makes it unreconcilable.

    Each gate carries its own copy so it can run standalone. That is fine only while
    the copies agree — one gate hashing differently produces receipts that every
    other gate rejects as stale, and the check it performed is silently wasted.
    """
    task = tmp_path / "tbrain-hash"
    (task / "environment").mkdir(parents=True)
    (task / "instruction.md").write_text("Fix the package.\n", encoding="utf-8")
    (task / "environment" / "core.py").write_text("def run():\n    return 1\n", encoding="utf-8")

    digests = {}
    for name, path in IMPLEMENTATIONS.items():
        if not path.is_file():
            pytest.fail(f"{name} not found at {path}")
        module = load(name, path)
        assert hasattr(module, "tree_hash"), f"{name} has no tree_hash"
        digests[name] = module.tree_hash(task)

    distinct = set(digests.values())
    assert len(distinct) == 1, f"snapshot hash disagrees across gates: {digests}"


def test_the_separators_distinguish_a_path_boundary(tmp_path: Path) -> None:
    """Without separators, moving bytes from a name into the content collides."""
    module = load("panel_precheck", IMPLEMENTATIONS["panel_precheck"])

    one = tmp_path / "one"
    one.mkdir()
    (one / "ab").write_text("c", encoding="utf-8")

    two = tmp_path / "two"
    two.mkdir()
    (two / "a").write_text("bc", encoding="utf-8")

    assert module.tree_hash(one) != module.tree_hash(two)
