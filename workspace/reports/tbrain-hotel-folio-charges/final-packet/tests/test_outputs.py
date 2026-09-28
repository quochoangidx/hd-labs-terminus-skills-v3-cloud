"""Verifier for the folio repair (folio charges rules FC-3).

Before any candidate code runs, the delivered driver's bytes are recorded, the verifier's own copy
(tests/shipped/app/tools/folio_run.py) is os.replace-d onto /app/tools/folio_run.py, and all of /app is
made root-owned and unwritable by others. Every night audit file is billed by the documented command,
python3 /app/tools/folio_run.py STAYS.json, as an unprivileged user in its own session with an isolated
interpreter, from a fresh directory, on a file with the same neutral name for every job. Expected statements were
written ahead of time by solution/seal.py from an independent model of the rules and are read from
tests/expected/, whose SHA-256 sums and row counts are pinned in tests/expected/ROSTER.

One test per rule. Two figures are left by the rules to today's code: the city tax of a room under 5,000 cents a
night, and the service fee, whose rate and rounding the rules do not give. A room under 5,000 cents a night appears
only in the test that grades its city tax. Only a fee that lands exactly on a half cent tells today's rounding
from another; such a stay's service fee, its folio total and its file's total are compared only in the test that
grades the service fee.
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
SHIPPED_DRIVER = SHIPPED_APP / "tools" / "folio_run.py"
DELIVERED_DRIVER = Path("/app/tools/folio_run.py")
CANDIDATE_UID = 65534
SHIPPED_UID = 65533
ENV = ["/usr/bin/env", "-i", "PATH=/usr/local/bin:/usr/bin:/bin", "HOME=/nonexistent", "LANG=C.UTF-8", "PYTHONDONTWRITEBYTECODE=1"]
DEADLINE = time.monotonic() + 1500
# Fresh labels for the relabelled generated files; printed in every failure message.
RELABEL_SEED = int.from_bytes(os.urandom(8), "big")
FOLIO_KEYS = ("id", "room", "occupancy_tax", "city_tax", "service_fee", "total")
CODE = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"

# Families that grade the service fee of a stay whose fee lands on a half cent.
GRADES = {"service_fee": {"half_fee"}, "city_tax_cheap": {"cheap"}}


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
    staged = DELIVERED_DRIVER.with_name(".folio_run.verifier")
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


def run(stays, shipped=False):
    """Run the driver on one night audit file (the candidate's package, or the shipped copy); return its parsed stdout."""
    stage = tempfile.mkdtemp()
    work = tempfile.mkdtemp()
    os.chmod(stage, 0o755)
    os.chmod(work, 0o777)
    path = os.path.join(stage, "stays.json")
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(stays, handle)
    os.chmod(path, 0o644)
    remaining = DEADLINE - time.monotonic()
    assert remaining > 0, "verifier time budget exhausted"
    uid, driver = (SHIPPED_UID, str(SHIPPED_RUN / "app" / "tools" / "folio_run.py")) if shipped else (CANDIDATE_UID, str(DELIVERED_DRIVER))
    code, out, err = run_as(uid, ["python3", "-I", "-S", driver, path], work, remaining)
    shutil.rmtree(stage, ignore_errors=True)
    shutil.rmtree(work, ignore_errors=True)
    assert code == 0, f"driver exited {code}: {err[-2000:]}"
    return json.loads(out)


def half_fee(stay):
    """True when the stay's service fee lands exactly on a half cent under rules 2.1 and today's 3.5 per cent."""
    nights, rate = stay["nights"], stay["rate"]
    return ((nights - nights // 7) * rate * 35) % 1000 == 500


def within_limits(a):
    """Rule 1.2, every limit including its ends: each graded file must keep to it."""
    items = a["stays"]
    assert isinstance(a["audit"], str) and 1 <= len(items) <= 200
    assert len({x["id"] for x in items}) == len(items)
    for x in items:
        assert 1 <= len(x["id"]) <= 10 and set(x["id"]) <= set(CODE)
        assert type(x["nights"]) is int and 1 <= x["nights"] <= 60
        assert type(x["rate"]) is int and 1000 <= x["rate"] <= 150000


def load(name):
    """Rows of one family; fails when the file, its digest or its count differ from the roster, or a file breaks
    rule 1.2 or puts a room under 5,000 cents a night in a family that does not grade it."""
    file, digest, count = ROSTER[name]
    raw = (EXPECTED / file).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == digest, f"{name} does not match the roster"
    rows = [json.loads(line) for line in raw.decode().splitlines() if line]
    assert len(rows) == count, f"{name}: {len(rows)} rows, roster says {count}"
    for row in rows:
        within_limits(row["stays"])
        cheap = any(x["rate"] < 5000 for x in row["stays"]["stays"])
        assert not cheap or "cheap" in GRADES.get(name, set()), f"{name}: {row['stays']['audit']} has a room under 5,000 cents a night"
    return rows


def _same(actual, expected, where):
    assert type(actual) is type(expected) and actual == expected, f"{where}: {actual!r}, expected {expected!r}"


def compare(actual, expected, stays, label, grades=frozenset()):
    """Every key the README lists, as a JSON integer or string; further keys are ignored. For a stay whose service
    fee lands on a half cent, the fee, the folio total and the file total are compared only where ``grades`` holds
    "half_fee"."""
    assert isinstance(actual, dict) and set(actual) >= {"audit", "folios", "total"}, f"{label}: top-level keys"
    _same(actual["audit"], expected["audit"], f"{label} audit")
    skipped = {i for i, x in enumerate(stays) if half_fee(x)} if "half_fee" not in grades else set()
    if not skipped:
        _same(actual["total"], expected["total"], f"{label} total")
    got, want = actual["folios"], expected["folios"]
    assert isinstance(got, list) and len(got) == len(want), f"{label}: {len(got) if isinstance(got, list) else got!r} folios, expected {len(want)}"
    for index, (row, ref) in enumerate(zip(got, want)):
        assert isinstance(row, dict) and set(row) >= set(FOLIO_KEYS), f"{label} folios[{index}]: keys {row!r}"
        for key in FOLIO_KEYS:
            if index in skipped and key in ("service_fee", "total"):
                continue
            _same(row[key], ref[key], f"{label} folios[{index}] ({ref['id']}) {key}")


def check_family(name):
    grades = GRADES.get(name, frozenset())
    for row in load(name):
        compare(run(row["stays"]), row["folios"], row["stays"]["stays"], f"{name} {row['stays']['audit']}", grades)


def test_rule_2_1_every_seventh_night_free():
    """Stays of 1, 6, 7, 8, 13, 14, 15 and 60 nights."""
    check_family("free_nights")


def test_rule_2_2_city_tax_for_at_most_fourteen_nights():
    """250 cents a night, stopping after the fourteenth night."""
    check_family("city_tax")


def test_rule_2_3_occupancy_tax_half_cent_up():
    """13.5 per cent of the room charge, an exact half cent going up."""
    check_family("occupancy_tax")


def test_rule_2_5_totals_and_folio_order():
    """Every folio total and the file total, folios in file order, ids of one to ten characters."""
    check_family("order_and_total")


def test_service_fee_keeps_todays_step():
    """The rules give no rate or rounding for the service fee: today's step stands, half cents included."""
    check_family("service_fee")


def test_room_under_5000_keeps_todays_city_tax():
    """The rules give no city tax for a room under 5,000 cents a night: today's step stands."""
    check_family("city_tax_cheap")


def test_rule_1_2_limits_reached():
    """200 stays; 1 and 60 nights; rates of 5,000 and 150,000 cents."""
    assert len(load("limits")[0]["stays"]["stays"]) == 200
    check_family("limits")


def relabel(row, rng):
    """The same file under a fresh name and ids, stays shuffled; the folios follow."""
    a, want = copy.deepcopy(row["stays"]), copy.deepcopy(row["folios"])
    ids = set()
    while len(ids) < len(a["stays"]):
        ids.add("".join(rng.choice(CODE) for _ in range(rng.randint(1, 10))))
    ids = sorted(ids)
    order = list(range(len(a["stays"])))
    rng.shuffle(order)
    name = "FC3-" + "".join(rng.choice(CODE) for _ in range(8))
    items = [dict(a["stays"][i], id=ids[i]) for i in order]
    folios = [dict(want["folios"][i], id=ids[i]) for i in order]
    return {"audit": name, "stays": items}, {"audit": name, "folios": folios, "total": want["total"]}


def test_generated_night_audits():
    """Seeded files of rooms at 5,000 cents a night or more, as sealed and under fresh labels."""
    check_family("generated")
    rng = random.Random(RELABEL_SEED)
    for row in load("generated"):
        a, expected = relabel(row, rng)
        within_limits(a)
        compare(run(a), expected, a["stays"], f"generated {row['stays']['audit']} relabelled (seed {RELABEL_SEED})")


def _unreadable_by_candidate(target):
    probe = f"import os,sys\ntry:\n    os.listdir({target!r}) if os.path.isdir({target!r}) else open({target!r}).read()\nexcept OSError:\n    sys.exit(0)\nsys.exit(1)"
    code, _, _ = run_as(CANDIDATE_UID, ["python3", "-I", "-S", "-c", probe], "/", 60)
    return code == 0


def test_candidate_cannot_read_verifier_state():
    """The candidate's user cannot read /tests, the expectations, the shipped copy or /logs/verifier."""
    for target in ["/tests", str(EXPECTED / "ROSTER"), str(SHIPPED_RUN), str(SHIPPED_RUN / "app" / "tools" / "folio_run.py"), "/logs/verifier"]:
        assert _unreadable_by_candidate(target), f"the candidate's user can read {target}"
    control = Path(tempfile.mkdtemp()) / "control.txt"
    control.write_text("readable\n")
    os.chmod(control.parent, 0o755)
    os.chmod(control, 0o644)
    assert not _unreadable_by_candidate(str(control)), "control: the probe cannot read a world-readable file"


def test_submitted_driver_unchanged():
    """The delivered driver matches the shipped one, and is still the verifier's copy after every run."""
    assert DELIVERED_BYTES == SHIPPED_DRIVER.read_bytes(), "the delivered /app/tools/folio_run.py differs from the shipped driver"
    assert DELIVERED_DRIVER.read_bytes() == SHIPPED_DRIVER.read_bytes(), "the driver on the documented path changed during the run"
    for path in [DELIVERED_DRIVER, DELIVERED_DRIVER.parent, DELIVERED_DRIVER.parent.parent]:
        info = path.lstat()
        assert info.st_uid == 0 and not info.st_mode & 0o022, f"{path} is writable by the candidate's user"
