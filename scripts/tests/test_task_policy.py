from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("task_policy", REPO_ROOT / "scripts" / "task-policy.py")
assert SPEC and SPEC.loader
POLICY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(POLICY)

PYTHON_IMAGE = next(image for image in POLICY.CANONICAL_IMAGES if "/python:" in image)


def statuses(checks):
    return {check["check"]: check["status"] for check in checks}


class DockerPolicyTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.dockerfile = Path(self.temp_dir.name) / "Dockerfile"

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_every_external_stage_must_be_digest_pinned(self):
        self.dockerfile.write_text(
            f"FROM {PYTHON_IMAGE} AS builder\n"
            "FROM ubuntu:24.04\n"
            "RUN apt-get update && apt-get install -y tmux asciinema\n"
        )

        checks = POLICY.validate_dockerfile(self.dockerfile, "agent")

        self.assertEqual(statuses(checks)["agent-dockerfile:digests"], "fail")
        self.assertEqual(statuses(checks)["agent-dockerfile:final-base"], "fail")

    def test_noncanonical_base_requires_a_real_comment(self):
        self.dockerfile.write_text(
            "# Targeting Zig because the canonical list does not cover its toolchain.\n"
            "FROM example.invalid/zig@sha256:" + "a" * 64 + "\n"
            "RUN apt-get update && apt-get install -y tmux asciinema\n"
        )

        checks = POLICY.validate_dockerfile(self.dockerfile, "agent")

        self.assertEqual(statuses(checks)["agent-dockerfile:digests"], "pass")
        self.assertEqual(statuses(checks)["agent-dockerfile:final-base"], "pass")

    def test_platform_pin_and_apt_version_pins_fail_and_nproc_warns(self):
        self.dockerfile.write_text(
            f"FROM --platform=linux/amd64 {PYTHON_IMAGE}\n"
            "RUN apt-get update && apt-get install -y --no-install-recommends curl=7.88.1-10 tmux asciinema \\\n"
            "    && make -j$(nproc)\n"
        )
        checks = statuses(POLICY.validate_dockerfile(self.dockerfile, "agent"))
        self.assertEqual(checks["agent-dockerfile:no-platform-pin"], "fail")
        self.assertEqual(checks["agent-dockerfile:apt-unpinned"], "fail")
        self.assertEqual(checks["agent-dockerfile:no-bare-nproc"], "warn")

    def test_unpinned_apt_and_no_platform_pass(self):
        self.dockerfile.write_text(
            f"FROM {PYTHON_IMAGE}\n"
            "RUN apt-get update && apt-get install -y --no-install-recommends tmux asciinema \\\n"
            "    && pip install --no-cache-dir requests==2.32.3\n"
        )
        checks = statuses(POLICY.validate_dockerfile(self.dockerfile, "agent"))
        self.assertEqual(checks["agent-dockerfile:no-platform-pin"], "pass")
        self.assertEqual(checks["agent-dockerfile:apt-unpinned"], "pass")
        self.assertEqual(checks["agent-dockerfile:no-bare-nproc"], "pass")

    def test_agent_image_requires_harness_tools(self):
        self.dockerfile.write_text(f"FROM {PYTHON_IMAGE}\n")

        checks = POLICY.validate_dockerfile(self.dockerfile, "agent")

        self.assertEqual(statuses(checks)["agent-dockerfile:harness-tools"], "fail")

    def test_agent_image_must_keep_harness_binaries(self):
        for line in ("RUN rm -f /bin/sed /usr/bin/sed", "RUN rm -f /bin/grep /usr/bin/grep",
                     "RUN apt-get purge -y sed"):
            with self.subTest(line=line):
                self.dockerfile.write_text(f"FROM {PYTHON_IMAGE}\nRUN apt-get install -y tmux asciinema\n{line}\n")
                checks = statuses(POLICY.validate_dockerfile(self.dockerfile, "agent"))
                self.assertEqual(checks["agent-dockerfile:harness-binaries-kept"], "fail")

    def test_removing_other_binaries_keeps_the_harness_check_green(self):
        self.dockerfile.write_text(
            f"FROM {PYTHON_IMAGE}\nRUN apt-get install -y tmux asciinema\n"
            "RUN rm -f /usr/bin/sort /usr/bin/join /bin/date && rm -rf /var/lib/apt/lists/*\n"
            "# RUN rm -f /bin/sed (comment only)\n"
        )
        checks = statuses(POLICY.validate_dockerfile(self.dockerfile, "agent"))
        self.assertEqual(checks["agent-dockerfile:harness-binaries-kept"], "pass")

    def test_cloud_builder_accepts_named_copy_chown(self):
        """The builder resolves --chown names through /etc/passwd (portal 2026-09-17)."""
        self.dockerfile.write_text(
            f"FROM {PYTHON_IMAGE}\n"
            "COPY --chown=root:root app/ /app/\n"
            "RUN apt-get update && apt-get install -y tmux asciinema\n"
        )

        checks = POLICY.validate_dockerfile(self.dockerfile, "agent")

        self.assertEqual(statuses(checks)["agent-dockerfile:modal-syntax"], "pass")

    def test_cloud_builder_accepts_numeric_chown_and_stage_copy(self):
        self.dockerfile.write_text(
            f"FROM {PYTHON_IMAGE} AS builder\n"
            "COPY --chown=1000:1000 app/ /app/\n"
            f"FROM {PYTHON_IMAGE}\n"
            "COPY --from=builder /app/tool /usr/local/bin/tool\n"
            "RUN apt-get update && apt-get install -y tmux asciinema\n"
        )

        checks = POLICY.validate_dockerfile(self.dockerfile, "agent")

        self.assertEqual(statuses(checks)["agent-dockerfile:modal-syntax"], "pass")

    def test_cloud_builder_requires_digest_only_external_copy_source(self):
        digest = "a" * 64
        self.dockerfile.write_text(
            f"FROM {PYTHON_IMAGE}\n"
            f"COPY --from=golang:1.24-bookworm@sha256:{digest} /usr/local/go /usr/local/go\n"
            "RUN apt-get update && apt-get install -y tmux asciinema\n"
        )

        checks = POLICY.validate_dockerfile(self.dockerfile, "agent")
        self.assertEqual(statuses(checks)["agent-dockerfile:modal-syntax"], "fail")

        self.dockerfile.write_text(
            f"FROM {PYTHON_IMAGE}\n"
            f"COPY --from=golang@sha256:{digest} /usr/local/go /usr/local/go\n"
            "RUN apt-get update && apt-get install -y tmux asciinema\n"
        )
        checks = POLICY.validate_dockerfile(self.dockerfile, "agent")
        self.assertEqual(statuses(checks)["agent-dockerfile:modal-syntax"], "pass")

    def test_verifier_requires_pins_copy_and_artifact_landing(self):
        self.dockerfile.write_text(
            f"FROM {PYTHON_IMAGE}\n"
            "RUN pip install pytest pytest-json-ctrf\n"
        )

        checks = POLICY.validate_dockerfile(
            self.dockerfile,
            "verifier",
            ["/app/output.json"],
        )
        by_name = statuses(checks)

        self.assertEqual(by_name["verifier-dockerfile:pinned-deps"], "fail")
        self.assertEqual(by_name["verifier-dockerfile:copy-tests"], "fail")
        self.assertEqual(by_name["verifier-dockerfile:artifact-landing"], "fail")

    def test_verifier_accepts_an_explicit_file_list_copied_into_tests(self):
        """`COPY a b c /tests/` is as correct as `COPY . /tests/`.

        Separate-mode verifier images routinely name the files they own, and rejecting
        that spelling was a false alarm on a task that is otherwise correct.
        """
        self.dockerfile.write_text(
            f"FROM {PYTHON_IMAGE}\n"
            "RUN pip install pytest==9.1.1 pytest-json-ctrf==0.5.2\n"
            "COPY test.sh probe.py test_outputs.py Probe.java api.txt /tests/\n"
            "RUN mkdir -p /app\n"
        )

        checks = POLICY.validate_dockerfile(self.dockerfile, "verifier", ["/app/"])

        self.assertEqual(statuses(checks)["verifier-dockerfile:copy-tests"], "pass")

    def test_agent_image_must_not_install_verifier_deps(self):
        """`environment_hygiene` failed a task for exactly this line, split or not."""
        base = f"FROM {PYTHON_IMAGE}\nRUN apt-get update && apt-get install -y tmux asciinema\n"
        for install in (
            "RUN pip install --no-cache-dir pytest==9.1.1\n",
            "RUN python3 -m pip install \\\n    numpy==2.1.0 \\\n    pytest-json-ctrf==0.5.2\n",
        ):
            with self.subTest(install=install):
                self.dockerfile.write_text(base + install)
                checks = POLICY.validate_dockerfile(self.dockerfile, "agent")
                self.assertEqual(statuses(checks)["agent-dockerfile:no-verifier-deps"], "fail")

    def test_agent_image_verifier_deps_allowed_when_the_agent_runs_pytest(self):
        self.dockerfile.write_text(
            f"FROM {PYTHON_IMAGE}\nRUN apt-get update && apt-get install -y tmux asciinema\n"
            "RUN pip install pytest==9.1.1\n"
        )

        checks = POLICY.validate_dockerfile(self.dockerfile, "agent", agent_uses_pytest=True)

        self.assertEqual(statuses(checks)["agent-dockerfile:no-verifier-deps"], "pass")

    def test_agent_image_ignores_comments_and_similar_package_names(self):
        self.dockerfile.write_text(
            f"FROM {PYTHON_IMAGE}\nRUN apt-get update && apt-get install -y tmux asciinema\n"
            "# RUN pip install pytest==9.1.1\n"
            "RUN pip install hypothesis==6.0 pytest-cov-free-helper==1.0\n"
        )

        checks = POLICY.validate_dockerfile(self.dockerfile, "agent")

        self.assertEqual(statuses(checks)["agent-dockerfile:no-verifier-deps"], "pass")

    def test_task_scan_exempts_a_shipped_pytest_suite(self):
        task_dir = Path(self.temp_dir.name) / "tbrain-shipped-suite"
        app = task_dir / "environment" / "app"
        app.mkdir(parents=True)
        (task_dir / "environment" / "Dockerfile").write_text(
            f"FROM {PYTHON_IMAGE}\nRUN apt-get update && apt-get install -y tmux asciinema\n"
            "RUN pip install pytest==9.1.1\n"
        )
        (task_dir / "instruction.md").write_text("Fix the package.\n")

        self.assertEqual(
            statuses(POLICY.validate_task(task_dir))["agent-dockerfile:no-verifier-deps"], "fail"
        )

        (app / "README.md").write_text("Run `python3 -m pytest tests -q`.\n")
        self.assertEqual(
            statuses(POLICY.validate_task(task_dir))["agent-dockerfile:no-verifier-deps"], "pass"
        )

    def test_task_scan_checks_nested_dockerfiles(self):
        task_dir = Path(self.temp_dir.name) / "tbrain-nested-dockerfile"
        nested = task_dir / "environment" / "repo" / "tools"
        nested.mkdir(parents=True)
        (nested / "Dockerfile").write_text(
            "FROM scratch\n"
            f"COPY --from=golang:1.24-bookworm@sha256:{'a' * 64} /usr/local/go /go\n"
        )

        checks = POLICY.validate_task(task_dir)

        self.assertEqual(statuses(checks)["dockerfiles:modal-syntax"], "fail")

    def test_compose_networks_rejects_runner_colliding_keys(self):
        """check_compose_networks: the runner owns the namespace (portal 2026-09-17)."""
        errors = POLICY.compose_network_errors(
            "networks:\n"
            "  backend:\n"
            "    internal: true\n"
            "services:\n"
            "  app:\n"
            "    build: .\n"
            "    networks: [backend]\n"
            "    network_mode: bridge\n"
        )

        self.assertEqual(len(errors), 3)

    def test_compose_networks_accepts_default_project_network(self):
        errors = POLICY.compose_network_errors(
            "services:\n"
            "  app:\n"
            "    build: .\n"
            "    depends_on:\n"
            "      - db\n"
            "    environment:\n"
            "      - DATABASE_URL=postgresql://user:pass@db:5432/app\n"
            "  db:\n"
            f"    image: postgres:15@sha256:{'a' * 64}\n"
        )

        self.assertEqual(errors, [])


