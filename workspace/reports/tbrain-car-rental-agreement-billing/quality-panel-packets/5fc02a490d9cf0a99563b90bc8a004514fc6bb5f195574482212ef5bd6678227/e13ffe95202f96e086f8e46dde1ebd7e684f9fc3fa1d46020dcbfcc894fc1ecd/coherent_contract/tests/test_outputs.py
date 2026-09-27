"""Verifier for the rentcharge repair (rental charges manual RC-3).

Before any candidate code runs, the delivered driver's bytes are recorded, the verifier's own copy
(tests/shipped/app/tools/rentcharge_run.py) is os.replace-d onto /app/tools/rentcharge_run.py, and all of /app is
made root-owned and unwritable by others. Every agreement file is billed by the documented command,
python3 /app/tools/rentcharge_run.py AGREEMENTS.json, as an unprivileged user in its own session with an isolated
interpreter, from a fresh directory, on a file with the same neutral name for every job. Expected bill runs were
written ahead of time by solution/seal.py from an independent model of the manual and are read from
tests/expected/, whose SHA-256 sums and row counts are pinned in tests/expected/ROSTER.

One test per rule. Two figures are left by the manual to today's code: the days of a rental under a day, and the
fuel charge of a car back with as much fuel as it left with or more. Inputs carrying them appear only in the tests
that grade them.
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
from datetime import datetime, timedelta
from pathlib import Path

TESTS = Path(__file__).resolve().parent
EXPECTED = TESTS / "expected"
SHIPPED_APP = TESTS / "shipped" / "app"
SHIPPED_DRIVER = SHIPPED_APP / "tools" / "rentcharge_run.py"
DELIVERED_DRIVER = Path("/app/tools/rentcharge_run.py")
CANDIDATE_UID = 65534
SHIPPED_UID = 65533
ENV = ["/usr/bin/env", "-i", "PATH=/usr/local/bin:/usr/bin:/bin", "HOME=/nonexistent", "LANG=C.UTF-8", "PYTHONDONTWRITEBYTECODE=1"]
DEADLINE = time.monotonic() + 1500
# Fresh labels for the relabelled generated files; printed in every failure message.
RELABEL_SEED = int.from_bytes(os.urandom(8), "big")
BILL_KEYS = ("id", "days", "miles", "time_charge", "mileage_charge", "fuel_charge", "tax", "total")
CODE = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
DAY = 1440
FMT = "%Y-%m-%dT%H:%M"
# Inputs whose figures the manual leaves to today's code, allowed only in the families that grade them.
SILENT = {"short_days": {"short"}, "short_allowance": {"short"}, "fuel_not_short": {"fuller"}, "traps_combined": {"short", "fuller"}}


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
    staged = DELIVERED_DRIVER.with_name(".rentcharge_run.verifier")
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


def bill_run(agreements, shipped=False):
    """Run the driver on one agreement file (the candidate's package, or the shipped copy); return its parsed stdout."""
    stage = tempfile.mkdtemp()
    work = tempfile.mkdtemp()
    os.chmod(stage, 0o755)
    os.chmod(work, 0o777)
    path = os.path.join(stage, "agreements.json")
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(agreements, handle)
    os.chmod(path, 0o644)
    remaining = DEADLINE - time.monotonic()
    assert remaining > 0, "verifier time budget exhausted"
    uid, driver = (SHIPPED_UID, str(SHIPPED_RUN / "app" / "tools" / "rentcharge_run.py")) if shipped else (CANDIDATE_UID, str(DELIVERED_DRIVER))
    code, out, err = run_as(uid, ["python3", "-I", "-S", driver, path], work, remaining)
    shutil.rmtree(stage, ignore_errors=True)
    shutil.rmtree(work, ignore_errors=True)
    assert code == 0, f"driver exited {code}: {err[-2000:]}"
    return json.loads(out)


def _minutes(text):
    delta = datetime.strptime(text, FMT) - datetime(2000, 1, 1)
    return delta.days * DAY + delta.seconds // 60


def within_limits(run):
    """Rule 1.3, every limit including its ends: each graded file must keep to it."""
    items = run["agreements"]
    assert isinstance(run["branch"], str) and 1 <= len(items) <= 200
    assert len({a["id"] for a in items}) == len(items)
    for a in items:
        assert 1 <= len(a["id"]) <= 10 and set(a["id"]) <= set(CODE + "-")
        assert all(2000 <= datetime.strptime(a[k], FMT).year <= 2099 for k in ("out", "in"))
        assert 1 <= _minutes(a["in"]) - _minutes(a["out"]) <= 86400
        for k, lo, hi in (("odometer_out", 0, 999_999), ("odometer_in", 0, 999_999), ("fuel_out", 0, 8), ("fuel_in", 0, 8),
                          ("day_rate", 100, 100_000), ("mile_rate", 0, 500), ("fuel_rate", 0, 2000)):
            assert type(a[k]) is int and lo <= a[k] <= hi
        assert (a["odometer_in"] - a["odometer_out"]) % 1_000_000 <= 20_000


def silent_inputs(run):
    out = set()
    for a in run["agreements"]:
        if _minutes(a["in"]) - _minutes(a["out"]) < DAY:
            out.add("short")
        if a["fuel_in"] > a["fuel_out"]:
            out.add("fuller")
    return out


def load(name):
    """Rows of one family; fails when the file, its digest or its count differ from the roster, or a file breaks
    rule 1.3 or carries an input whose figure the manual leaves to today's code into a family that does not grade it."""
    file, digest, count = ROSTER[name]
    raw = (EXPECTED / file).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == digest, f"{name} does not match the roster"
    rows = [json.loads(line) for line in raw.decode().splitlines() if line]
    assert len(rows) == count, f"{name}: {len(rows)} rows, roster says {count}"
    for row in rows:
        within_limits(row["agreements"])
        assert silent_inputs(row["agreements"]) <= SILENT.get(name, set()), f"{name}: {row['agreements']['branch']} carries {silent_inputs(row['agreements'])}"
    return rows


def _same(actual, expected, where):
    assert type(actual) is type(expected) and actual == expected, f"{where}: {actual!r}, expected {expected!r}"


def compare(actual, expected, label):
    """Every key the README lists, as a JSON integer (or the branch string); further keys are ignored."""
    assert isinstance(actual, dict) and set(actual) >= {"branch", "bills", "revenue", "tax"}, f"{label}: top-level keys"
    for key in ("branch", "revenue", "tax"):
        _same(actual[key], expected[key], f"{label} {key}")
    got, want = actual["bills"], expected["bills"]
    assert isinstance(got, list) and len(got) == len(want), f"{label}: {len(got) if isinstance(got, list) else got!r} bills, expected {len(want)}"
    for index, (row, ref) in enumerate(zip(got, want)):
        assert isinstance(row, dict) and set(row) >= set(BILL_KEYS), f"{label} bills[{index}]: keys {row!r}"
        for key in BILL_KEYS:
            _same(row[key], ref[key], f"{label} bills[{index}] ({ref['id']}) {key}")


def check_family(name):
    for row in load(name):
        compare(bill_run(row["agreements"]), row["bills"], f"{name} {row['agreements']['branch']}")


def test_rule_2_3_whole_days_and_59_minutes_free():
    """A day rental is charged its whole days, and one more only past 59 minutes over."""
    check_family("grace")


def test_rule_3_2_allowance_150_miles_a_day():
    """150 free miles for each day charged; the mile rate beyond, at rates of nought to 500."""
    check_family("allowance")


def test_rule_2_4_odometer_turns_over():
    """A reading coming back smaller than the one going out has turned over at 1,000,000."""
    check_family("turnover")


def test_rule_3_3_refuelling_fee():
    """Each eighth short at the fuel rate plus the 1,500-cent refuelling fee."""
    check_family("refuelling")


def test_rule_4_1_fuel_is_not_taxed():
    """Tax is 8.25 per cent of the time and mileage charges only."""
    check_family("tax_base")


def test_rule_1_2_tax_half_cent_goes_up():
    """The tax to the nearest cent, an exact half cent going up."""
    check_family("tax_rounding")


def test_bill_order_and_file_totals():
    """Bills in file order; revenue and tax summed over the file."""
    check_family("order_and_totals")


def test_rental_under_a_day_keeps_todays_days():
    """The manual gives no days for a rental under a day: today's step (every day begun) stands."""
    check_family("short_days")


def test_rule_3_2_allowance_on_a_rental_under_a_day():
    """A rental under a day of an hour or more drives 150 miles free for the day it is charged for."""
    check_family("short_allowance")


def test_car_back_as_full_or_fuller_keeps_todays_fuel_charge():
    """The manual gives no fuel charge for a car back with as much fuel or more: today's step stands."""
    check_family("fuel_not_short")


def test_figures_left_to_todays_code_together():
    """Rentals under an hour and under a day, cars back fuller, in one file."""
    check_family("traps_combined")


def test_rule_1_3_limits_reached():
    """200 agreements; 60-day and one-day rentals; the years 2000 and 2099; every rate and reading at its ends."""
    rows = load("limits")
    assert len(rows[0]["agreements"]["agreements"]) == 200
    check_family("limits")


def relabel(row, rng):
    """The same file under a fresh branch and ids, agreements shuffled and every time moved by the same whole number
    of weeks within 2000-2099; the expected bills follow the same labels and order."""
    run, want = copy.deepcopy(row["agreements"]), copy.deepcopy(row["bills"])
    times = [datetime.strptime(a[k], FMT) for a in run["agreements"] for k in ("out", "in")]
    low, high = (datetime(2000, 1, 1) - min(times)).days // 7 + 1, (datetime(2099, 12, 25) - max(times)).days // 7
    shift = timedelta(weeks=rng.randint(low, high)) if low <= high else timedelta(0)
    ids = set()
    while len(ids) < len(run["agreements"]):
        ids.add("".join(rng.choice(CODE + "-") for _ in range(rng.randint(1, 10))))
    ids = sorted(ids)
    order = list(range(len(run["agreements"])))
    rng.shuffle(order)
    items, bills = [], []
    for index in order:
        a = dict(run["agreements"][index], id=ids[index])
        for k in ("out", "in"):
            a[k] = (datetime.strptime(a[k], FMT) + shift).strftime(FMT)
        items.append(a)
        bills.append(dict(want["bills"][index], id=ids[index]))
    branch = "RC3-" + "".join(rng.choice(CODE) for _ in range(8))
    return {"branch": branch, "agreements": items}, {"branch": branch, "bills": bills, "revenue": want["revenue"], "tax": want["tax"]}


def test_generated_agreement_files():
    """Seeded day rentals over the rest of the rule 1.3 domain, as sealed and under fresh labels."""
    check_family("generated")
    rng = random.Random(RELABEL_SEED)
    for row in load("generated"):
        run, expected = relabel(row, rng)
        within_limits(run)
        compare(bill_run(run), expected, f"generated {row['agreements']['branch']} relabelled (seed {RELABEL_SEED})")


def _unreadable_by_candidate(target):
    probe = f"import os,sys\ntry:\n    os.listdir({target!r}) if os.path.isdir({target!r}) else open({target!r}).read()\nexcept OSError:\n    sys.exit(0)\nsys.exit(1)"
    code, _, _ = run_as(CANDIDATE_UID, ["python3", "-I", "-S", "-c", probe], "/", 60)
    return code == 0


def test_candidate_cannot_read_verifier_state():
    """The candidate's user cannot read /tests, the expectations, the shipped copy or /logs/verifier."""
    for target in ["/tests", str(EXPECTED / "ROSTER"), str(SHIPPED_RUN), str(SHIPPED_RUN / "app" / "tools" / "rentcharge_run.py"), "/logs/verifier"]:
        assert _unreadable_by_candidate(target), f"the candidate's user can read {target}"
    control = Path(tempfile.mkdtemp()) / "control.txt"
    control.write_text("readable\n")
    os.chmod(control.parent, 0o755)
    os.chmod(control, 0o644)
    assert not _unreadable_by_candidate(str(control)), "control: the probe cannot read a world-readable file"


def test_submitted_driver_unchanged():
    """The delivered driver matches the shipped one, and is still the verifier's copy after every run."""
    assert DELIVERED_BYTES == SHIPPED_DRIVER.read_bytes(), "the delivered /app/tools/rentcharge_run.py differs from the shipped driver"
    assert DELIVERED_DRIVER.read_bytes() == SHIPPED_DRIVER.read_bytes(), "the driver on the documented path changed during the run"
    for path in [DELIVERED_DRIVER, DELIVERED_DRIVER.parent, DELIVERED_DRIVER.parent.parent]:
        info = path.lstat()
        assert info.st_uid == 0 and not info.st_mode & 0o022, f"{path} is writable by the candidate's user"
