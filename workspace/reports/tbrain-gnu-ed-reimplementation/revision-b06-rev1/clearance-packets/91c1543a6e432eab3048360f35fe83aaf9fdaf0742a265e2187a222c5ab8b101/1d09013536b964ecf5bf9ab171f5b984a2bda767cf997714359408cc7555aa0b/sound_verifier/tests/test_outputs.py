"""Verifier for pyed: every case is run through GNU ed 1.19 and through the delivered
/app/pyed/ed.py, and they must agree on the standard output (byte for byte), on whether
the exit status is zero, and on the files left in the working directory.

The cases are the committed families under cases/, one rule each, and the scripts that
generated.py draws from the command grammar when the verifier collects. scope.py checks
every one of them against the input domain the instruction states before anything runs.

The expected result of each case is produced at test time by the GNU ed 1.19 binary of
this image, run by the verifier itself; the binary is made root-only before any candidate
code runs. Each program runs in its own fresh directory holding the case's files, with
LC_ALL=C; the candidate runs as an unprivileged user, through the launcher in guard.py,
which stops a run that starts another program, loads native code or imports code that
is neither in the standard library nor a delivered Python source file. The command script reaches
standard input either through a pipe or as a regular file, as the case says.
"""

import json
import os
import py_compile
import shutil
import signal
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
CASE_DIR = os.path.join(HERE, "cases")
sys.path.insert(0, HERE)

import generated  # noqa: E402
import scope  # noqa: E402


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
    buckets = generated.generate()
    if len(buckets) != generated.BUCKETS:
        raise AssertionError(f"expected {generated.BUCKETS} generated buckets, got {len(buckets)}")
    for family, rows in sorted(buckets.items()):
        if len(rows) != generated.PER_BUCKET:
            raise AssertionError(f"{family}: expected {generated.PER_BUCKET} scripts, got {len(rows)}")
        for row in rows:
            cases.append({"family": family, "args": row["args"], "stdin": row["stdin"],
                          "script": row["script"], "files": row["files"]})
    # every case must stay inside the domain the instruction states (scope.py)
    outside = [(case["family"], case["script"], problems) for case in cases
               for problems in [scope.case_problems(case)] if problems]
    if outside:
        family, script, problems = outside[0]
        raise AssertionError(f"{len(outside)} cases leave the stated domain; first: {family} "
                             f"{script!r}: {'; '.join(problems)}")
    return cases


CASES = load_cases()

WORKERS = max(1, min(8, len(os.sched_getaffinity(0)) if hasattr(os, "sched_getaffinity") else (os.cpu_count() or 1)))
GNU_ED = "/usr/bin/ed"
PYTHON = "/usr/local/bin/python3"
GUARD = "/opt/pyedguard/guard.py"
GUARDCHECK = "/opt/pyedguard/guardcheck"
ENTRY = "/app/pyed/ed.py"
CANDIDATE = [PYTHON, GUARD, ENTRY]
DEMOTE = ["setpriv", "--reuid=65534", "--regid=65534", "--clear-groups", "--no-new-privs", "--"]
ENV = {"LC_ALL": "C", "PATH": "/usr/local/bin:/usr/bin:/bin", "HOME": "/nonexistent",
       "PYTHONDONTWRITEBYTECODE": "1"}


def workdir(case):
    """A fresh directory holding the case's files; a name with a directory part
    creates that directory, and a name ending in a slash is a directory alone."""
    path = tempfile.mkdtemp()
    os.chmod(path, 0o777)
    for name, text in case["files"]:
        full = os.path.join(path, name)
        parent = full if name.endswith("/") else os.path.dirname(full)
        if parent != path:
            os.makedirs(parent, exist_ok=True)
            os.chmod(parent, 0o777)
        if name.endswith("/"):
            continue
        with open(full, "w", encoding="latin-1") as handle:
            handle.write(text)
        os.chmod(full, 0o666)
    return path