class TestSheCalibration(unittest.TestCase):
    """The test.sh rules judge properties, not one blessed spelling.

    Each case below is a correct verifier entrypoint that an earlier literal-match
    rule rejected. A false FAIL here is worse than a miss: with no reviewer to
    overrule it, an author obediently "fixes" a working task into a broken one.
    """

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.task_dir = Path(self.temp_dir.name) / "tbrain-shape"
        (self.task_dir / "tests").mkdir(parents=True)

    def run_checks(self, body: str):
        test_sh = self.task_dir / "tests" / "test.sh"
        test_sh.write_text(body)
        test_sh.chmod(0o755)
        return statuses(POLICY.validate_task(self.task_dir))

    def test_a_comment_naming_set_e_does_not_count_as_using_it(self):
        checks = self.run_checks(
            "#!/bin/bash\n"
            "# Deliberately NOT `set -e`: a failing pytest must still reach the reward write.\n"
            "set -uo pipefail\n"
            "install -d -m 700 /logs/verifier\n"
            "echo 0 > /logs/verifier/reward.txt\n"
            "/venv/bin/python -m pytest --ctrf /logs/verifier/ctrf.json /tests/test_outputs.py\n"
            "rc=$?\n"
            'if [ "$rc" -eq 0 ]; then\n'
            "  echo 1 > /logs/verifier/reward.txt\n"
            "else\n"
            "  echo 0 > /logs/verifier/reward.txt\n"
            "fi\n"
        )
        self.assertEqual(checks["test.sh:no-errexit"], "pass")

    def test_a_pinned_venv_interpreter_is_an_explicit_interpreter(self):
        checks = self.run_checks(
            "#!/bin/bash\n"
            "set -uo pipefail\n"
            "install -d -m 700 /logs/verifier\n"
            "echo 0 > /logs/verifier/reward.txt\n"
            "/venv/bin/python -m pytest --ctrf /logs/verifier/ctrf.json /tests/test_outputs.py\n"
            "rc=$?\n"
            'if [ "$rc" -eq 0 ]; then echo 1 > /logs/verifier/reward.txt; else echo 0 > /logs/verifier/reward.txt; fi\n'
        )
        self.assertEqual(checks["test.sh:python3"], "pass")

    def test_bare_python_on_path_is_still_rejected(self):
        checks = self.run_checks(
            "#!/bin/bash\n"
            "set -uo pipefail\n"
            "install -d -m 700 /logs/verifier\n"
            "echo 0 > /logs/verifier/reward.txt\n"
            "python -m pytest --ctrf /logs/verifier/ctrf.json /tests/test_outputs.py\n"
            "rc=$?\n"
            'if [ "$rc" -eq 0 ]; then echo 1 > /logs/verifier/reward.txt; else echo 0 > /logs/verifier/reward.txt; fi\n'
        )
        self.assertEqual(checks["test.sh:python3"], "fail")

    def test_mkdir_plus_chmod_over_several_paths_satisfies_the_default_reward(self):
        checks = self.run_checks(
            "#!/bin/bash\n"
            "set -uo pipefail\n"
            "mkdir -p /logs/verifier\n"
            "chmod 700 /logs/verifier /tests\n"
            "echo 0 > /logs/verifier/reward.txt\n"
            "/venv/bin/python3 -m pytest --ctrf /logs/verifier/ctrf.json /tests/test_outputs.py\n"
            "rc=$?\n"
            'if [[ "$rc" == 0 ]]; then echo 1 > /logs/verifier/reward.txt; else echo 0 > /logs/verifier/reward.txt; fi\n'
        )
        self.assertEqual(checks["test.sh:default-reward"], "pass")
        self.assertEqual(checks["test.sh:reward-footer"], "pass")

    def test_the_portal_template_shape_is_advisory_not_a_failure(self):
        """The published portal test.sh writes the reward only in its two branches.

        Pre-writing a default 0 is extra insurance against the verifier being killed,
        and worth suggesting — but failing a task built exactly to the documented
        template would reject correct work.
        """
        checks = self.run_checks(
            "#!/bin/bash\n"
            "set -uo pipefail\n"
            "mkdir -p /logs/verifier\n"
            "chmod 700 /logs/verifier\n"
            "/venv/bin/python3 -m pytest --ctrf /logs/verifier/ctrf.json /tests/test_outputs.py\n"
            "rc=$?\n"
            'if [ "$rc" -eq 0 ]; then echo 1 > /logs/verifier/reward.txt; else echo 0 > /logs/verifier/reward.txt; fi\n'
        )
        self.assertEqual(checks["test.sh:default-reward"], "warn")
        self.assertEqual(checks["test.sh:reward-dir"], "pass")
        self.assertEqual(checks["test.sh:reward-footer"], "pass")



