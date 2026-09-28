"""Verifier for pygrep: every case is run through GNU grep 3.8 and through the delivered
/app/pygrep/grep.py; the standard output (byte for byte) and the exit status must agree.

The expected result of each case is produced at test time by the GNU grep 3.8 binary of
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

GNU_GREP = "/bin/grep"
CANDIDATE = ["/usr/local/bin/python3", "/app/pygrep/grep.py"]
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
        want = run([GNU_GREP], case)
        got = run(DEMOTE + CANDIDATE, case)
        if got != want:
            failures.append((case, want, got))
    if failures:
        case, want, got = failures[0]
        detail = (f"{len(failures)} of {len(cases)} cases differ; first: grep {case['args']!r} with files "
                  f"{[n for n, _t in case['files']]} on stdin {case['stdin'][:60]!r}: expected {want[0]!r} "
                  f"(status {want[1]}), got {got[0]!r} (status {got[1]})")
        raise AssertionError(detail)


def test_binary_input():
    check("binary_input")


def test_context():
    check("context")


def test_files_and_status():
    check("files_and_status")


def test_mixed_1():
    check("mixed_1")


def test_mixed_2():
    check("mixed_2")


def test_mixed_3():
    check("mixed_3")


def test_mixed_4():
    check("mixed_4")


def test_mixed_5():
    check("mixed_5")


def test_mixed_6():
    check("mixed_6")


def test_mixed_7():
    check("mixed_7")


def test_mixed_8():
    check("mixed_8")


def test_null_data():
    check("null_data")


def test_only_matching():
    check("only_matching")


def test_output_controls():
    check("output_controls")


def test_patterns():
    check("patterns")

