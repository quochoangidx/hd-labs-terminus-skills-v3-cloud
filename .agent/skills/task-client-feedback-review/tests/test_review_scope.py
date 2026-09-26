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
        "COPY --from=golang:1.24@sha256:" + digest + " /usr/local/go /usr/local/go\n"
    )
    assert len(MODULE.cloud_builder_copy_issues(bad)) == 1

    # Named --chown values are resolved by the cloud builder; only the
    # tag+digest --from ref above is rejected.
    good = (
        "FROM image@sha256:" + digest + " AS builder\n"
        "COPY --chown=root:root src/ /app/\n"
        "COPY --chown=1000:1000 src/ /app/\n"
        "COPY --from=builder /app/tool /usr/local/bin/tool\n"
        "COPY --from=golang@sha256:" + digest + " /usr/local/go /usr/local/go\n"
    )
    assert MODULE.cloud_builder_copy_issues(good) == []


def test_review_scans_nested_dockerfiles(tmp_path: Path) -> None:
    nested = tmp_path / "environment" / "repo" / "tools"
    nested.mkdir(parents=True)
    (nested / "Dockerfile").write_text(
        "FROM scratch\n"
        "COPY --from=golang:1.24@sha256:" + "a" * 64 + " /usr/local/go /go\n"
    )

    result = MODULE.review(tmp_path, include_external_evidence=False)

    assert any(
        finding["check"] == "dockerfile-modal-syntax"
        and finding["path"] == "environment/repo/tools/Dockerfile"
        for finding in result["findings"]
    )


def test_review_blocks_verifier_deps_in_the_agent_image(tmp_path: Path) -> None:
    env = tmp_path / "environment"
    env.mkdir()
    (env / "Dockerfile").write_text(
        "FROM python:3.13@sha256:" + "a" * 64 + "\n"
        "RUN apt-get update && apt-get install -y tmux asciinema\n"
        "RUN pip install --no-cache-dir pytest==9.1.1\n"
    )

    result = MODULE.review(tmp_path, include_external_evidence=False)

    assert any(
        finding["check"] == "dockerfile-verifier-deps" and finding["severity"] == "blocker"
        for finding in result["findings"]
    )


def test_review_allows_a_clean_agent_image(tmp_path: Path) -> None:
    env = tmp_path / "environment"
    env.mkdir()
    (env / "Dockerfile").write_text(
        "FROM python:3.13@sha256:" + "a" * 64 + "\n"
        "RUN apt-get update && apt-get install -y tmux asciinema\n"
    )

    result = MODULE.review(tmp_path, include_external_evidence=False)

    assert not any(f["check"] == "dockerfile-verifier-deps" for f in result["findings"])


def test_review_allows_pytest_when_a_shipped_suite_uses_it(tmp_path: Path) -> None:
    app = tmp_path / "environment" / "app"
    app.mkdir(parents=True)
    (tmp_path / "environment" / "Dockerfile").write_text(
        "FROM python:3.13@sha256:" + "a" * 64 + "\n"
        "RUN apt-get update && apt-get install -y tmux asciinema\n"
        "RUN pip install pytest==9.1.1\n"
    )
    (app / "README.md").write_text("Run the suite with `python3 -m pytest tests -q`.\n")

    result = MODULE.review(tmp_path, include_external_evidence=False)

    assert not any(f["check"] == "dockerfile-verifier-deps" for f in result["findings"])


def _driver_task(tmp_path: Path, run_line: str) -> Path:
    for rel in ("environment/app/tools/pkg_run.py", "tests/shipped/tools/pkg_run.py"):
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / rel).write_text("# fixed driver\n")
    (tmp_path / "tests" / "test_outputs.py").write_text(run_line)
    return tmp_path


def test_review_blocks_grading_through_the_candidate_driver(tmp_path: Path) -> None:
    task = _driver_task(
        tmp_path,
        'APP_ROOT = os.environ.get("PKG_APP", "/app")\n'
        "def run_job(job, *, root: str = APP_ROOT):\n"
        '    cmd = [sys.executable, "-I", f"{root}/tools/pkg_run.py"]\n',
    )

    result = MODULE.review(task, include_external_evidence=False)

    assert any(f["check"] == "verifier-trusts-candidate-driver" for f in result["findings"])


def test_review_allows_a_verifier_owned_driver(tmp_path: Path) -> None:
    task = _driver_task(
        tmp_path,
        'DRIVER_ROOT = os.environ.get("PKG_DRIVER", "/opt/driver")\n'
        "def run_job(job, *, root: str = DRIVER_ROOT):\n"
        '    cmd = [sys.executable, "-I", f"{root}/tools/pkg_run.py"]\n',
    )

    result = MODULE.review(task, include_external_evidence=False)

    assert not any(f["check"] == "verifier-trusts-candidate-driver" for f in result["findings"])


