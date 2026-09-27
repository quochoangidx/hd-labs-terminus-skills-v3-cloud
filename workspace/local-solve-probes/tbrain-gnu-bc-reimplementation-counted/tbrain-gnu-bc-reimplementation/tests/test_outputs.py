"""Verifier for pybc: every case is run through GNU bc 1.07.1 and through the delivered
/app/pybc/bc.py, and their standard output must agree byte for byte.

The expected output of each case is produced at test time by the GNU bc 1.07.1 binary of
this image, run by the verifier itself; that binary and the dc of the same package are made
root-only before any candidate code runs. Each program runs in its own fresh directory
holding the case's files, with LC_ALL=C and BC_LINE_LENGTH, BC_ENV_ARGS and
POSIXLY_CORRECT unset, and reads the case's standard input from a pipe.

The candidate runs through the launcher in guard.py, which stops a run that starts another
program, loads native code or imports code from outside the standard library.
"""

import ast
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(HERE, "cases.json"), encoding="utf-8") as handle:
    CASES = json.load(handle)

GNU_BC = "/usr/bin/bc"
PYTHON = "/usr/local/bin/python3"
GUARD = "/opt/pybcguard/guard.py"
GUARDCHECK = "/opt/pybcguard/guardcheck"
DELIVERED = "/app"
ENTRY = "/app/pybc/bc.py"
CANDIDATE = [PYTHON, GUARD, ENTRY]
DEMOTE = ["setpriv", "--reuid=65534", "--regid=65534", "--clear-groups", "--no-new-privs", "--"]
ENV = {"LC_ALL": "C", "PATH": "/usr/local/bin:/usr/bin:/bin", "HOME": "/nonexistent",
       "PYTHONDONTWRITEBYTECODE": "1"}


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


def guardcheck(program, args=(), expect_status=None):
    """Run one of the launcher's own probe programs the way a candidate is run."""
    path = tempfile.mkdtemp()
    os.chmod(path, 0o777)
    try:
        proc = subprocess.Popen(DEMOTE + [PYTHON, GUARD, os.path.join(GUARDCHECK, program)] + list(args),
                                stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                cwd=path, env=ENV, start_new_session=True)
        out, err = proc.communicate(timeout=20)
        return proc.returncode, out, err
    finally:
        shutil.rmtree(path, ignore_errors=True)


def test_launcher_stops_delegation_and_foreign_code():
    """The construction rules are enforced, and an ordinary program is left alone."""
    for program in ("launcher.py", "exec_launcher.py", "vendored.py"):
        status, out, err = guardcheck(program, ["--version"])
        assert status == 120, f"{program}: expected the launcher to stop it, got status {status} and {out!r}"
        assert b"pybc-guard: " in err, f"{program}: no reason reported, stderr {err!r}"
        assert b"bc 1." not in out and b"vendored" not in out, f"{program}: it produced {out!r}"
    status, out, _err = guardcheck("plain.py", ["x"])
    assert (status, out) == (0, b"plain plain.py x\nre bb\n"), f"the launcher changed an ordinary run: {status} {out!r}"
    status, _out, _err = guardcheck("plain.py", ["fail"])
    assert status == 3, f"the launcher lost the exit status: {status}"


def delivered_files():
    """Every delivered file, leaving out the interpreter's own bytecode caches."""
    for root, dirs, names in os.walk(DELIVERED):
        dirs[:] = sorted(d for d in dirs if d != "__pycache__")
        for name in sorted(names):
            if not name.endswith(".pyc"):
                yield os.path.join(root, name)


def test_delivered_package_is_standard_library_python():
    """Everything delivered is Python text importing only the standard library and itself."""
    local = {"pybc"}
    sources = {}
    for full in delivered_files():
        if os.path.islink(full) and not os.path.realpath(full).startswith(DELIVERED + os.sep):
            raise AssertionError(f"{full} points outside the delivered package")
        with open(full, "rb") as handle:
            raw = handle.read()
        if b"\x00" in raw or raw[:4] == b"\x7fELF":
            raise AssertionError(f"{full} is not text: only Python sources and text belong here")
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as bad:
            raise AssertionError(f"{full} is not text: {bad}")
        if full.endswith(".py"):
            sources[full] = text
            local.add(os.path.splitext(os.path.basename(full))[0])
    assert ENTRY in sources, f"{ENTRY} is missing from the delivered package"
    for full, text in sorted(sources.items()):
        try:
            tree = ast.parse(text, filename=full)
        except SyntaxError as bad:
            raise AssertionError(f"{full} does not parse: {bad}")
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                names = [node.module]
            for name in names:
                top = name.split(".")[0]
                assert top in sys.stdlib_module_names or top in local, (
                    f"{full} imports {name}, which is neither the standard library nor part of "
                    "the delivered package")
