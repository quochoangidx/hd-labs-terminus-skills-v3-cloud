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


INDEPENDENT_MODEL = "def depth(width, height):\n    return max(0, min(width, height) // 2)\n"


def run_main(monkeypatch, capsys, *argv: str) -> tuple[int, str]:
    monkeypatch.setattr("sys.argv", ["independence_check.py", *argv])
    code = MODULE.main()
    return code, capsys.readouterr().out


def test_a_model_under_tests_is_blocking_even_when_independent(
    task, tmp_path, monkeypatch, capsys
) -> None:
    """writing-tests.md: no end-to-end solver in tests/ (crop-water v3, royalty v3 returns)."""
    (task / "tests/model.py").write_text(INDEPENDENT_MODEL)
    report = tmp_path / "report.json"

    code, out = run_main(
        monkeypatch,
        capsys,
        str(task),
        "--model",
        "tests/model.py",
        "--report-json",
        str(report),
    )

    assert code == 1
    assert "model_in_tests" in out
    data = MODULE.json.loads(report.read_text())
    assert data["status"] == "fail"
    assert data["models"][0]["status"] == "model_in_tests"
    # The declared model is already blocking, so it is not repeated as an advisory.
    assert data["advisories"] == []


def test_a_model_in_solution_still_gets_the_independence_check(task, monkeypatch, capsys) -> None:
    (task / "solution").mkdir()
    (task / "solution/model.py").write_text(INDEPENDENT_MODEL)
    assert run_main(monkeypatch, capsys, str(task), "--model", "solution/model.py")[0] == 0

    (task / "solution/model.py").write_text("from cairnlift.scale import depth\n")
    code, out = run_main(monkeypatch, capsys, str(task), "--model", "solution/model.py")
    assert code == 1
    assert "contaminated" in out and "line 0: model_in_tests" not in out


def test_a_dotted_path_that_escapes_tests_is_not_under_tests(task: Path) -> None:
    assert MODULE.under_tests(task, "tests/model.py")
    assert MODULE.under_tests(task, "./tests/sub/../model.py")
    assert not MODULE.under_tests(task, "tests/../solution/model.py")


def test_the_scan_flags_an_imported_model_module(task: Path) -> None:
    (task / "tests/model.py").write_text(INDEPENDENT_MODEL)
    (task / "tests/test_outputs.py").write_text("import model\n")

    found = MODULE.scan_tests_for_models(task)

    assert [(f["path"], f["kind"]) for f in found] == [
        ("tests/model.py", "model_in_tests_suspected")
    ]


def test_the_scan_ignores_a_model_named_module_no_test_imports(task: Path) -> None:
    (task / "tests/model.py").write_text(INDEPENDENT_MODEL)
    (task / "tests/test_outputs.py").write_text("import json\n")

    assert MODULE.scan_tests_for_models(task) == []


def test_the_scan_flags_an_expected_maker_under_another_name(task: Path) -> None:
    (task / "tests/ledger.py").write_text("def compute_expected(job):\n    return [job]\n")
    (task / "tests/test_outputs.py").write_text("from ledger import compute_expected\n")

    assert [f["path"] for f in MODULE.scan_tests_for_models(task)] == ["tests/ledger.py"]


def test_the_scan_leaves_a_loader_of_sealed_expectations_alone(task: Path) -> None:
    (task / "tests/runs.py").write_text(
        "import json\nfrom pathlib import Path\n\n\ndef expected(name):\n"
        "    return json.loads((Path(__file__).parent / 'expected' / name).read_text())\n"
    )
    (task / "tests/jobgen.py").write_text("def sweep(seed):\n    return {'seed': seed}\n")
    (task / "tests/test_outputs.py").write_text("import jobgen\nimport runs\n")

    assert MODULE.scan_tests_for_models(task) == []


def test_the_scan_alone_advises_but_does_not_fail(task, monkeypatch, capsys) -> None:
    (task / "tests/oracle.py").write_text(INDEPENDENT_MODEL)
    (task / "tests/test_outputs.py").write_text("import oracle\n")

    code, out = run_main(monkeypatch, capsys, str(task))

    assert code == 0
    assert "model_in_tests_suspected" in out and "independence was not checked" in out
