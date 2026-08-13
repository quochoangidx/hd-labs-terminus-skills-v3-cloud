#!/usr/bin/env bash
# new-task.sh — stamp a new Terminus Regular task skeleton with the packaging /
# verifier hygiene from AGENTS.md §8/§10 baked in, so none of it is re-derived
# by hand per task.
#
# Usage: scripts/new-task.sh <slug> <lang> <category> <subcategory>
#   slug      tbrain-<problem-slug>   (domain-named, no tool/repo filler)
#   lang      rust | go | c | cpp | python | ruby | node | java | generic
#   category/subcategory  one exact Terminus 3 taxonomy pair
#
# Output: workspace/tasks/<slug>/ with task.toml, instruction.md, environment/,
# solution/, tests/ pre-filled. Every TODO marker must be resolved before the
# skeleton probe. Refuses to overwrite an existing folder.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SLUG="${1:?usage: new-task.sh <slug> <lang> <category> <subcategory>}"
LANG_ID="${2:?usage: new-task.sh <slug> <lang> <category> <subcategory>}"
CATEGORY="${3:?usage: new-task.sh <slug> <lang> <category> <subcategory>}"
SUBCATEGORY="${4:?usage: new-task.sh <slug> <lang> <category> <subcategory>}"

if ! POLICY_RESULT="$(python3 "$REPO_ROOT/scripts/task-policy.py" category "$CATEGORY" "$SUBCATEGORY" 2>&1)"; then
  echo "$POLICY_RESULT" >&2
  exit 1
fi

# Canonical digest-pinned bases from the current Terminus 3 Dockerfile guide.
BASE_RUST="public.ecr.aws/docker/library/rust:1.85-slim@sha256:9f841bbe9e7d8e37ceb96ed907265a3a0df7f44e3737d0b100e7907a679acb36"
BASE_GO="public.ecr.aws/docker/library/golang:1.24-bookworm@sha256:1a6d4452c65dea36aac2e2d606b01b4a029ec90cc1ae53890540ce6173ea77ac"
BASE_GCC="public.ecr.aws/docker/library/gcc:13-bookworm@sha256:930f2ebe239275fa67226654cb79273ea34eee672ae61c8a39f689c37fb7ac5c"
BASE_PY="public.ecr.aws/docker/library/python:3.13-slim-bookworm@sha256:01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb"
BASE_RUBY="public.ecr.aws/docker/library/ruby:3.3-slim-bookworm@sha256:e76733e94b3a5893e4a141024ef3a583dc10781dc24becebf74f9c9f9a33e3df"
BASE_DEBIAN="public.ecr.aws/docker/library/debian:bookworm-slim@sha256:4724b8cc51e33e398f0e2e15e18d5ec2851ff0c2280647e1310bc1642182655d"
BASE_NODE="public.ecr.aws/docker/library/node:22-bookworm-slim@sha256:f3a68cf41a855d227d1b0ab832bed9749469ef38cf4f58182fb8c893bc462383"
BASE_JAVA="public.ecr.aws/docker/library/eclipse-temurin:21-jdk-jammy@sha256:25d1276565738d3c805e632a4542c3a7598866ef967f4def6544c15de3a74b14"

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
  python) BASE="$BASE_PY" ;;
  ruby)   BASE="$BASE_RUBY" ;;
  node)   BASE="$BASE_NODE" ;;
  java)   BASE="$BASE_JAVA"; APT_COMMON="$APT_COMMON git"
          EXTRA_RUN='RUN git config --system safe.directory /app' ;;
  generic) BASE="$BASE_DEBIAN"; LANG_TOML='"bash"' ;;
  *) echo "REJECT: unknown lang '$LANG_ID'." >&2; exit 1 ;;
esac

TASK_DIR="$REPO_ROOT/workspace/tasks/$SLUG"
[ -e "$TASK_DIR" ] && { echo "REJECT: $TASK_DIR already exists." >&2; exit 1; }
mkdir -p "$TASK_DIR"/{environment/app,solution,tests}

cat > "$TASK_DIR/task.toml" <<EOF
artifacts = ["/app/"]
name = "$SLUG"

[metadata]
author_name = "anonymous"
author_email = "anonymous"
difficulty = "core"
category = "$CATEGORY"
subcategory = "$SUBCATEGORY"
languages = [$LANG_TOML]
tags = ["TODO", "TODO", "TODO"]
expert_time_estimate_hours = 4
difficulty_explanation = "TODO: summarize the empirically measured difficulty crux."
solution_explanation = "TODO: summarize how the oracle solves the task."
verification_explanation = "TODO: summarize how the isolated verifier evaluates the artifacts."
relevant_experience = "TODO: summarize the relevant authoring experience."

[verifier]
timeout_sec = 1800
environment_mode = "separate"

[agent]
timeout_sec = 5400

[environment]
network_mode = "public"
build_timeout_sec = 900
cpus = 2
memory_mb = 8192
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

cat > "$TASK_DIR/tests/Dockerfile" <<EOF
FROM $BASE_PY

RUN pip install --no-cache-dir pytest==9.1.1 pytest-json-ctrf==0.5.2
RUN mkdir -p /app /logs/verifier
COPY . /tests/
WORKDIR /tests
EOF

cat > "$TASK_DIR/tests/test_outputs.py" <<'EOF'
"""Behavioral verifier skeleton. The hygiene helpers below are load-bearing:
keep them wired even after replacing the TODO test bodies."""
import json
import os
import signal
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


def _kill_process_group(proc):
    """Kill and reap the candidate plus every descendant it left behind."""
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    proc.wait()


def _run_candidate(argv, *, input_text=None, cwd=None, timeout=30):
    """Run untrusted candidate code in its own disposable process group."""
    proc = subprocess.Popen(
        argv,
        cwd=cwd,
        stdin=subprocess.PIPE if input_text is not None else None,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
        **_candidate_user_kwargs(),
    )
    try:
        stdout, stderr = proc.communicate(input=input_text, timeout=timeout)
    except subprocess.TimeoutExpired:
        _kill_process_group(proc)
        raise
    finally:
        # communicate() can return after the direct child exits while a detached
        # descendant remains alive. The group still belongs to this one run.
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        proc.wait()
    return subprocess.CompletedProcess(argv, proc.returncode, stdout, stderr)


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
    r = _run_candidate(
        [built_binary],
        input_text=json.dumps(case["input"]),
        timeout=30,
    )
    assert r.returncode == 0, r.stderr
    assert json.loads(r.stdout) == case["expected"]
EOF

echo "Created $TASK_DIR"
echo "Next: fill TODOs -> collapse-law screen -> skeleton probe (task-local-solve-probe) -> build -> scripts/preflight.sh"
case "$LANG_ID" in
  rust|go|c|cpp) echo "WARNING: template_detection flags minimal single-source stdin->stdout CLI shapes (rust_cli + siblings). Build a multi-module layout, file-based I/O surface, and varied repo furniture — the stamped skeleton is NOT enough by itself." >&2 ;;
esac
