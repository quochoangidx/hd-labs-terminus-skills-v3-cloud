"""Verifier for pysed: every case is run through GNU sed 4.9 and through the delivered
/app/pysed/sed.py, and the standard output (byte for byte) and exit status must agree.

The expected result of each case is produced at test time by the GNU sed 4.9 binary of
this image, run by the verifier itself; the binary is made root-only before any candidate
code runs. The candidate runs as an unprivileged user, in a fresh directory that holds
only the case's input files, with LC_ALL=C.
"""

import json
import os
import shutil
import subprocess
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(HERE, "cases.json"), encoding="utf-8") as handle:
    CASES = json.load(handle)

GNU_SED = "/bin/sed"
CANDIDATE = ["/usr/local/bin/python3", "/app/pysed/sed.py"]
DEMOTE = ["setpriv", "--reuid=65534", "--regid=65534", "--clear-groups", "--no-new-privs", "--"]
ENV = {"LC_ALL": "C", "PATH": "/usr/local/bin:/usr/bin:/bin", "HOME": "/nonexistent"}


def arguments(case):
    names = [name for name, _text in case.get("files", [])]
    return case["opts"] + ["-e", case["script"]] + case.get("extra", []) + names


def workdir(case):
    path = tempfile.mkdtemp()
    os.chmod(path, 0o755)
    for name, text in case.get("files", []):
        if text is None:
            continue  # a file named on the command line that does not exist
        with open(os.path.join(path, name), "w", encoding="latin-1") as handle:
            handle.write(text)
        os.chmod(os.path.join(path, name), 0o644)
    return path


def run(command, case, path):
    try:
        proc = subprocess.run(command + arguments(case), input=case["input"].encode("latin-1"),
                              capture_output=True, cwd=path, env=ENV, timeout=20,
                              start_new_session=True, check=False)
    except subprocess.TimeoutExpired:
        return None, "timeout"
    return proc.stdout, proc.returncode


def check(family):
    cases = [c for c in CASES if c["family"] == family]
    assert cases, f"no cases for {family}"
    failures = []
    for case in cases:
        path = workdir(case)
        try:
            want = run([GNU_SED], case, path)
            got = run(DEMOTE + CANDIDATE, case, path)
        finally:
            shutil.rmtree(path, ignore_errors=True)
        if got != want:
            failures.append((case, want, got))
    if failures:
        case, want, got = failures[0]
        detail = (f"{len(failures)} of {len(cases)} cases differ; first: sed {' '.join(case['opts'])} "
                  f"-e {case['script']!r} on {case['input'][:60]!r}: expected {want[0]!r} (status {want[1]}), "
                  f"got {got[0]!r} (status {got[1]})")
        raise AssertionError(detail)


def test_substitution_and_regex_escapes():
    check("substitution_and_regex_escapes")


def test_leftmost_longest_matching():
    check("leftmost_longest")


def test_back_references():
    check("back_references")


def test_bracket_expressions():
    check("bracket_expressions")


def test_case_conversion():
    check("case_conversion")


def test_step_and_regex_addresses():
    check("step_and_regex_addresses")


def test_plus_ranges():
    check("plus_ranges")


def test_multiple_ranges():
    check("multiple_ranges")


def test_zero_address():
    check("zero_address")


def test_append_insert_change():
    check("append_insert_change")


def test_hold_space():
    check("hold_space")


def test_multiline_commands():
    check("multiline_commands")


def test_branching_and_t_flag():
    check("branching_and_t_flag")


def test_quit_and_exit_status():
    check("quit_and_exit_status")


def test_l_command():
    check("l_command")


def test_y_z_and_line_numbers():
    check("y_z_and_line_numbers")


def test_comments_and_first_line():
    check("comments_and_first_line")


def test_several_files():
    check("several_files")


def test_mixed_scripts_1():
    check("mixed_scripts_1")


def test_mixed_scripts_2():
    check("mixed_scripts_2")


def test_mixed_scripts_3():
    check("mixed_scripts_3")


def test_mixed_scripts_4():
    check("mixed_scripts_4")
