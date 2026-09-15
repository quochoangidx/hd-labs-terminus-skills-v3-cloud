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

    def test_agent_image_requires_harness_tools(self):
        self.dockerfile.write_text(f"FROM {PYTHON_IMAGE}\n")

        checks = POLICY.validate_dockerfile(self.dockerfile, "agent")

        self.assertEqual(statuses(checks)["agent-dockerfile:harness-tools"], "fail")

    def test_cloud_builder_rejects_named_copy_chown(self):
        self.dockerfile.write_text(
            f"FROM {PYTHON_IMAGE}\n"
            "COPY --chown=root:root app/ /app/\n"
            "RUN apt-get update && apt-get install -y tmux asciinema\n"
        )

        checks = POLICY.validate_dockerfile(self.dockerfile, "agent")

        self.assertEqual(statuses(checks)["agent-dockerfile:modal-syntax"], "fail")

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

    def test_task_scan_checks_nested_dockerfiles(self):
        task_dir = Path(self.temp_dir.name) / "tbrain-nested-dockerfile"
        nested = task_dir / "environment" / "repo" / "tools"
        nested.mkdir(parents=True)
        (nested / "Dockerfile").write_text(
            "FROM scratch\nCOPY --chown=appuser:appuser . /app\n"
        )

        checks = POLICY.validate_task(task_dir)

        self.assertEqual(statuses(checks)["dockerfiles:modal-syntax"], "fail")


if __name__ == "__main__":
    unittest.main()
