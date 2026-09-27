from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).parents[1] / "scripts" / "sound_verifier_sweep.py"
SPEC = importlib.util.spec_from_file_location("sound_verifier_sweep", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

SHIPPED = "def total(runs):\n    return sum(runs[:8])\n"
FIXED = "def total(runs):\n    return sum(runs)\n"


@pytest.fixture
def task(tmp_path: Path) -> Path:
    root = tmp_path / "tbrain-sweep"
    (root / "environment/app/src").mkdir(parents=True)
    (root / "solution").mkdir()
    (root / "environment/app/src/calc.py").write_text(SHIPPED)
    patch = MODULE.unified_patch({"app/src/calc.py": SHIPPED}, {"app/src/calc.py": FIXED})
    (root / "solution/fix.patch").write_text(patch)
    return root


def catalog(**mutant_overrides) -> dict:
    mutant = {"class": "C5", "expect_failing": ["test_many_runs"], "rationale": "up to 80 runs",
              "edits": [{"file": "app/src/calc.py", "old": "sum(runs)", "new": "sum(runs[:64])"}]}
    mutant.update(mutant_overrides)
    return {"reference_patch": "solution/fix.patch", "mutants": {"c5-cap-64": mutant},
            "alternatives": {"alt-loop": {"edits": [{"file": "app/src/calc.py", "old": "return sum(runs)",
                                                     "new": "total = 0\n    for r in runs:\n        total += r\n    return total"}]}}}


def test_a_mutant_patch_is_the_reference_fix_plus_one_edit(task: Path, tmp_path: Path) -> None:
    patches = MODULE.build(task, catalog(), tmp_path)

    env = tmp_path / "check"
    subprocess.run(["cp", "-R", str(task / "environment"), str(env)], check=True)
    subprocess.run(["git", "apply", str(patches["c5-cap-64"])], cwd=env, check=True)
    assert (env / "app/src/calc.py").read_text() == "def total(runs):\n    return sum(runs[:64])\n"


def test_an_edit_whose_old_text_is_ambiguous_is_refused(task: Path, tmp_path: Path) -> None:
    bad = catalog(edits=[{"file": "app/src/calc.py", "old": "runs", "new": "items"}])
    with pytest.raises(SystemExit, match="occurs 2 times"):
        MODULE.build(task, bad, tmp_path)


def test_build_only_reports_untouched_classes(task: Path, tmp_path: Path) -> None:
    cat = tmp_path / "catalog.json"
    cat.write_text(json.dumps(catalog()))
    done = subprocess.run([sys.executable, str(SCRIPT), str(task), "--catalog", str(cat),
                           "--out", str(tmp_path / "out"), "--build-only"],
                          capture_output=True, text=True)
    assert done.returncode == 0, done.stdout + done.stderr
    assert "classes covered ['C5']" in done.stdout and "C18" in done.stdout


def test_a_mutant_without_a_class_or_witness_is_refused(task: Path, tmp_path: Path) -> None:
    cat = tmp_path / "catalog.json"
    cat.write_text(json.dumps(catalog(**{"class": "C99"})))
    done = subprocess.run([sys.executable, str(SCRIPT), str(task), "--catalog", str(cat),
                           "--out", str(tmp_path / "out")], capture_output=True, text=True)
    assert done.returncode == 2
