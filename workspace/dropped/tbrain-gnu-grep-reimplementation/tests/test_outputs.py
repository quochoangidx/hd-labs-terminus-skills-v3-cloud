"""Verifier for pygrep: every case is run through GNU grep 3.8 and through the delivered
/app/pygrep/grep.py; the standard output (byte for byte) and the exit status must agree.

The expected result of each case is produced at test time by the GNU grep 3.8 binary of
this image, run by the verifier itself; the binary is made root-only before any candidate
code runs. Each program runs in its own fresh directory holding the case's files, with
LC_ALL=C, and reads the case's standard input from a pipe.

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
ROSTER = {
    "patterns": 32,
    "only_matching": 16,
    "output_controls": 21,
    "context": 18,
    "null_data": 6,
    "binary_input": 8,
    "files_and_status": 19,
    "mixed_1": 236,
    "mixed_2": 235,
    "mixed_3": 234,
    "mixed_4": 235,
    "mixed_5": 233,
    "mixed_6": 236,
    "mixed_7": 235,
    "mixed_8": 235,
}


def load_cases():
    """Read every case chunk (one JSON case per line) and pin the roster."""
    cases = []
    folder = os.path.join(HERE, "cases")
    for name in sorted(os.listdir(folder)):
        if name.endswith(".jsonl"):
            with open(os.path.join(folder, name), encoding="utf-8") as handle:
                cases.extend(json.loads(line) for line in handle if line.strip())
    counts = {}
    for case in cases:
        counts[case["family"]] = counts.get(case["family"], 0) + 1
    assert counts == ROSTER, f"case roster mismatch: {counts} != {ROSTER}"
    return cases


CASES = load_cases()

GNU_GREP = "/bin/grep"
PYTHON = "/usr/local/bin/python3"
GUARD = "/opt/pygrepguard/guard.py"
GUARDCHECK = "/opt/pygrepguard/guardcheck"
DELIVERED = "/app"
ENTRY = "/app/pygrep/grep.py"
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
    for program in ("launcher.py", "exec_launcher.py", "vendored.py", "native.py"):
        status, out, err = guardcheck(program, ["--version"])
        assert status == 120, f"{program}: expected the launcher to stop it, got status {status} and {out!r}"
        assert b"pygrep-guard: " in err, f"{program}: no reason reported, stderr {err!r}"
        assert b"GNU grep" not in out and b"vendored" not in out and b"native" not in out, f"{program}: it produced {out!r}"
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
    local = {"pygrep"}
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
