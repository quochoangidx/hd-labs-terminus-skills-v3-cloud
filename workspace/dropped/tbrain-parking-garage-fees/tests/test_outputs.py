"""Verifier for the parkfee repair (garage tariff GT-2).

Before any candidate code runs, the delivered driver's bytes are recorded, the verifier's own copy
(tests/shipped/app/tools/parkfee_run.py) is os.replace-d onto /app/tools/parkfee_run.py, and all of /app is
made root-owned and unwritable by others. Every exits file is billed by the documented command,
python3 /app/tools/parkfee_run.py SESSIONS.json, as an unprivileged user in its own session with an isolated
interpreter, from a fresh directory, on a file with the same neutral name for every job. Expected statements were
written ahead of time by solution/seal.py from an independent model of the tariff and are read from
tests/expected/, whose SHA-256 sums and row counts are pinned in tests/expected/ROSTER.

One test per rule. Two figures are left by the tariff to today's code: the amount due (200 cents off a validated
ticket's fee, below nought where the fee is under 200) and the parking fee of a motorcycle past the car-and-van
maximum or inside the car-and-van grace period. A session carrying either appears only in the tests that grade it.
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
SHIPPED_DRIVER = SHIPPED_APP / "tools" / "parkfee_run.py"
DELIVERED_DRIVER = Path("/app/tools/parkfee_run.py")
CANDIDATE_UID = 65534
SHIPPED_UID = 65533
ENV = ["/usr/bin/env", "-i", "PATH=/usr/local/bin:/usr/bin:/bin", "HOME=/nonexistent", "LANG=C.UTF-8", "PYTHONDONTWRITEBYTECODE=1"]
DEADLINE = time.monotonic() + 1500
# Fresh labels for the relabelled generated files; printed in every failure message.
RELABEL_SEED = int.from_bytes(os.urandom(8), "big")
SESSION_KEYS = ("id", "hours", "fee", "due")
CODE = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
RATE = {"CAR": 300, "VAN": 450, "MOTO": 150}
# Figures left by the tariff to today's code that a family grades; a session carrying one appears only in a family
# that grades it.
GRADES = {"validated_credit": {"credit"}, "motorcycle": {"moto"}, "together": {"credit", "moto"}}


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
    staged = DELIVERED_DRIVER.with_name(".parkfee_run.verifier")
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


def run(sessions, shipped=False):
    """Run the driver on one exits file (the candidate's package, or the shipped copy); return its parsed stdout."""
    stage = tempfile.mkdtemp()
    work = tempfile.mkdtemp()
    os.chmod(stage, 0o755)
    os.chmod(work, 0o777)
    path = os.path.join(stage, "sessions.json")
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(sessions, handle)
    os.chmod(path, 0o644)
    remaining = DEADLINE - time.monotonic()
    assert remaining > 0, "verifier time budget exhausted"
    uid, driver = (SHIPPED_UID, str(SHIPPED_RUN / "app" / "tools" / "parkfee_run.py")) if shipped else (CANDIDATE_UID, str(DELIVERED_DRIVER))
    code, out, err = run_as(uid, ["python3", "-I", "-S", driver, path], work, remaining)
    shutil.rmtree(stage, ignore_errors=True)
    shutil.rmtree(work, ignore_errors=True)
    assert code == 0, f"driver exited {code}: {err[-2000:]}"
    return json.loads(out)


def silent(session):
    """The figures the tariff leaves to today's code that this session carries."""
    out = set()
    stay = session["exit"] - session["entry"]
    fee = 0 if stay <= 15 and session["vehicle"] != "MOTO" else -(-stay // 60) * RATE[session["vehicle"]]
    if session["validated"] and fee < 200:
        out.add("credit")
    if session["vehicle"] == "MOTO" and (fee > 2400 * -(-stay // 1440) or 0 < stay <= 15):
        out.add("moto")
    return out


def within_limits(e):
    """Rule 1.2, every limit including its ends: each graded file must keep to it."""
    items = e["sessions"]
    assert isinstance(e["garage"], str) and 1 <= len(items) <= 200
    assert len({x["id"] for x in items}) == len(items)
    for x in items:
        assert 1 <= len(x["id"]) <= 10 and set(x["id"]) <= set(CODE)
        assert x["vehicle"] in ("CAR", "VAN", "MOTO")
        assert type(x["entry"]) is int and 0 <= x["entry"] <= 100000
        assert type(x["exit"]) is int and 0 <= x["exit"] - x["entry"] <= 10080
        assert type(x["validated"]) is bool


def load(name):
    """Rows of one family; fails when the file, its digest or its count differ from the roster, or a file breaks
    rule 1.2 or carries a session with a figure left to today's code into a family that does not grade it."""
    file, digest, count = ROSTER[name]
    raw = (EXPECTED / file).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == digest, f"{name} does not match the roster"
    rows = [json.loads(line) for line in raw.decode().splitlines() if line]
    assert len(rows) == count, f"{name}: {len(rows)} rows, roster says {count}"
    for row in rows:
        within_limits(row["sessions"])
        for x in row["sessions"]["sessions"]:
            assert silent(x) <= GRADES.get(name, set()), f"{name}: {row['sessions']['garage']} session {x['id']} is not graded here"
    return rows


def _same(actual, expected, where):
    assert type(actual) is type(expected) and actual == expected, f"{where}: {actual!r}, expected {expected!r}"


def compare(actual, expected, label):
    """Every key the README lists, as a JSON integer or string; further keys are ignored."""
    assert isinstance(actual, dict) and set(actual) >= {"garage", "sessions", "total"}, f"{label}: top-level keys"
    _same(actual["garage"], expected["garage"], f"{label} garage")
    _same(actual["total"], expected["total"], f"{label} total")
    got, want = actual["sessions"], expected["sessions"]
    assert isinstance(got, list) and len(got) == len(want), f"{label}: {len(got) if isinstance(got, list) else got!r} sessions, expected {len(want)}"
    for index, (row, ref) in enumerate(zip(got, want)):
        assert isinstance(row, dict) and set(row) >= set(SESSION_KEYS), f"{label} sessions[{index}]: keys {row!r}"
        for key in SESSION_KEYS:
            _same(row[key], ref[key], f"{label} sessions[{index}] ({ref['id']}) {key}")


def check_family(name):
    for row in load(name):
        compare(run(row["sessions"]), row["statement"], f"{name} {row['sessions']['garage']}")


def test_rule_2_2_grace_period_and_hours():
    """0, 15 and 16 minutes; 60 and 61 minutes charged 1 and 2 hours."""
    check_family("grace")


def test_rule_3_1_hourly_rates():
    """Car 300, van 450, motorcycle 150 cents an hour."""
    check_family("rates")


def test_rule_3_3_car_and_van_maximum():
    """2,400 cents for each 24 hours begun; stays exactly on a day and a minute past it."""
    check_family("maximum")


def test_total_and_session_order():
    """Every amount due and the total, sessions in file order, ids of one to ten characters."""
    check_family("order_and_total")


def test_validated_ticket_keeps_todays_amount_due():
    """The tariff gives no rule for the amount due: 200 cents off a validated ticket's fee, below nought too."""
    check_family("validated_credit")


def test_motorcycle_keeps_todays_uncapped_fee():
    """The tariff gives no grace period and no maximum for a motorcycle: today's step stands."""
    check_family("motorcycle")


def test_figures_left_to_todays_code_together():
    """Validated tickets below nought and motorcycles past the maximum, beside cars and vans."""
    check_family("together")


def test_rule_1_2_limits_reached():
    """200 sessions; entry minutes 0 and 100,000; stays of 0 and 10,080 minutes."""
    assert len(load("limits")[0]["sessions"]["sessions"]) == 200
    check_family("limits")


def relabel(row, rng):
    """The same file under a fresh name and ids, sessions shuffled and moved in time; the statement follows."""
    e, want = copy.deepcopy(row["sessions"]), copy.deepcopy(row["statement"])
    ids = set()
    while len(ids) < len(e["sessions"]):
        ids.add("".join(rng.choice(CODE) for _ in range(rng.randint(1, 10))))
    ids = sorted(ids)
    order = list(range(len(e["sessions"])))
    rng.shuffle(order)
    name = "GT2-" + "".join(rng.choice(CODE) for _ in range(8))
    items = []
    for i in order:
        x = e["sessions"][i]
        start = rng.randint(0, 100000)
        items.append(dict(x, id=ids[i], entry=start, exit=start + x["exit"] - x["entry"]))
    lines = [dict(want["sessions"][i], id=ids[i]) for i in order]
    return {"garage": name, "sessions": items}, {"garage": name, "sessions": lines, "total": want["total"]}


def test_generated_exits_files():
    """Seeded files of cars and vans, as sealed and under fresh labels."""
    check_family("generated")
    rng = random.Random(RELABEL_SEED)
    for row in load("generated"):
        e, expected = relabel(row, rng)
        within_limits(e)
        compare(run(e), expected, f"generated {row['sessions']['garage']} relabelled (seed {RELABEL_SEED})")


def _unreadable_by_candidate(target):
    probe = f"import os,sys\ntry:\n    os.listdir({target!r}) if os.path.isdir({target!r}) else open({target!r}).read()\nexcept OSError:\n    sys.exit(0)\nsys.exit(1)"
    code, _, _ = run_as(CANDIDATE_UID, ["python3", "-I", "-S", "-c", probe], "/", 60)
    return code == 0


def test_candidate_cannot_read_verifier_state():
    """The candidate's user cannot read /tests, the expectations, the shipped copy or /logs/verifier."""
    for target in ["/tests", str(EXPECTED / "ROSTER"), str(SHIPPED_RUN), str(SHIPPED_RUN / "app" / "tools" / "parkfee_run.py"), "/logs/verifier"]:
        assert _unreadable_by_candidate(target), f"the candidate's user can read {target}"
    control = Path(tempfile.mkdtemp()) / "control.txt"
    control.write_text("readable\n")
    os.chmod(control.parent, 0o755)
    os.chmod(control, 0o644)
    assert not _unreadable_by_candidate(str(control)), "control: the probe cannot read a world-readable file"


def test_submitted_driver_unchanged():
    """The delivered driver matches the shipped one, and is still the verifier's copy after every run."""
    assert DELIVERED_BYTES == SHIPPED_DRIVER.read_bytes(), "the delivered /app/tools/parkfee_run.py differs from the shipped driver"
    assert DELIVERED_DRIVER.read_bytes() == SHIPPED_DRIVER.read_bytes(), "the driver on the documented path changed during the run"
    for path in [DELIVERED_DRIVER, DELIVERED_DRIVER.parent, DELIVERED_DRIVER.parent.parent]:
        info = path.lstat()
        assert info.st_uid == 0 and not info.st_mode & 0o022, f"{path} is writable by the candidate's user"