if __name__ == "__main__":
    unittest.main()


class GradedDisclosedFixtureTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.task = Path(self.temp_dir.name)
        (self.task / "environment" / "app" / "samples").mkdir(parents=True)
        (self.task / "tests" / "samples").mkdir(parents=True)
        (self.task / "tests" / "legacy").mkdir(parents=True)
        (self.task / "environment" / "app" / "samples" / "north.stmt").write_bytes(b"TOTAL 1\n")
        (self.task / "tests" / "samples" / "north.stmt").write_bytes(b"TOTAL 1\n")
        (self.task / "environment" / "app" / "prog.cbl").write_bytes(b"PROGRAM\n")
        (self.task / "tests" / "legacy" / "prog.cbl").write_bytes(b"PROGRAM\n")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_a_test_function_that_grades_a_shipped_sample_fails(self):
        (self.task / "tests" / "test_outputs.py").write_text(
            '"""Builds legacy/prog.cbl at image build time."""\n'
            "def test_sample():\n"
            "    assert open('samples/north.stmt', 'rb').read() == run()\n"
        )
        hits = POLICY.graded_disclosed_fixtures(self.task)
        self.assertEqual(hits, ["tests/test_outputs.py::test_sample names tests/samples/north.stmt"])

    def test_a_build_stage_only_use_of_the_shipped_sample_passes(self):
        (self.task / "tests" / "test_outputs.py").write_text(
            '"""Builds legacy/prog.cbl and checks samples/north.stmt at image build time."""\n'
            "SAMPLE = 'samples/north.stmt'\n"
            "def test_hidden():\n"
            "    assert run('cases/a.dat') == open('expected/a.stmt', 'rb').read()\n"
        )
        self.assertEqual(POLICY.graded_disclosed_fixtures(self.task), [])


class UndisclosedSizeCapTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.task = Path(self.temp_dir.name)
        (self.task / "tests").mkdir()
        (self.task / "environment" / "docs").mkdir(parents=True)
        (self.task / "instruction.md").write_text("Write the plan to /app/plans/a.json.\n")
        (self.task / "environment" / "docs" / "rules.md").write_text("Other keys are ignored.\n")

    def tearDown(self):
        self.temp_dir.cleanup()

    def write_test(self, body):
        (self.task / "tests" / "test_outputs.py").write_text("import os\n\ndef test_plan():\n" + body)

    def test_an_undisclosed_upper_bound_fails(self):
        self.write_test("    assert os.path.getsize('/app/plans/a.json') <= 5_000_000\n")
        self.assertEqual(POLICY.undisclosed_size_caps(self.task), ["tests/test_outputs.py:4"])

    def test_a_reversed_bound_through_stat_fails(self):
        self.write_test("    assert 2_000_000 >= os.stat('/app/out').st_size\n")
        self.assertEqual(len(POLICY.undisclosed_size_caps(self.task)), 1)

    def test_a_non_empty_check_passes(self):
        self.write_test("    assert os.path.getsize('/app/plans/a.json') > 0\n")
        self.assertEqual(POLICY.undisclosed_size_caps(self.task), [])

    def test_a_stated_limit_passes(self):
        self.write_test("    assert os.path.getsize('/app/plans/a.json') <= 1_000_000\n")
        (self.task / "environment" / "docs" / "rules.md").write_text("A plan file is at most 1 MB.\n")
        self.assertEqual(POLICY.undisclosed_size_caps(self.task), [])


