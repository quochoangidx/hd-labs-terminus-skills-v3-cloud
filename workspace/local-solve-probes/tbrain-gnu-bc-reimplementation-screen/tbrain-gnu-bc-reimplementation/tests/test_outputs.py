"""Verifier for pybc: every case is run through GNU bc 1.07.1 and through the delivered
/app/pybc/bc.py, and their standard output must agree byte for byte.

The expected output of each case is produced at test time by the GNU bc 1.07.1 binary of
this image, run by the verifier itself; that binary and the dc of the same package are made
root-only before any candidate code runs. Each program runs in its own fresh directory
holding the case's files, with LC_ALL=C and BC_LINE_LENGTH, BC_ENV_ARGS and
POSIXLY_CORRECT unset, and reads the case's standard input from a pipe.
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

GNU_BC = "/usr/bin/bc"
CANDIDATE = ["/usr/local/bin/python3", "/app/pybc/bc.py"]
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
            return "timeout"
        return out
    finally:
        shutil.rmtree(path, ignore_errors=True)


def check(family):
    cases = [c for c in CASES if c["family"] == family]
    assert cases, f"no cases for {family}"
    failures = []
    for case in cases:
        want = run([GNU_BC], case)
        got = run(DEMOTE + CANDIDATE, case)
        if got != want:
            failures.append((case, want, got))
    if failures:
        case, want, got = failures[0]
        detail = (f"{len(failures)} of {len(cases)} cases differ; first: bc {case['args']!r} with files "
                  f"{[n for n, _t in case['files']]} and stdin {case['stdin'][:200]!r}: expected {want!r}, got {got!r}")
        raise AssertionError(detail)


def test_numbers_and_bases():
    check("numbers_and_bases")


def test_arithmetic_and_scale():
    check("arithmetic_and_scale")


def test_builtin_functions():
    check("builtin_functions")


def test_printing_and_radixes():
    check("printing_and_radixes")


def test_strings_and_print():
    check("strings_and_print")


def test_relational_and_boolean():
    check("relational_and_boolean")


def test_assignment_and_variables():
    check("assignment_and_variables")


def test_control_flow():
    check("control_flow")


def test_user_functions():
    check("user_functions")


def test_runtime_errors():
    check("runtime_errors")


def test_mixed_programs_1():
    check("mixed_1")


def test_mixed_programs_2():
    check("mixed_2")


def test_mixed_programs_3():
    check("mixed_3")


def test_mixed_programs_4():
    check("mixed_4")


def test_mixed_programs_5():
    check("mixed_5")


def test_mixed_programs_6():
    check("mixed_6")


def test_mixed_programs_7():
    check("mixed_7")


def test_mixed_programs_8():
    check("mixed_8")
