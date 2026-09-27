"""Verifier for the cyclecount repair (cycle count procedure CC-2).

Before any candidate code runs, the delivered driver's bytes are recorded, the verifier's own copy
(tests/shipped/app/tools/cyclecount_run.py) is os.replace-d onto /app/tools/cyclecount_run.py, and all of /app is
made root-owned and unwritable by others. Every count sheet is reported by the documented command,
python3 /app/tools/cyclecount_run.py SHEET.json, as an unprivileged user in its own session with an isolated
interpreter, from a fresh directory, on a file with the same neutral name for every job. Expected reports were
written ahead of time by solution/seal.py from an independent model of the procedure and are read from
tests/expected/, whose SHA-256 sums and row counts are pinned in tests/expected/ROSTER.

One test per rule. Two figures are left by the procedure to today's code: the tolerance of a line that is not a
graded item, and the units booked by a line that is not adjusted. Each is graded only in its own tests.
"""

import copy
import hashlib
import json
import os
import random
import shutil
import signal
import subprocess
import tempfile
import time
from pathlib import Path

TESTS = Path(__file__).resolve().parent
EXPECTED = TESTS / "expected"
SHIPPED_APP = TESTS / "shipped" / "app"
SHIPPED_DRIVER = SHIPPED_APP / "tools" / "cyclecount_run.py"
DELIVERED_DRIVER = Path("/app/tools/cyclecount_run.py")
CANDIDATE_UID = 65534
SHIPPED_UID = 65533
ENV = ["/usr/bin/env", "-i", "PATH=/usr/local/bin:/usr/bin:/bin", "HOME=/nonexistent", "LANG=C.UTF-8", "PYTHONDONTWRITEBYTECODE=1"]
DEADLINE = time.monotonic() + 1500
# Fresh labels for the relabelled generated files; printed in every failure message.
RELABEL_SEED = int.from_bytes(os.urandom(8), "big")
LINE_KEYS = ("sku", "variance", "tolerance", "status", "value", "booked")
CODE = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-"
# Figures left by the procedure to today's code that a family grades; a line of a class other than A, B or C
# appears only in a family that grades it.
GRADES = {"other_classes": {"other_class"}, "booked_not_adjusted": {"booked"}, "together": {"other_class", "booked"}}


def _roster():
    """family -> (file name, SHA-256, row count); files are named NN-<family>.jsonl, NN their reading order."""
    rows = {}
    for line in (EXPECTED / "ROSTER").read_text().splitlines():
        digest, name, count = line.split()
        rows[name.split("-", 1)[1].removesuffix(".jsonl")] = (name, digest, int(count))
    return rows


ROSTER = _roster()


def _install_driver():
    """Keep the delivered driver's bytes, then put the verifier's copy on the documented path."""
    delivered = DELIVERED_DRIVER.read_bytes() if DELIVERED_DRIVER.is_file() else None
    DELIVERED_DRIVER.parent.mkdir(parents=True, exist_ok=True)
    staged = DELIVERED_DRIVER.with_name(".cyclecount_run.verifier")
    shutil.copyfile(SHIPPED_DRIVER, staged)
    os.chmod(staged, 0o644)
    os.replace(staged, DELIVERED_DRIVER)
    return delivered


def _install_shipped():
    """A copy of the shipped package that only its own user can open."""
    root = Path(tempfile.mkdtemp())
    shutil.copytree(SHIPPED_APP, root / "app")
    for path in [root, *root.rglob("*")]:
        os.chown(path, SHIPPED_UID, SHIPPED_UID)
    os.chmod(root, 0o700)
    return root


def _seal_app():
    """Make the delivered /app root-owned and closed to writes by anyone else, without following links, so
    candidate code cannot change the driver, or anything else under /app, between jobs."""
    root = DELIVERED_DRIVER.parent.parent
    for path in [root, *root.rglob("*")]:
        os.lchown(path, 0, 0)
        if not path.is_symlink():
            os.chmod(path, path.stat().st_mode & ~0o7022)


DELIVERED_BYTES = _install_driver()
_seal_app()
SHIPPED_RUN = _install_shipped()


def _kill_user(uid):
    """SIGKILL every process still running as ``uid``."""
    for entry in os.listdir("/proc"):
        if entry.isdigit():
            try:
                if os.stat(f"/proc/{entry}").st_uid == uid:
                    os.kill(int(entry), signal.SIGKILL)
            except OSError:
                pass


