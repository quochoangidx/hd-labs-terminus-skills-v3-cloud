"""Verifier for pyed: every case is run through GNU ed 1.19 and through the delivered
/app/pyed/ed.py, and they must agree on the standard output (byte for byte), on whether
the exit status is zero, and on the files left in the working directory.

The expected result of each case is produced at test time by the GNU ed 1.19 binary of
this image, run by the verifier itself; the binary is made root-only before any candidate
code runs. Each program runs in its own fresh directory holding the case's files, with
LC_ALL=C; the candidate runs as an unprivileged user, through the launcher in guard.py,
which stops a run that starts another program or imports code from outside the standard
library. The command script reaches standard input either through a pipe or as a regular
file, as the case says.
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
CASE_DIR = os.path.join(HERE, "cases")


def load_cases():
    """Read the corpus and refuse to run unless it matches the committed roster.

    The cases live one per line in a file per family, with the input files shared through
    a named fixture table, so each file stays small enough to be read whole. That only
    helps if the roster is checked rather than assumed, so collection fails when a family
    is missing, a count differs, or a case names a fixture that is not in the table.
    """
    with open(os.path.join(CASE_DIR, "roster.json"), encoding="utf-8") as handle:
        roster = json.load(handle)
    with open(os.path.join(CASE_DIR, "fixtures.json"), encoding="utf-8") as handle:
        fixtures = json.load(handle)
    if len(fixtures) != roster["fixtures"]:
        raise AssertionError(f"roster expects {roster['fixtures']} fixture sets, found {len(fixtures)}")
    cases = []
    for family, expected in sorted(roster["families"].items()):
        path = os.path.join(CASE_DIR, family + ".jsonl")
        if not os.path.isfile(path):
            raise AssertionError(f"{family}: {path} is missing")
        with open(path, encoding="utf-8") as handle:
            rows = [json.loads(line) for line in handle if line.strip()]
        if len(rows) != expected:
            raise AssertionError(f"{family}: roster expects {expected} cases, the file holds {len(rows)}")
        for row in rows:
            if row["fixture"] not in fixtures:
                raise AssertionError(f"{family}: no fixture named {row['fixture']}")
            cases.append({"family": family, "args": row["args"], "stdin": row["stdin"],
                          "script": row["script"], "files": fixtures[row["fixture"]]})
    if len(cases) != roster["total"]:
        raise AssertionError(f"roster expects {roster['total']} cases, loaded {len(cases)}")
    return cases


CASES = load_cases()

GNU_ED = "/usr/bin/ed"
PYTHON = "/usr/local/bin/python3"
GUARD = "/opt/pyedguard/guard.py"
GUARDCHECK = "/opt/pyedguard/guardcheck"
DELIVERED = "/app"
ENTRY = "/app/pyed/ed.py"
CANDIDATE = [PYTHON, GUARD, ENTRY]
DEMOTE = ["setpriv", "--reuid=65534", "--regid=65534", "--clear-groups", "--no-new-privs", "--"]
ENV = {"LC_ALL": "C", "PATH": "/usr/local/bin:/usr/bin:/bin", "HOME": "/nonexistent",
       "PYTHONDONTWRITEBYTECODE": "1"}


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
        assert b"pyed-guard: " in err, f"{program}: no reason reported, stderr {err!r}"
        assert b"GNU ed" not in out and b"vendored" not in out and b"libc loaded" not in out, (
            f"{program}: it produced {out!r}")
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
    local = {"pyed"}
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
