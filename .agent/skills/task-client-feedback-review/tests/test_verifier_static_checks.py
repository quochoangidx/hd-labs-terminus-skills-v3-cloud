from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "verifier_static_checks.py"
SPEC = importlib.util.spec_from_file_location("verifier_static_checks", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_flags_root_build_and_candidate_wrapper() -> None:
    source = '''
import subprocess

APP_DIR = "/app"

def _run_candidate(argv):
    return subprocess.Popen(argv, start_new_session=True)

def simulator():
    subprocess.run(["make", "clean"], cwd=APP_DIR)
    subprocess.run(["make", "build"], cwd=APP_DIR)
'''
    count, unsafe = MODULE.analyze_candidate_privileges(source)
    assert count == 3
    assert {item.function for item in unsafe} == {"_run_candidate", "simulator"}


def test_accepts_demoted_build_and_runtime() -> None:
    source = '''
import subprocess

def _candidate_user_kwargs():
    return {"user": "nobody", "group": "nogroup"}

def _run_candidate(argv):
    return subprocess.Popen(argv, **_candidate_user_kwargs())

def build(candidate_dir):
    return subprocess.run(["make", "build"], cwd=candidate_dir,
                          user="nobody", group="nogroup")
'''
    count, unsafe = MODULE.analyze_candidate_privileges(source)
    assert count == 2
    assert unsafe == []


def test_ignores_verifier_owned_exec_probe() -> None:
    source = '''
import subprocess

def _find_exec_base(probe):
    return subprocess.run([probe], check=False)
'''
    count, unsafe = MODULE.analyze_candidate_privileges(source)
    assert count == 0
    assert unsafe == []


def test_flags_unverified_unit_test_promise() -> None:
    contract = "The Go unit tests already in the repository must keep passing."
    verifier = 'subprocess.run(["make", "build"])'
    assert MODULE.unit_test_alignment_issue(contract, verifier)
    assert not MODULE.unit_test_alignment_issue(
        contract,
        'subprocess.run(["go", "test", "./..."])',
    )


def test_flags_setpriv_without_no_new_privs() -> None:
    unsafe = 'DROP = ["setpriv", "--reuid=12000", "--regid=12000"]'
    safe = unsafe[:-1] + ', "--no-new-privs"]'
    assert MODULE.setpriv_missing_no_new_privs(unsafe)
    assert not MODULE.setpriv_missing_no_new_privs(safe)


def test_flags_pytest_node_name_identity_channel() -> None:
    assert MODULE.test_identity_leak("path = root / request.node.name")
    assert not MODULE.test_identity_leak("path = root / uuid.uuid4().hex")


def test_flags_dual_bash_permission_restore_without_resolution() -> None:
    unsafe = '''
import os

paths = ["/bin/bash", "/usr/bin/bash"]
modes = {path: os.stat(path).st_mode for path in paths}
for path in paths:
    os.chmod(path, 0)
for path in paths:
    os.chmod(path, modes[path])
'''
    safe = unsafe.replace(
        'paths = ["/bin/bash", "/usr/bin/bash"]',
        'paths = list({Path(path).resolve() for path in ["/bin/bash", "/usr/bin/bash"]})',
    )
    assert MODULE.interpreter_permission_alias_issue(unsafe) is True
    assert MODULE.interpreter_permission_alias_issue(safe) is False


def test_interpreter_permission_parse_failure_is_incomplete_warning() -> None:
    assert MODULE.interpreter_permission_alias_issue("def broken(:") is None