def run_as(uid, argv, cwd, timeout):
    """Run code as ``uid``, in its own session, without new privileges; kill the whole group afterwards."""
    proc = subprocess.Popen(
        ["setpriv", f"--reuid={uid}", f"--regid={uid}", "--clear-groups", "--no-new-privs", "--"] + ENV + argv,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )
    try:
        out, err = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGKILL)
        proc.communicate()
        raise
    finally:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        _kill_user(uid)  # anything that left the session
    return proc.returncode, out, err


def report(sheet, shipped=False):
    """Run the driver on one count sheet (the candidate's package, or the shipped copy); return its parsed stdout."""
    stage = tempfile.mkdtemp()
    work = tempfile.mkdtemp()
    os.chmod(stage, 0o755)
    os.chmod(work, 0o777)
    path = os.path.join(stage, "sheet.json")
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(sheet, handle)
    os.chmod(path, 0o644)
    remaining = DEADLINE - time.monotonic()
    assert remaining > 0, "verifier time budget exhausted"
    uid, driver = (SHIPPED_UID, str(SHIPPED_RUN / "app" / "tools" / "cyclecount_run.py")) if shipped else (CANDIDATE_UID, str(DELIVERED_DRIVER))
    code, out, err = run_as(uid, ["python3", "-I", "-S", driver, path], work, remaining)
    shutil.rmtree(stage, ignore_errors=True)
    shutil.rmtree(work, ignore_errors=True)
    assert code == 0, f"driver exited {code}: {err[-2000:]}"
    return json.loads(out)


def within_limits(s):
    """Rule 1.3, every limit including its ends: each graded sheet must keep to it."""
    lines = s["lines"]
    assert isinstance(s["sheet"], str) and 1 <= len(lines) <= 300
    assert len({x["sku"] for x in lines}) == len(lines)
    for x in lines:
        assert 1 <= len(x["sku"]) <= 12 and set(x["sku"]) <= set(CODE)
        assert len(x["class"]) == 1 and "A" <= x["class"] <= "Z"
        for k in ("system", "count"):
            assert type(x[k]) is int and 0 <= x[k] <= 100000
        assert x["recount"] is None or (type(x["recount"]) is int and 0 <= x["recount"] <= 100000)
        assert type(x["unit_cost"]) is int and 1 <= x["unit_cost"] <= 1000000


def load(name):
    """Rows of one family; fails when the file, its digest or its count differ from the roster, or a sheet breaks
    rule 1.3 or carries a line of a class other than A, B or C into a family that does not grade it."""
    file, digest, count = ROSTER[name]
    raw = (EXPECTED / file).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == digest, f"{name} does not match the roster"
    rows = [json.loads(line) for line in raw.decode().splitlines() if line]
    assert len(rows) == count, f"{name}: {len(rows)} rows, roster says {count}"
    for row in rows:
        within_limits(row["sheet"])
        other = any(x["class"] not in "ABC" for x in row["sheet"]["lines"])
        assert not other or "other_class" in GRADES.get(name, set()), f"{name}: {row['sheet']['sheet']} has a class other than A, B or C"
    return rows


def _same(actual, expected, where):
    assert type(actual) is type(expected) and actual == expected, f"{where}: {actual!r}, expected {expected!r}"


def compare(actual, expected, label, grades=frozenset()):
    """Every key the README lists, as a JSON integer or string; further keys are ignored. The units booked by a
    line that is not adjusted are compared only where ``grades`` holds "booked"."""
    assert isinstance(actual, dict) and set(actual) >= {"sheet", "lines", "shrink"}, f"{label}: top-level keys"
    _same(actual["sheet"], expected["sheet"], f"{label} sheet")
    _same(actual["shrink"], expected["shrink"], f"{label} shrink")
    got, want = actual["lines"], expected["lines"]
    assert isinstance(got, list) and len(got) == len(want), f"{label}: {len(got) if isinstance(got, list) else got!r} lines, expected {len(want)}"
    for index, (row, ref) in enumerate(zip(got, want)):
        assert isinstance(row, dict) and set(row) >= set(LINE_KEYS), f"{label} lines[{index}]: keys {row!r}"
        for key in LINE_KEYS:
            if key == "booked" and ref["status"] != "adjust" and "booked" not in grades:
                continue
            _same(row[key], ref[key], f"{label} lines[{index}] ({ref['sku']}) {key}")


def check_family(name):
    grades = GRADES.get(name, frozenset())
    for row in load(name):
        compare(report(row["sheet"]), row["report"], f"{name} {row['sheet']['sheet']}", grades)


