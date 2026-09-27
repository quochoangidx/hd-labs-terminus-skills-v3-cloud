"""Verifier for pyed: every case is run through GNU ed 1.19 and through the delivered
/app/pyed/ed.py, and they must agree on the standard output (byte for byte), on whether
the exit status is zero, and on the files left in the working directory.

The expected result of each case is produced at test time by the GNU ed 1.19 binary of
this image, run by the verifier itself; the binary is made root-only before any candidate
code runs. Each program runs in its own fresh directory holding the case's files, with
LC_ALL=C; the candidate runs as an unprivileged user. The command script reaches standard
input either through a pipe or as a regular file, as the case says.
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

GNU_ED = "/usr/bin/ed"
CANDIDATE = ["/usr/local/bin/python3", "/app/pyed/ed.py"]
DEMOTE = ["setpriv", "--reuid=65534", "--regid=65534", "--clear-groups", "--no-new-privs", "--"]
ENV = {"LC_ALL": "C", "PATH": "/usr/local/bin:/usr/bin:/bin", "HOME": "/nonexistent"}


def workdir(case):
    path = tempfile.mkdtemp()
    os.chmod(path, 0o777)
    for name, text in case["files"]:
        with open(os.path.join(path, name), "w", encoding="latin-1") as handle:
            handle.write(text)
        os.chmod(os.path.join(path, name), 0o666)
    return path


def snapshot(path):
    result = {}
    for name in sorted(os.listdir(path)):
        full = os.path.join(path, name)
        if os.path.isfile(full):
            with open(full, "rb") as handle:
                result[name] = handle.read()
        else:
            result[name] = None
    return result


def run(command, case):
    path = workdir(case)
    script_dir = tempfile.mkdtemp()
    os.chmod(script_dir, 0o755)
    script = os.path.join(script_dir, "script")
    with open(script, "w", encoding="latin-1") as handle:
        handle.write(case["script"])
    os.chmod(script, 0o644)
    try:
        if case["stdin"] == "file":
            stdin = open(script, "rb")
            data = None
        else:
            stdin = subprocess.PIPE
            data = case["script"].encode("latin-1")
        proc = subprocess.Popen(command + case["args"], stdin=stdin, stdout=subprocess.PIPE,
                                stderr=subprocess.DEVNULL, cwd=path, env=ENV, start_new_session=True)
        try:
            out, _err = proc.communicate(data, timeout=20)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)
            proc.communicate()
            return ("timeout", None, None)
        finally:
            if case["stdin"] == "file":
                stdin.close()
        return (out, proc.returncode == 0, snapshot(path))
    finally:
        shutil.rmtree(path, ignore_errors=True)
        shutil.rmtree(script_dir, ignore_errors=True)


def check(family):
    cases = [c for c in CASES if c["family"] == family]
    assert cases, f"no cases for {family}"
    failures = []
    for case in cases:
        want = run([GNU_ED], case)
        got = run(DEMOTE + CANDIDATE, case)
        if got != want:
            failures.append((case, want, got))
    if failures:
        case, want, got = failures[0]
        detail = (f"{len(failures)} of {len(cases)} cases differ; first: ed {case['args']!r} with "
                  f"files {[n for n, _t in case['files']]} and script {case['script']!r} on a "
                  f"{case['stdin']}: expected output {want[0]!r} (zero status: {want[1]}, files: "
                  f"{want[2]!r}), got {got[0]!r} (zero status: {got[1]}, files: {got[2]!r})")
        raise AssertionError(detail)


def test_addresses():
    check("addresses")


def test_append_insert_change():
    check("append_insert_change")


def test_delete_join_move_copy():
    check("delete_join_move_copy")


def test_substitute():
    check("substitute")


def test_global_commands():
    check("global_commands")


def test_interactive_global():
    check("interactive_global")


def test_undo():
    check("undo")


def test_print_list_number():
    check("print_list_number")


def test_regex():
    check("regex")


def test_regex_extended():
    check("regex_extended")


def test_files_and_write():
    check("files_and_write")


def test_errors_and_exit():
    check("errors_and_exit")


def test_options():
    check("options")


def test_odd_files():
    check("odd_files")


def test_mixed_scripts_1():
    check("mixed_scripts_1")


def test_mixed_scripts_2():
    check("mixed_scripts_2")


def test_mixed_scripts_3():
    check("mixed_scripts_3")


def test_mixed_scripts_4():
    check("mixed_scripts_4")


def test_mixed_scripts_5():
    check("mixed_scripts_5")


def test_mixed_scripts_6():
    check("mixed_scripts_6")


def test_mixed_scripts_7():
    check("mixed_scripts_7")


def test_mixed_scripts_8():
    check("mixed_scripts_8")