def snapshot(path):
    """Every file under the directory by relative path with its bytes, and every
    directory by its path with a trailing slash."""
    result = {}
    for root, dirs, names in os.walk(path):
        dirs.sort()
        rel = os.path.relpath(root, path)
        prefix = "" if rel == "." else rel + "/"
        for name in dirs:
            result[prefix + name + "/"] = None
        for name in sorted(names):
            with open(os.path.join(root, name), "rb") as handle:
                result[prefix + name] = handle.read()
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
    # each case runs in its own fresh directories, so cases are independent and can run
    # side by side; map() keeps the corpus order, so the first failure reported is stable
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        results = list(pool.map(lambda case: (case, run([GNU_ED], case), run(DEMOTE + CANDIDATE, case)), cases))
    failures = [(case, want, got) for case, want, got in results if got != want]
    if failures:
        case, want, got = failures[0]
        detail = (f"{len(failures)} of {len(cases)} cases differ; first: ed {case['args']!r} with "
                  f"files {[n for n, _t in case['files']]} and script {case['script']!r} on a "
                  f"{case['stdin']}: expected output {want[0]!r} (zero status: {want[1]}, files: "
                  f"{want[2]!r}), got {got[0]!r} (zero status: {got[1]}, files: {got[2]!r})")
        raise AssertionError(detail)


def guardcheck(program, args=(), folder=GUARDCHECK):
    """Run one of the launcher's own probe programs the way a candidate is run."""
    path = tempfile.mkdtemp()
    os.chmod(path, 0o777)
    try:
        proc = subprocess.Popen(DEMOTE + [PYTHON, GUARD, os.path.join(folder, program)] + list(args),
                                stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                cwd=path, env=ENV, start_new_session=True)
        out, err = proc.communicate(timeout=20)
        return proc.returncode, out, err
    finally:
        shutil.rmtree(path, ignore_errors=True)


def bytecode_folder():
    """A program folder holding bytecode.py and legacy.pyc, a compiled module with no
    source beside it, so the program's own tree holds a file that is not Python source."""
    folder = tempfile.mkdtemp()
    os.chmod(folder, 0o755)
    shutil.copy(os.path.join(GUARDCHECK, "bytecode.py"), folder)
    py_compile.compile(os.path.join(GUARDCHECK, "..", "guardvendor", "thirdparty.py"),
                       cfile=os.path.join(folder, "legacy.pyc"), doraise=True)
    for name in os.listdir(folder):
        os.chmod(os.path.join(folder, name), 0o644)
    return folder


def test_launcher_stops_delegation_and_foreign_code():
    """The construction rules are enforced, and an ordinary program is left alone.

    Besides the plain routes (subprocess, exec, ctypes, an SQLite extension, a module
    from outside the program's own files or an installed one),
    the probes take the routes a program could use against a launcher that shares its
    process: the C helper behind subprocess, which raises no audit event, a fresh copy
    of that helper, a search of live objects for the hook, and rebinding every name the
    launcher's module, os, posix and builtins hold before replacing itself, and a module
    delivered as compiled bytecode rather than as Python source.
    """
    compiled = bytecode_folder()
    probes = [(name, GUARDCHECK) for name in (
        "launcher.py", "exec_launcher.py", "vendored.py", "native.py", "installed.py",
        "forkexec.py", "reimport.py", "gcreach.py", "tamper.py", "sqlite_ext.py")]
    probes.append(("bytecode.py", compiled))
    for program, folder in probes:
        status, out, err = guardcheck(program, ["--version"], folder)
        assert status == 120, f"{program}: expected the launcher to stop it, got status {status} and {out!r}"
        assert b"pyed-guard: " in err, f"{program}: no reason reported, stderr {err!r}"
        assert not any(mark in out for mark in (b"GNU ed", b"vendored", b"libc loaded",
                                               b"installed package loaded", b"another program ran",
                                               b"fork_exec returned", b"launcher reached",
                                               b"sqlite extension enabled", b"bytecode loaded")), (
            f"{program}: it produced {out!r}")
    status, out, _err = guardcheck("plain.py", ["x"])
    assert (status, out) == (0, b"plain plain.py x\nre bb\n"), f"the launcher changed an ordinary run: {status} {out!r}"
    status, _out, _err = guardcheck("plain.py", ["fail"])
    assert status == 3, f"the launcher lost the exit status: {status}"


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


def test_generated_1():
    check("generated_1")


def test_generated_2():
    check("generated_2")


def test_generated_3():
    check("generated_3")


def test_generated_4():
    check("generated_4")


def test_generated_5():
    check("generated_5")


def test_generated_6():
    check("generated_6")


def test_generated_7():
    check("generated_7")


def test_generated_8():
    check("generated_8")