def test_rule_2_1_recount_replaces_the_count():
    """The final count is the recount when one was taken."""
    check_family("recounts")


def test_rule_2_3_graded_tolerances_on_the_edge():
    """A nought, B 2 per cent and C 5 per cent of the system quantity, a fraction dropped; on the edge and one past."""
    check_family("graded_tolerance")


def test_rule_3_1_recount_or_adjust():
    """Outside tolerance with no recount is "recount"; with a recount it is "adjust"."""
    check_family("status")


def test_rule_3_4_shrink_counts_adjusted_shortages_only():
    """Shrink sums adjusted shortages; a surplus or a line awaiting recount does not change it."""
    check_family("shrink")


def test_rule_3_2_value_and_line_order():
    """Every line's value, lines in sheet order, SKUs of one to twelve characters."""
    check_family("value_and_order")


def test_line_of_another_class_keeps_todays_tolerance():
    """The procedure gives no tolerance for a line that is not a graded item: today's step stands."""
    check_family("other_classes")


def test_line_not_adjusted_keeps_todays_booked_units():
    """The procedure gives no booked figure for a line that is not adjusted: today's step stands."""
    check_family("booked_not_adjusted")


def test_figures_left_to_todays_code_together():
    """Other classes and lines not adjusted, with shortages and surpluses, in one sheet."""
    check_family("together")


def test_rule_1_3_limits_reached():
    """300 lines; quantities 0 and 100,000; unit costs 1 and 1,000,000."""
    assert len(load("limits")[0]["sheet"]["lines"]) == 300
    check_family("limits")


def relabel(row, rng):
    """The same sheet under a fresh name and SKUs, lines shuffled; the expected report follows."""
    s, want = copy.deepcopy(row["sheet"]), copy.deepcopy(row["report"])
    skus = set()
    while len(skus) < len(s["lines"]):
        skus.add("".join(rng.choice(CODE) for _ in range(rng.randint(1, 12))))
    skus = sorted(skus)
    order = list(range(len(s["lines"])))
    rng.shuffle(order)
    name = "CC2-" + "".join(rng.choice(CODE[:36]) for _ in range(8))
    lines = [dict(s["lines"][i], sku=skus[i]) for i in order]
    rows = [dict(want["lines"][i], sku=skus[i]) for i in order]
    return {"sheet": name, "lines": lines}, {"sheet": name, "lines": rows, "shrink": want["shrink"]}


def test_generated_count_sheets():
    """Seeded sheets over the graded classes, as sealed and under fresh labels."""
    check_family("generated")
    rng = random.Random(RELABEL_SEED)
    for row in load("generated"):
        s, expected = relabel(row, rng)
        within_limits(s)
        compare(report(s), expected, f"generated {row['sheet']['sheet']} relabelled (seed {RELABEL_SEED})")


def _unreadable_by_candidate(target):
    probe = f"import os,sys\ntry:\n    os.listdir({target!r}) if os.path.isdir({target!r}) else open({target!r}).read()\nexcept OSError:\n    sys.exit(0)\nsys.exit(1)"
    code, _, _ = run_as(CANDIDATE_UID, ["python3", "-I", "-S", "-c", probe], "/", 60)
    return code == 0


def test_candidate_cannot_read_verifier_state():
    """The candidate's user cannot read /tests, the expectations, the shipped copy or /logs/verifier."""
    for target in ["/tests", str(EXPECTED / "ROSTER"), str(SHIPPED_RUN), str(SHIPPED_RUN / "app" / "tools" / "cyclecount_run.py"), "/logs/verifier"]:
        assert _unreadable_by_candidate(target), f"the candidate's user can read {target}"
    assert not _unreadable_by_candidate("/app/README.md"), "control: the probe cannot read a world-readable file"


def test_submitted_driver_unchanged():
    """The delivered driver matches the shipped one, and is still the verifier's copy after every run."""
    assert DELIVERED_BYTES == SHIPPED_DRIVER.read_bytes(), "the delivered /app/tools/cyclecount_run.py differs from the shipped driver"
    assert DELIVERED_DRIVER.read_bytes() == SHIPPED_DRIVER.read_bytes(), "the driver on the documented path changed during the run"
    for path in [DELIVERED_DRIVER, DELIVERED_DRIVER.parent, DELIVERED_DRIVER.parent.parent]:
        info = path.lstat()
        assert info.st_uid == 0 and not info.st_mode & 0o022, f"{path} is writable by the candidate's user"
