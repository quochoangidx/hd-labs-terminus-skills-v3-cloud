from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).parents[1] / "scripts" / "fixture_bounds_check.py"
SPEC = importlib.util.spec_from_file_location("fixture_bounds_check", SCRIPT)
CHECK = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHECK)


def test_closed_ends_must_be_reached_exactly() -> None:
    rows, gaps = CHECK.check([{"name": "mdl", "key": "mdl", "low": 0.0001, "high": 100}], {"mdl": [0.0051, 100]})
    assert gaps == 1 and rows[0]["status"] == "GAP"
    rows, gaps = CHECK.check([{"name": "mdl", "key": "mdl", "low": 0.0001, "high": 100}], {"mdl": [0.0001, 7, 100]})
    assert gaps == 0


def test_open_ends_accept_a_value_just_inside() -> None:
    spec = [{"name": "ratio", "key": "r", "low": 0.5, "high": 1.5, "open": "both"}]
    assert CHECK.check(spec, {"r": [0.5002, 1.4998]})[1] == 0
    assert CHECK.check(spec, {"r": [0.8, 1.25]})[1] == 1


def test_missing_key_and_unbounded_range_are_gaps() -> None:
    assert CHECK.check([{"name": "x", "key": "x", "low": 0}], {})[1] == 1
    rows, gaps = CHECK.check([{"name": "true", "key": "t"}], {"t": [1, 80]})
    assert gaps == 1 and "unbounded" in rows[0]["reason"]


def test_must_reach_negative() -> None:
    spec = [{"name": "intercept", "key": "b", "must_reach_negative": True}]
    assert CHECK.check(spec, {"b": [0.1, 5]})[1] == 1
    assert CHECK.check(spec, {"b": [-1.6, 5]})[1] == 0


def test_cli_reads_sealed_rows_through_the_adapter(tmp_path: Path) -> None:
    task = tmp_path / "task"
    (task / "tests/expected").mkdir(parents=True)
    (task / "tests/expected/a.jsonl").write_text("\n".join(json.dumps({"batch": {"dilution": d}}) for d in (1, 40, 1000)) + "\n")
    spec = tmp_path / "ranges.json"
    spec.write_text(json.dumps([{"name": "dilution", "key": "dilution", "low": 1, "high": 1000}]))
    adapter = tmp_path / "observe.py"
    adapter.write_text("def observe(rows):\n    return {'dilution': [r['batch']['dilution'] for r in rows]}\n")
    out = tmp_path / "receipt.json"
    proc = subprocess.run([sys.executable, str(SCRIPT), str(task), "--spec", str(spec), "--adapter", str(adapter), "--output", str(out)], capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert json.loads(out.read_text())["status"] == "pass"
