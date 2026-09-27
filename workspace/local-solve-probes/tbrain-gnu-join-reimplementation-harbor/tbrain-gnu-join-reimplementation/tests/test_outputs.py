"""Verifier for pyjoin: every case is run through GNU join (coreutils 9.1) and through the delivered
/app/pyjoin/join.py; the standard output (byte for byte) and the exit status must agree.

The expected result of each case is produced at test time by the GNU join binary of
this image, run by the verifier itself; the binary is made root-only before any candidate
code runs. Each program runs in its own fresh directory holding the case's files, with
LC_ALL=C, and reads the case's standard input from a pipe.
"""

import json
import os
import shutil
import signal
import subprocess
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(HERE, "cases.json"), encoding="utf-8") as handle:
    CASES = json.load(handle)

GNU_JOIN = "/usr/bin/join"
CANDIDATE = ["/usr/local/bin/python3", "/app/pyjoin/join.py"]
DEMOTE = ["setpriv", "--reuid=65534", "--regid=65534", "--clear-groups", "--no-new-privs", "--"]
ENV = {"LC_ALL": "C", "PATH": "/usr/local/bin:/usr/bin:/bin", "HOME": "/nonexistent"}


def run(command, case):
    path = tempfile.mkdtemp()
    os.chmod(path, 0o755)
    try:
        for name, text in case["files"]:
            with open(os.path.join(path, name), "w", encoding="latin-1") as handle:
                handle.write(text)
            os.chmod(os.path.join(path, name), 0o644)
        proc = subprocess.Popen(command + case["args"], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                stderr=subprocess.DEVNULL, cwd=path, env=ENV, start_new_session=True)
        try:
            out, _err = proc.communicate(case["stdin"].encode("latin-1"), timeout=20)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)
            proc.communicate()
            return None, "timeout"
        return out, proc.returncode
    finally:
        shutil.rmtree(path, ignore_errors=True)


def check(family):
    cases = [c for c in CASES if c["family"] == family]
    assert cases, f"no cases for {family}"
    failures = []
    for case in cases:
        want = run([GNU_JOIN], case)
        got = run(DEMOTE + CANDIDATE, case)
        if got != want:
            failures.append((case, want, got))
    if failures:
        case, want, got = failures[0]
        detail = (f"{len(failures)} of {len(cases)} cases differ; first: join {case['args']!r} with files "
                  f"{[n for n, _t in case['files']]} on stdin {case['stdin'][:60]!r}: expected {want[0]!r} "
                  f"(status {want[1]}), got {got[0]!r} (status {got[1]})")
        raise AssertionError(detail)


def test_random_1():
    check("random_1")


def test_random_2():
    check("random_2")


def test_random_3():
    check("random_3")


def test_random_4():
    check("random_4")


def test_random_5():
    check("random_5")


def test_random_6():
    check("random_6")


def test_random_7():
    check("random_7")


def test_random_8():
    check("random_8")