class ExpertHoursBoundTests(unittest.TestCase):
    """The platform's `solvable` check treats a large expert-hour estimate as evidence of an
    unreasonable amount of work (sed rev1: 12 h returned). The bound is a property of the
    number, not of any spelling."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.task_dir = Path(self.temp_dir.name) / "tbrain-hours"
        (self.task_dir / "tests").mkdir(parents=True)

    def run_checks(self, hours):
        (self.task_dir / "task.toml").write_text(
            'name = "tbrain-hours"\nartifacts = ["/app/"]\n[metadata]\n'
            f"expert_time_estimate_hours = {hours}\n"
        )
        return statuses(POLICY.validate_task(self.task_dir))

    def test_a_few_hours_passes(self):
        self.assertEqual(self.run_checks(5)["task.toml:expert-hours-bound"], "pass")
        self.assertEqual(self.run_checks(8)["task.toml:expert-hours-bound"], "pass")

    def test_twelve_hours_warns(self):
        checks = self.run_checks(12)
        self.assertEqual(checks["task.toml:expert-hours"], "pass")
        self.assertEqual(checks["task.toml:expert-hours-bound"], "warn")


class AuditHookProcessGapTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.task = Path(self.temp_dir.name)
        (self.task / "tests").mkdir()

    def tearDown(self):
        self.temp_dir.cleanup()

    def write_guard(self, text):
        (self.task / "tests" / "guard.py").write_text(text)

    def test_a_module_level_hook_without_fork_exec_fails_twice(self):
        self.write_guard(
            "import sys\nBLOCKED = ('subprocess.', 'os.exec')\n\n"
            "def hook(event, args):\n    if event.startswith(BLOCKED):\n        raise SystemExit(120)\n\n"
            "sys.addaudithook(hook)\n"
        )
        gaps = POLICY.audit_hook_process_gaps(self.task)
        self.assertEqual(len(gaps), 2)
        self.assertIn("fork_exec", gaps[0])
        self.assertIn("module-level", gaps[1])

    def test_a_closure_hook_that_replaces_fork_exec_passes(self):
        self.write_guard(
            "import sys\n\ndef install():\n    blocked = ('subprocess.', 'os.exec')\n\n"
            "    def hook(event, args):\n        if event.startswith(blocked):\n            raise SystemExit(120)\n\n"
            "    import _posixsubprocess\n    _posixsubprocess.fork_exec = None\n    sys.addaudithook(hook)\n\ninstall()\n"
        )
        self.assertEqual(POLICY.audit_hook_process_gaps(self.task), [])

    def test_a_native_code_hook_without_sqlite_extension_loading_fails(self):
        closure = ("import sys\n\ndef install():\n    blocked = ('subprocess.', 'os.exec', 'ctypes.'%s)\n\n"
                   "    def hook(event, args):\n        if event.startswith(blocked):\n            raise SystemExit(120)\n\n"
                   "    import _posixsubprocess\n    _posixsubprocess.fork_exec = None\n    sys.addaudithook(hook)\n\ninstall()\n")
        self.write_guard(closure % "")
        gaps = POLICY.audit_hook_process_gaps(self.task)
        self.assertEqual(len(gaps), 1)
        self.assertIn("sqlite3", gaps[0])
        self.write_guard(closure % ", 'sqlite3.enable_load_extension', 'sqlite3.load_extension'")
        self.assertEqual(POLICY.audit_hook_process_gaps(self.task), [])

    def test_a_hook_that_does_not_police_processes_is_ignored(self):
        self.write_guard("import sys\n\ndef hook(event, args):\n    pass\n\nsys.addaudithook(hook)\n")
        self.assertEqual(POLICY.audit_hook_process_gaps(self.task), [])

