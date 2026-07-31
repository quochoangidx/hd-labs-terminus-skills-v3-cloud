#!/usr/bin/env bash
# new-task.sh — stamp a new Terminus Regular task skeleton with the packaging /
# verifier hygiene from AGENTS.md §8/§10 baked in, so none of it is re-derived
# by hand per task.
#
# Usage: scripts/new-task.sh <slug> <lang> <category>
#   slug      tbrain-<problem-slug>   (domain-named, no tool/repo filler)
#   lang      rust | go | c | cpp | python | ruby | node | java | generic
#   category  one of the nine open Regular-task categories
#
# Output: workspace/<slug>/ with task.toml, instruction.md, environment/,
# solution/, tests/ pre-filled. Every TODO marker must be resolved before the
# skeleton probe. Refuses to overwrite an existing folder.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SLUG="${1:?usage: new-task.sh <slug> <lang> <category>}"
LANG_ID="${2:?usage: new-task.sh <slug> <lang> <category>}"
CATEGORY="${3:?usage: new-task.sh <slug> <lang> <category>}"

if ! POLICY_RESULT="$(python3 "$REPO_ROOT/scripts/task-policy.py" category "$CATEGORY" 2>&1)"; then
  echo "$POLICY_RESULT" >&2
  exit 1
fi

# Canonical digest-pinned bases (extracted from platform-passed zips).
# node/temurin digests were not recoverable from the repo: resolve the
# MANIFEST-LIST digest (docker buildx imagetools inspect <image>) before build.
BASE_RUST="public.ecr.aws/docker/library/rust:1.85-slim@sha256:9f841bbe9e7d8e37ceb96ed907265a3a0df7f44e3737d0b100e7907a679acb36"
BASE_GO="public.ecr.aws/docker/library/golang:1.24-bookworm@sha256:1a6d4452c65dea36aac2e2d606b01b4a029ec90cc1ae53890540ce6173ea77ac"
BASE_GCC="public.ecr.aws/docker/library/gcc:13-bookworm@sha256:930f2ebe239275fa67226654cb79273ea34eee672ae61c8a39f689c37fb7ac5c"
BASE_PY="public.ecr.aws/docker/library/python:3.13-slim-bookworm@sha256:01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb"
BASE_RUBY="public.ecr.aws/docker/library/ruby:3.3-slim-bookworm@sha256:e76733e94b3a5893e4a141024ef3a583dc10781dc24becebf74f9c9f9a33e3df"
BASE_DEBIAN="public.ecr.aws/docker/library/debian:bookworm-slim@sha256:4724b8cc51e33e398f0e2e15e18d5ec2851ff0c2280647e1310bc1642182655d"
BASE_NODE="public.ecr.aws/docker/library/node:22-bookworm-slim@sha256:TODO_RESOLVE_MANIFEST_LIST_DIGEST"
BASE_JAVA="public.ecr.aws/docker/library/eclipse-temurin:21-jdk-jammy@sha256:TODO_RESOLVE_MANIFEST_LIST_DIGEST"

APT_COMMON="tmux asciinema patch ca-certificates"
LANG_TOML="\"$LANG_ID\""
EXTRA_RUN=""
case "$LANG_ID" in
  rust)   BASE="$BASE_RUST" ;;
  go)     BASE="$BASE_GO"
          EXTRA_RUN='ENV GOTOOLCHAIN=auto
RUN ln -sf /usr/local/go/bin/go /usr/local/bin/go && git config --system safe.directory /app' ;;
  c)      BASE="$BASE_GCC"; APT_COMMON="tmux asciinema" ;;   # gcc image ships build tools + patch
  cpp)    BASE="$BASE_GCC"; APT_COMMON="tmux asciinema"; LANG_TOML='"c++"' ;;
  python) BASE="$BASE_PY"
          echo "NOTE: Python tasks must realistically target difficulty=hard (0/3 semantic)." >&2 ;;
  ruby)   BASE="$BASE_RUBY" ;;
  node)   BASE="$BASE_NODE" ;;
  java)   BASE="$BASE_JAVA"
          EXTRA_RUN='RUN git config --system safe.directory /app' ;;
  generic) BASE="$BASE_DEBIAN"; LANG_TOML='"bash"' ;;
  *) echo "REJECT: unknown lang '$LANG_ID'." >&2; exit 1 ;;
esac

TASK_DIR="$REPO_ROOT/workspace/$SLUG"
[ -e "$TASK_DIR" ] && { echo "REJECT: $TASK_DIR already exists." >&2; exit 1; }
mkdir -p "$TASK_DIR"/{environment/app,solution,tests}

cat > "$TASK_DIR/task.toml" <<EOF
version = "2.0"

[metadata]
author_name = "anonymous"
author_email = "anonymous"
difficulty = "hard"
category = "$CATEGORY"
subcategories = []
number_of_milestones = 0
codebase_size = "minimal"
languages = [$LANG_TOML]
tags = ["TODO", "TODO", "TODO"]
expert_time_estimate_min = 90
junior_time_estimate_min = 240

[verifier]
timeout_sec = 600.0

[agent]
timeout_sec = 1800.0

[environment]
allow_internet = false
build_timeout_sec = 1800.0
cpus = 2
memory_mb = 4096
storage_mb = 10240
EOF

cat > "$TASK_DIR/instruction.md" <<'EOF'
TODO: <=3 short paragraphs, narrative prose. State the OUTCOME and the
observable contract (exact output keys/constants are fair); never the
mechanism, the tests, or architecture nudges. Absolute /app/... file refs.
Run the category_rules.md screen on this text before the skeleton probe.
EOF