def test_review_allows_byte_comparing_the_submitted_driver(tmp_path: Path) -> None:
    task = _driver_task(
        tmp_path,
        'DRIVER = Path("/opt/driver/tools/pkg_run.py")\n'
        'SUBMITTED = Path("/app/tools/pkg_run.py")\n'
        "def run_job(job):\n"
        '    return subprocess.run([sys.executable, "-I", str(DRIVER), job])\n'
        "def test_job():\n"
        '    run_job("a")\n'
        "def test_driver_unchanged():\n"
        '    assert SUBMITTED.read_bytes() == Path("/tests/shipped/tools/pkg_run.py").read_bytes()\n',
    )

    result = MODULE.review(task, include_external_evidence=False)

    checks = {f["check"] for f in result["findings"]}
    assert "verifier-trusts-candidate-driver" not in checks
    assert "protected_file_checked_before_run" not in checks


def test_review_blocks_executing_an_aliased_candidate_driver(tmp_path: Path) -> None:
    task = _driver_task(
        tmp_path,
        'SUBMITTED = Path("/app/tools/pkg_run.py")\n'
        "def run_job(job):\n"
        '    return subprocess.run(\n'
        '        ["python3", str(SUBMITTED), job],\n'
        "        check=True,\n"
        "    )\n",
    )

    result = MODULE.review(task, include_external_evidence=False)

    assert any(f["check"] == "verifier-trusts-candidate-driver" for f in result["findings"])


def test_review_blocks_a_test_sh_that_runs_the_candidate_driver(tmp_path: Path) -> None:
    task = _driver_task(tmp_path, "def test_nothing():\n    pass\n")
    (task / "tests" / "test.sh").write_text("python3 /app/tools/pkg_run.py job.json out\n")

    assert MODULE.candidate_driver_trusted(
        MODULE.TaskView(task).files(), {}, (task / "tests" / "test.sh").read_text()
    ) == ["pkg_run.py"]


def test_driver_checked_only_before_the_job_tests_is_advisory(tmp_path: Path) -> None:
    task = _driver_task(
        tmp_path,
        'SUBMITTED = Path("/app/tools/pkg_run.py")\n'
        "def test_driver_unchanged():\n"
        '    assert SUBMITTED.read_bytes() == Path("/tests/shipped/tools/pkg_run.py").read_bytes()\n'
        "def test_job():\n"
        "    pass\n",
    )

    result = MODULE.review(task, include_external_evidence=False)

    found = [f for f in result["findings"] if f["check"] == "protected_file_checked_before_run"]
    assert found and all(f["severity"] != "blocker" for f in found)
    assert not any(f["check"] == "verifier-trusts-candidate-driver" for f in result["findings"])

    (task / "tests" / "test.sh").write_text(
        "python3 -m pytest /tests/test_outputs.py\ncmp /app/tools/pkg_run.py /tests/shipped/tools/pkg_run.py || echo 0 > /logs/verifier/reward.txt\n"
    )
    result = MODULE.review(task, include_external_evidence=False)
    assert not any(f["check"] == "protected_file_checked_before_run" for f in result["findings"])


def _toml_task(tmp_path: Path, explanation: str) -> Path:
    (tmp_path / "task.toml").write_text(
        '[metadata]\ndifficulty = "core"\ncategory = "Operations"\nsubcategory = "Finance"\n'
        'tags = ["a", "b", "c"]\n'
        f'difficulty_explanation = "{explanation}"\n'
    )
    return tmp_path


def test_difficulty_role_accepts_any_domain_role(tmp_path: Path) -> None:
    for role in ("retail controller", "rates analyst", "hydrologist", "cost accountant"):
        task = _toml_task(tmp_path, f"A {role} has to reconcile interacting rounding rules by hand.")
        result = MODULE.review(task, include_external_evidence=False)
        assert not any(f["check"] == "difficulty-explanation-role" for f in result["findings"]), role


def test_difficulty_role_missing_is_never_a_blocker(tmp_path: Path) -> None:
    task = _toml_task(tmp_path, "Interacting rounding rules must be reconciled by hand.")
    result = MODULE.review(task, include_external_evidence=False)
    found = [f for f in result["findings"] if f["check"] == "difficulty-explanation-role"]
    assert found and all(f["severity"] != "blocker" for f in found)
