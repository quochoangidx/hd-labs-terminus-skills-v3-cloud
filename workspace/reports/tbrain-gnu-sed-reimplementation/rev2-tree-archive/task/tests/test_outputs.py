"""Verifier for pysed: every case is run through GNU sed 4.9 and through the delivered
/app/pysed/sed.py, and the standard output (byte for byte) and exit status must agree.

The expected result of each case is produced at test time by the GNU sed 4.9 binary of
this image, run by the verifier itself; the binary is made root-only before any candidate
code runs. The candidate runs as an unprivileged user, in a fresh directory that holds
only the case's input files, with LC_ALL=C, under an audit hook that stops it the moment
it starts another program or loads native code through ctypes (the instruction says the
editing is done in Python itself).
"""

import json
import os
import shutil
import signal
import subprocess
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
CASE_FILES = ("areas.json", "areas_2.json", "mixed_1_2.json", "mixed_3_4.json")
# The graded roster: every family and its case count. Loading fails unless the case files
# hold exactly these families with exactly these counts.
FAMILY_COUNTS = {
    "substitution_and_regex_escapes": 125, "bracket_expressions": 48, "back_references": 12,
    "case_conversion": 19, "leftmost_longest": 14, "step_and_regex_addresses": 59,
    "plus_ranges": 3, "multiple_ranges": 11, "zero_address": 3, "y_z_and_line_numbers": 51,
    "append_insert_change": 71, "multiline_commands": 47, "l_command": 23, "hold_space": 8,
    "quit_and_exit_status": 7, "branching_and_t_flag": 23, "comments_and_first_line": 19,
    "several_files": 16, "options_and_script_argument": 7, "empty_input": 6,
    "mixed_scripts_1": 147, "mixed_scripts_2": 161, "mixed_scripts_3": 160, "mixed_scripts_4": 148,
}


def load_cases():
    """Case files map a family to its cases, one per line. An input or file text written as
    "@name" is the text stored under that name in inputs.json."""
    with open(os.path.join(HERE, "cases", "inputs.json"), encoding="utf-8") as handle:
        inputs = json.load(handle)

    def text(value):
        return inputs[value[1:]] if isinstance(value, str) and value.startswith("@") else value

    cases = []
    for name in CASE_FILES:
        with open(os.path.join(HERE, "cases", name), encoding="utf-8") as handle:
            for family, rows in json.load(handle).items():
                for row in rows:
                    case = dict(row, family=family, input=text(row["input"]))
                    if "files" in row:
                        case["files"] = [[fname, text(ftext)] for fname, ftext in row["files"]]
                    cases.append(case)
    counts = {}
    for case in cases:
        counts[case["family"]] = counts.get(case["family"], 0) + 1
    assert counts == FAMILY_COUNTS, f"case roster differs from FAMILY_COUNTS: {counts}"
    return cases


CASES = load_cases()

GNU_SED = "/bin/sed"
# Runs /app/pysed/sed.py as `python3 /app/pysed/sed.py ARGS` would (same argv, __main__,
# script directory on sys.path), after installing an audit hook that ends the process with
# status 97 on any attempt to start a program or to open a native library via ctypes.
GUARD_STATUS = 97
GUARD = f"""
import os, runpy, sys
BLOCKED = {{"os.exec", "os.posix_spawn", "os.spawn", "os.system", "os.fork", "os.forkpty",
           "subprocess.Popen", "ctypes.dlopen"}}
def hook(event, args):
    if event in BLOCKED:
        os.write(2, ("pysed guard: blocked " + event + "\\n").encode())
        os._exit({GUARD_STATUS})
sys.addaudithook(hook)
sys.argv = sys.argv[1:]
sys.path[0] = os.path.dirname(sys.argv[0])
runpy.run_path(sys.argv[0], run_name="__main__")
"""
CANDIDATE = ["/usr/local/bin/python3", "-c", GUARD, "/app/pysed/sed.py"]
DEMOTE = ["setpriv", "--reuid=65534", "--regid=65534", "--clear-groups", "--no-new-privs", "--"]
TIMEOUT = 5  # seconds per run, as the instruction allows
ENV = {"LC_ALL": "C", "PATH": "/usr/local/bin:/usr/bin:/bin", "HOME": "/nonexistent"}


def arguments(case):
    names = [name for name, _text in case.get("files", [])]
    script = [case["script"]] if case.get("script_arg") else ["-e", case["script"]]
    return case["opts"] + script + case.get("extra", []) + names


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
    proc = subprocess.Popen(command + arguments(case), stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                            stderr=subprocess.DEVNULL, cwd=path, env=ENV, start_new_session=True)
    try:
        out, _err = proc.communicate(case["input"].encode("latin-1"), timeout=TIMEOUT)
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGKILL)
        proc.communicate()
        return None, "timeout"
    return out, proc.returncode


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
        files = [name for name, _text in case.get("files", [])]
        detail = (f"{len(failures)} of {len(cases)} cases differ; first: sed {arguments(case)!r} "
                  f"with files {files} on stdin {case['input'][:60]!r}: expected {want[0]!r} "
                  f"(status {want[1]}), got {got[0]!r} (status {got[1]})")
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


def test_options_and_script_argument():
    check("options_and_script_argument")


def test_empty_input():
    check("empty_input")


def test_mixed_scripts_1():
    check("mixed_scripts_1")


def test_mixed_scripts_2():
    check("mixed_scripts_2")


def test_mixed_scripts_3():
    check("mixed_scripts_3")


def test_mixed_scripts_4():
    check("mixed_scripts_4")


def test_editing_is_done_in_python():
    """The instruction forbids handing the work to another program or to native code: no
    executable or shared library may be shipped under /app, and a few ordinary runs must not
    trip the guard (which a wrapper around a bundled sed, or ctypes calls into libc, would)."""
    shipped = []
    for root, _dirs, names in os.walk("/app"):
        for name in names:
            with open(os.path.join(root, name), "rb") as handle:
                if handle.read(4) == b"\x7fELF":
                    shipped.append(os.path.join(root, name))
    assert not shipped, f"native executables or libraries under /app: {shipped}"
    for script, opts in (("s/a/b/", []), ("/x/,/y/{s/\\(.\\)\\1/[&]/g;p}", []), ("s/(a|ab)(c|bcd)*/X/", ["-E"])):
        case = {"opts": opts, "script": script, "input": "aa\nabcd\nx\nyy\n"}
        path = workdir(case)
        try:
            _out, status = run(DEMOTE + CANDIDATE, case, path)
        finally:
            shutil.rmtree(path, ignore_errors=True)
        assert status != GUARD_STATUS, f"sed {arguments(case)!r} tried to start a process or load native code"