cat > "$TASK_DIR/environment/Dockerfile" <<EOF
FROM $BASE

RUN apt-get update && apt-get install -y --no-install-recommends $APT_COMMON && rm -rf /var/lib/apt/lists/*
$EXTRA_RUN

WORKDIR /app
COPY app/ /app/
EOF
# Hygiene reminders (enforced by preflight.sh): no '# syntax=' line, no
# --mount=type=bind, one merged dep-install RUN, no warm build of the target.

cat > "$TASK_DIR/environment/.dockerignore" <<'EOF'
.git
**/.git
.gitignore
.pytest_cache
.mypy_cache
.ruff_cache
node_modules
__pycache__
*.pyc
.DS_Store
solution/
tests/
.env
EOF

cat > "$TASK_DIR/environment/app/README.md" <<EOF
# $SLUG

TODO: 2-4 sentences of realistic project framing (repo furniture, not task
instructions). Vary wording per task — identical furniture across tasks feeds
template_detection.
EOF

cat > "$TASK_DIR/solution/solve.sh" <<'EOF'
#!/bin/bash
# Oracle entry point. Platform rule: realistic engineer commands only —
# never `patch -p1 < fix.patch` as the visible action for milestone-0 tasks
# where reviewers flagged it; copy/edit source then rebuild.
set -euo pipefail
cd /app
# TODO: apply the reference solution (copy sources from /solution, rebuild).
EOF
chmod +x "$TASK_DIR/solution/solve.sh"

install -m 0755 "$REPO_ROOT/scripts/templates/test.sh" "$TASK_DIR/tests/test.sh"

cat > "$TASK_DIR/tests/test_outputs.py" <<'EOF'
"""Behavioral verifier skeleton. The hygiene helpers below are load-bearing:
keep them wired even after replacing the TODO test bodies."""
import json
import os
import shutil
import subprocess
import tempfile

import pytest

APP_DIR = "/app"
CORPUS = "/tests/corpus.jsonl"


def _find_exec_base():
    """First exec-capable dir for temp build/exec artifacts — bare /tmp is
    noexec on the platform."""
    for base in (APP_DIR, "/var/tmp", "/dev/shm", tempfile.gettempdir()):
        try:
            d = tempfile.mkdtemp(dir=base)
        except OSError:
            continue
        probe = os.path.join(d, "probe.sh")
        with open(probe, "w") as f:
            f.write("#!/bin/sh\nexit 0\n")
        os.chmod(probe, 0o755)
        try:
            if subprocess.run([probe], check=False).returncode == 0:
                return base
        except OSError:
            pass
        finally:
            shutil.rmtree(d, ignore_errors=True)
    return tempfile.gettempdir()


EXEC_TMP_BASE = _find_exec_base()


def _candidate_user_kwargs():
    """Run the candidate unprivileged so it cannot read verifier-owned data."""
    if os.geteuid() == 0:
        return {"user": "nobody", "group": "nogroup"}
    return {}


def _hide_corpus():
    """Unlink the expected-value corpus before any candidate code runs; the
    values live in memory already. Silently no-ops off-platform."""
    if os.path.dirname(CORPUS) == "/tests" and os.path.exists(CORPUS):
        try:
            os.unlink(CORPUS)
            os.chmod("/tests", 0o700)
        except OSError:
            pass


def _load_corpus():
    with open(CORPUS) as f:
        cases = [json.loads(line) for line in f if line.strip()]
    _hide_corpus()
    return cases


CASES = _load_corpus() if os.path.exists(CORPUS) else []


@pytest.fixture(scope="session")
def built_binary():
    """Build the candidate FROM /app SOURCE at verify time; assert the build's
    EXIT STATUS (a stale warm binary must never be graded)."""
    build_dir = tempfile.mkdtemp(dir=EXEC_TMP_BASE)
    # TODO: build command, e.g.:
    # r = subprocess.run(["go", "build", "-o", out, "./cmd/..."], cwd=APP_DIR,
    #                    capture_output=True, text=True, check=False,
    #                    env={**os.environ, "GOCACHE": build_dir, "HOME": build_dir})
    # assert r.returncode == 0, f"build failed:\n{r.stdout}\n{r.stderr}"
    # os.chmod / chmod -R a+rX so the demoted candidate user can exec it.
    raise NotImplementedError("TODO: implement build")


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.get("id", "case"))
def test_case(built_binary, case):
    """Per-case parametrized (never one monolithic all-N test — a single
    correlated blind spot would turn the whole suite 0/N)."""
    r = subprocess.run(
        [built_binary],
        input=json.dumps(case["input"]),
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
        **_candidate_user_kwargs(),
    )
    assert r.returncode == 0, r.stderr
    assert json.loads(r.stdout) == case["expected"]
EOF

echo "Created $TASK_DIR"
echo "Next: fill TODOs -> collapse-law screen -> skeleton probe (task-local-solve-probe) -> build -> scripts/preflight.sh"
case "$LANG_ID" in
  rust|go|c|cpp) echo "WARNING: template_detection flags minimal single-source stdin->stdout CLI shapes (rust_cli + siblings). Build a multi-module layout, file-based I/O surface, and varied repo furniture — the stamped skeleton is NOT enough by itself." >&2 ;;
esac
case "$BASE" in *TODO_RESOLVE*) echo "WARNING: base image digest is a placeholder — resolve the manifest-list digest before building." >&2 ;; esac
