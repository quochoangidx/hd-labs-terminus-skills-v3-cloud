from __future__ import annotations

import importlib.util
import json
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "freeze_reference_goldens.py"
SPEC = importlib.util.spec_from_file_location("freeze_reference_goldens", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

VERIFIER = '''
import hashlib, json, subprocess

CASES = [{"family": "b", "args": ["two"]}, {"family": "a", "args": ["one"]},
         {"family": "a", "args": ["three"]}]

def run(command, case):
    proc = subprocess.run(command + case["args"], capture_output=True)
    return proc.stdout, proc.returncode

def result_digest(result):
    return f"{result[1]}:" + hashlib.sha256(result[0]).hexdigest()[:24]

def inputs_digest(cases):
    return hashlib.sha256(json.dumps(cases, sort_keys=True).encode()).hexdigest()
'''


def test_freezes_one_digest_per_case_in_check_order(tmp_path: Path) -> None:
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_outputs.py").write_text(VERIFIER)
    out = tmp_path / "expected.json"

    assert MODULE.inner(tests, ["/bin/echo"], None, out) == 0

    frozen = json.loads(out.read_text())["families"]
    assert sorted(frozen) == ["a", "b"]
    assert [r.split(":")[0] for r in frozen["a"]["results"]] == ["0", "0"]
    import hashlib
    assert frozen["a"]["results"][1].endswith(hashlib.sha256(b"three\n").hexdigest()[:24])


def test_refuses_a_verifier_without_the_digest_hooks(tmp_path: Path) -> None:
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_outputs.py").write_text("CASES = []\n")

    assert MODULE.inner(tests, ["/bin/echo"], None, tmp_path / "expected.json") == 2
