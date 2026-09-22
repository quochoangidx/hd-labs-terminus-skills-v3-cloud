from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


SCRIPT = Path(__file__).parents[1] / "scripts" / "independence_check.py"
SPEC = importlib.util.spec_from_file_location("independence_check", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


@pytest.fixture
def task(tmp_path: Path) -> Path:
    root = tmp_path / "tbrain-independence"
    (root / "environment/repo/cairnlift").mkdir(parents=True)
    (root / "tests").mkdir()
    (root / "environment/repo/cairnlift/__init__.py").write_text("")
    (root / "environment/repo/cairnlift/scale.py").write_text("def depth(w, h):\n    return 1\n")
    return root


def kinds(task: Path, model: str) -> list[str]:
    return [f["kind"] for f in MODULE.scan_model(task / model, MODULE.package_names(task))]


def test_a_model_rederived_from_the_authority_is_independent(task: Path) -> None:
    (task / "tests/model.py").write_text(
        "import math\n\n\ndef depth(width, height):\n"
        "    # Worked out from the note: halve the shorter side, rounding up.\n"
        "    return max(0, int(math.log2(min(width, height))) - 1)\n"
    )

    assert kinds(task, "tests/model.py") == []


def test_importing_the_package_under_repair_is_contamination(task: Path) -> None:
    (task / "tests/model.py").write_text("from cairnlift.scale import depth\n")

    assert "import" in kinds(task, "tests/model.py")


def test_a_relative_import_counts_too(task: Path) -> None:
    (task / "tests/model.py").write_text("from . import scale\n")

    assert "import" in kinds(task, "tests/model.py")


def test_shelling_out_to_the_implementation_is_contamination(task: Path) -> None:
    """Running it is the same circularity as importing it, spelled differently."""
    (task / "tests/model.py").write_text(
        "import subprocess\n\n\ndef depth(w, h):\n"
        "    return subprocess.run(['python', '-c', 'import cairnlift'], capture_output=True)\n"
    )

    assert "dynamic_entry" in kinds(task, "tests/model.py")


def test_an_unrelated_subprocess_call_is_reported_but_not_blocking(task: Path) -> None:
    (task / "tests/model.py").write_text(
        "import subprocess\n\n\ndef tools():\n    return subprocess.run(['javap', '-v'])\n"
    )

    assert kinds(task, "tests/model.py") == ["dynamic_entry_unresolved"]


def test_package_names_are_read_from_the_environment_tree(task: Path) -> None:
    assert "cairnlift" in MODULE.package_names(task)
    assert "scale" in MODULE.package_names(task)
