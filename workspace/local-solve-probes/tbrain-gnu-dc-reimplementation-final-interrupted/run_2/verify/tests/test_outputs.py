"""Verifier for pydc: every case is run through GNU dc 1.4.1 and through the delivered
/app/pydc/dc.py, and their standard output must agree byte for byte.

The expected output of each case is produced at test time by the GNU dc 1.4.1 binary of
this image, run by the verifier itself; the binary is made root-only before any candidate
code runs. Each program runs in its own fresh directory holding the case's files, with
LC_ALL=C and DC_LINE_LENGTH unset, and reads the case's standard input from a pipe.
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

GNU_DC = "/usr/bin/dc"
CANDIDATE = ["/usr/local/bin/python3", "/app/pydc/dc.py"]
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
        want = run([GNU_DC], case)
        got = run(DEMOTE + CANDIDATE, case)
        if got != want:
            failures.append((case, want, got))
    if failures:
        case, want, got = failures[0]
        detail = (f"{len(failures)} of {len(cases)} cases differ; first: dc {case['args']!r} with files "
                  f"{[n for n, _t in case['files']]} and stdin {case['stdin'][:80]!r}: expected {want!r}, got {got!r}")
        raise AssertionError(detail)




def test_printing():
    check("printing")


def test_arithmetic():
    check("arithmetic")


def test_stack_control():
    check("stack_control")


def test_registers():
    check("registers")


def test_arrays():
    check("arrays")


def test_parameters():
    check("parameters")


def test_strings_and_macros():
    check("strings")


def test_status_inquiry():
    check("status_inquiry")


def test_misc_and_comments():
    check("misc_and_comments")


def test_errors_and_recovery():
    check("errors_and_recovery")


def test_options_and_files():
    check("options_and_files")


def test_mixed_scripts_1():
    check("mixed_1")


def test_mixed_scripts_2():
    check("mixed_2")


def test_mixed_scripts_3():
    check("mixed_3")


def test_mixed_scripts_4():
    check("mixed_4")


def test_random_scripts_1():
    check("random_1")


def test_random_scripts_2():
    check("random_2")


def test_random_scripts_3():
    check("random_3")


def test_random_scripts_4():
    check("random_4")


def test_random_scripts_5():
    check("random_5")


def test_random_scripts_6():
    check("random_6")


def test_random_scripts_7():
    check("random_7")


def test_random_scripts_8():
    check("random_8")
