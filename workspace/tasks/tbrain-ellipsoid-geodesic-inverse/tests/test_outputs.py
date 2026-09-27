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
    #                    env={**os.environ, "GOCACHE": build_dir, "HOME": build_dir},
    #                    **_candidate_user_kwargs())
    # assert r.returncode == 0, f"build failed:\n{r.stdout}\n{r.stderr}"
    # Stage source/output/cache in a candidate-owned scratch tree first; never
    # let the demoted build write /app, /tests, or /logs/verifier.
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
