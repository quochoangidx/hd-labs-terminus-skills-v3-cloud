"""Verifier for pysed: every case is run through GNU sed 4.9 and through the delivered
/app/pysed/sed.py, and the standard output (byte for byte) and exit status must agree.

The expected result of each case is produced at test time by the GNU sed 4.9 binary of
this image, run by the verifier itself; the binary is made root-only before any candidate
code runs. The candidate runs as an unprivileged user that cannot write under /app, in a
fresh directory that holds only the case's input files, with LC_ALL=C, under an audit hook
that stops it the moment it starts another program or loads native code through ctypes or an
extension module (the instruction says the editing is done in Python itself).
"""

import json
import os
import shutil
import signal
import subprocess
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
CASE_FILES = ("areas.json", "areas_2.json", "mixed_1_2.json", "mixed_3_4.json", "matrix.json", "sweeps.json")
# The graded roster: every family and its case count. Loading fails unless the case files
# hold exactly these families with exactly these counts.
FAMILY_COUNTS = {
    "substitution_and_regex_escapes": 108, "bracket_expressions": 45, "leftmost_longest": 14,
    "step_and_regex_addresses": 58, "plus_ranges": 3, "multiple_ranges": 11, "zero_address": 2,
    "z_and_line_numbers": 6, "append_insert_change": 50, "multiline_commands": 22, "hold_space": 8,
    "quit_and_exit_status": 7, "branching_and_t_flag": 23, "comments_and_first_line": 19,
    "several_files": 16, "options_and_script_argument": 7, "empty_input": 6,
    "mixed_scripts_1": 80, "mixed_scripts_2": 74, "mixed_scripts_3": 75, "mixed_scripts_4": 70,
}
# matrix.json walks the instruction clause by clause: every escape in every position, every
# order of the s flags, every group number, q/Q codes, ranges on blocks, - among files, ...
MATRIX_COUNTS = {
    "matrix_escapes": 112, "matrix_regex_escapes": 84, "matrix_s_flags": 59,
    "matrix_groups": 29, "matrix_intervals": 24, "matrix_quit": 61, "matrix_t_flag": 19,
    "matrix_blocks": 29, "matrix_files": 26, "matrix_append": 16, "matrix_long_input": 10,
    "matrix_anchors": 11, "matrix_ranges": 19, "matrix_delimiters": 25, "matrix_brackets": 38,
}
FAMILY_COUNTS.update(MATRIX_COUNTS)
# sweeps.json takes whole classes rather than one example each: lines of any length, every
# number with more than one digit, every character class over all of ASCII, every character as a
# delimiter, // after skipped commands, and bracket expressions that start or end with - or ].
SWEEP_COUNTS = {
    "sweep_long_lines": 14, "sweep_numbers": 41, "sweep_classes": 42, "sweep_delimiters": 201,
    "sweep_empty_regex": 10, "sweep_bracket_edges": 32,
}
FAMILY_COUNTS.update(SWEEP_COUNTS)


def load_cases():
    """Case files map a family to its cases, one per line. An input or file text written as
    "@name" is the text stored under that name in inputs.json. A file whose text is null is
    named on the command line but not created: a missing file, or "-" for standard input."""
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
# script directory on sys.path) but without site-packages (test.sh also makes it root-only, so it
# cannot be put back on sys.path), after installing an audit hook
# that ends the process with status 97 on any attempt to start a program, to open a native
# library via ctypes, or to load an extension module from anywhere but Python's lib-dynload.
GUARD_STATUS = 97
GUARD = f"""
import os, runpy, sys
BLOCKED = {{"os.exec", "os.posix_spawn", "os.spawn", "os.system", "os.fork", "os.forkpty",
           "subprocess.Popen", "ctypes.dlopen"}}
# an extension module is native code too; only Python's own lib-dynload ones may load
DYNLOAD = os.path.join(sys.base_prefix, "lib", "python%d.%d" % sys.version_info[:2], "lib-dynload") + os.sep
def hook(event, args):
    if event == "import" and len(args) > 1 and args[1] and not os.path.realpath(args[1]).startswith(DYNLOAD) \\
            and not args[1].endswith((".py", ".pyc")):
        event = "native extension " + str(args[1])
    elif event not in BLOCKED:
        return
    os.write(2, ("pysed guard: blocked " + event + "\\n").encode())
    os._exit({GUARD_STATUS})
sys.addaudithook(hook)
sys.argv = sys.argv[1:]
# only /app and the standard library: none of the verifier's own packages
sys.path[:] = [p for p in sys.path[1:] if "-packages" not in p]
sys.path.insert(0, os.path.dirname(sys.argv[0]))
runpy.run_path(sys.argv[0], run_name="__main__")
"""
CANDIDATE = ["/usr/local/bin/python3", "-S", "-c", GUARD, "/app/pysed/sed.py"]
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


def test_bracket_expressions():
    check("bracket_expressions")


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


def test_z_and_line_numbers():
    check("z_and_line_numbers")


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


def test_matrix_escapes():
    check("matrix_escapes")


def test_matrix_regex_escapes():
    check("matrix_regex_escapes")


def test_matrix_s_flags():
    check("matrix_s_flags")


def test_matrix_groups():
    check("matrix_groups")


def test_matrix_intervals():
    check("matrix_intervals")


def test_matrix_quit():
    check("matrix_quit")


def test_matrix_t_flag():
    check("matrix_t_flag")


def test_matrix_blocks():
    check("matrix_blocks")


def test_matrix_files():
    check("matrix_files")


def test_matrix_append():
    check("matrix_append")


def test_matrix_long_input():
    check("matrix_long_input")


def test_matrix_anchors():
    check("matrix_anchors")


def test_matrix_ranges():
    check("matrix_ranges")


def test_matrix_delimiters():
    check("matrix_delimiters")


def test_matrix_brackets():
    check("matrix_brackets")


def test_sweep_long_lines():
    check("sweep_long_lines")


def test_sweep_numbers():
    check("sweep_numbers")


def test_sweep_classes():
    check("sweep_classes")


def test_sweep_delimiters():
    check("sweep_delimiters")


def test_sweep_empty_regex():
    check("sweep_empty_regex")


def test_sweep_bracket_edges():
    check("sweep_bracket_edges")


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
    # packages installed outside /app are not available: the job user cannot even list them
    probe = subprocess.run(DEMOTE + ["/usr/local/bin/python3", "-S", "-c", "import glob, os; "
                                     "[os.listdir(p) for p in glob.glob('/usr/local/lib/python3*/site-packages')]"],
                           env=ENV, capture_output=True)
    assert probe.returncode != 0, "the job user can read the verifier's site-packages"
    for script, opts in (("s/a/b/", []), ("/x/,/y/{s/\\(.\\)\\(.\\)/\\2\\1/g;p}", []), ("s/(a|ab)(c|bcd)*/X/", ["-E"])):
        case = {"opts": opts, "script": script, "input": "aa\nabcd\nx\nyy\n"}
        path = workdir(case)
        try:
            _out, status = run(DEMOTE + CANDIDATE, case, path)
        finally:
            shutil.rmtree(path, ignore_errors=True)
        assert status != GUARD_STATUS, f"sed {arguments(case)!r} tried to start a process or load native code"
