"""Verifier for the demurrage repair (demurrage tariff DM-3).

Before any candidate code runs, the delivered driver's bytes are recorded, the verifier's own copy
(tests/shipped/app/tools/demurrage_run.py) is os.replace-d onto /app/tools/demurrage_run.py, and all of /app is
made root-owned and unwritable by others. Every release file is billed by the documented command,
python3 /app/tools/demurrage_run.py RELEASES.json, as an unprivileged user in its own session with an isolated
interpreter, from a fresh directory, on a file with the same neutral name for every job. Expected statements were
written ahead of time by solution/seal.py from an independent model of the tariff and are read from
tests/expected/, whose SHA-256 sums and row counts are pinned in tests/expected/ROSTER.

One test per rule. Two figures are left by the tariff to today's code: the free days of a tank container, and the
demurrage days and charge of a container that is not on demurrage. A container carrying either appears only in the
tests that grade it.
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
SHIPPED_DRIVER = SHIPPED_APP / "tools" / "demurrage_run.py"
DELIVERED_DRIVER = Path("/app/tools/demurrage_run.py")
CANDIDATE_UID = 65534
SHIPPED_UID = 65533
ENV = ["/usr/bin/env", "-i", "PATH=/usr/local/bin:/usr/bin:/bin", "HOME=/nonexistent", "LANG=C.UTF-8", "PYTHONDONTWRITEBYTECODE=1"]
DEADLINE = time.monotonic() + 1500
# Fresh labels for the relabelled generated files; printed in every failure message.
RELABEL_SEED = int.from_bytes(os.urandom(8), "big")
CONTAINER_KEYS = ("id", "dwell", "free", "days", "charge")
CODE = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
FREE = {"DRY": 5, "REEFER": 3}
# Figures left by the tariff to today's code that a family grades; a container carrying one appears only in a
# family that grades it.
GRADES = {"tank": {"tank"}, "not_on_demurrage": {"idle"}, "together": {"tank", "idle"}}


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
    staged = DELIVERED_DRIVER.with_name(".demurrage_run.verifier")
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


def run(release, shipped=False):
    """Run the driver on one release file (the candidate's package, or the shipped copy); return its parsed stdout."""
    stage = tempfile.mkdtemp()
    work = tempfile.mkdtemp()
    os.chmod(stage, 0o755)
    os.chmod(work, 0o777)
    path = os.path.join(stage, "release.json")
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(release, handle)
    os.chmod(path, 0o644)
    remaining = DEADLINE - time.monotonic()
    assert remaining > 0, "verifier time budget exhausted"
    uid, driver = (SHIPPED_UID, str(SHIPPED_RUN / "app" / "tools" / "demurrage_run.py")) if shipped else (CANDIDATE_UID, str(DELIVERED_DRIVER))
    code, out, err = run_as(uid, ["python3", "-I", "-S", driver, path], work, remaining)
    shutil.rmtree(stage, ignore_errors=True)
    shutil.rmtree(work, ignore_errors=True)
    assert code == 0, f"driver exited {code}: {err[-2000:]}"
    return json.loads(out)


def silent(box):
    """The figures the tariff leaves to today's code that this container carries."""
    out = set()
    if box["type"] not in FREE:
        out.add("tank")
    if box["picked_up"] - box["discharged"] + 1 <= FREE.get(box["type"], 5):
        out.add("idle")
    return out


def within_limits(r):
    """Rule 1.2, every limit including its ends: each graded file must keep to it."""
    boxes = r["containers"]
    assert isinstance(r["terminal"], str) and 1 <= len(boxes) <= 200
    assert len({x["id"] for x in boxes}) == len(boxes)
    for x in boxes:
        assert 1 <= len(x["id"]) <= 11 and set(x["id"]) <= set(CODE)
        assert x["type"] in ("DRY", "REEFER", "TANK")
        assert type(x["discharged"]) is int and 0 <= x["discharged"] <= 3650
        assert type(x["picked_up"]) is int and 0 <= x["picked_up"] - x["discharged"] <= 120
        assert type(x["rate"]) is int and 1 <= x["rate"] <= 100000


def load(name):
    """Rows of one family; fails when the file, its digest or its count differ from the roster, or a file breaks
    rule 1.2 or carries a container with a figure left to today's code into a family that does not grade it."""
    file, digest, count = ROSTER[name]
    raw = (EXPECTED / file).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == digest, f"{name} does not match the roster"
    rows = [json.loads(line) for line in raw.decode().splitlines() if line]
    assert len(rows) == count, f"{name}: {len(rows)} rows, roster says {count}"
    for row in rows:
        within_limits(row["release"])
        for x in row["release"]["containers"]:
            assert silent(x) <= GRADES.get(name, set()), f"{name}: {row['release']['terminal']} container {x['id']} is not graded here"
    return rows


def _same(actual, expected, where):
    assert type(actual) is type(expected) and actual == expected, f"{where}: {actual!r}, expected {expected!r}"


def compare(actual, expected, label):
    """Every key the README lists, as a JSON integer or string; further keys are ignored."""
    assert isinstance(actual, dict) and set(actual) >= {"terminal", "containers", "total"}, f"{label}: top-level keys"
    _same(actual["terminal"], expected["terminal"], f"{label} terminal")
    _same(actual["total"], expected["total"], f"{label} total")
    got, want = actual["containers"], expected["containers"]
    assert isinstance(got, list) and len(got) == len(want), f"{label}: {len(got) if isinstance(got, list) else got!r} containers, expected {len(want)}"
    for index, (row, ref) in enumerate(zip(got, want)):
        assert isinstance(row, dict) and set(row) >= set(CONTAINER_KEYS), f"{label} containers[{index}]: keys {row!r}"
        for key in CONTAINER_KEYS:
            _same(row[key], ref[key], f"{label} containers[{index}] ({ref['id']}) {key}")


def check_family(name):
    for row in load(name):
        compare(run(row["release"]), row["statement"], f"{name} {row['release']['terminal']}")


def test_rule_2_1_dwell_counts_both_ends():
    """The discharge day, the pickup day and every day between."""
    check_family("dwell")


def test_rule_2_2_reefer_free_days():
    """A reefer has 3 free days and a dry box 5; on the edge and one past."""
    check_family("reefer")


def test_rule_3_1_twice_the_rate_after_the_fourth_day():
    """The rate for each of the first 4 demurrage days, twice the rate for each day after."""
    check_family("higher_rate")


def test_rule_3_2_total_and_container_order():
    """Every charge and the total, containers in file order, ids of one to eleven characters."""
    check_family("order_and_total")


def test_tank_container_keeps_todays_free_days():
    """The tariff gives no free days for a tank container: today's step stands."""
    check_family("tank")


def test_container_not_on_demurrage_keeps_todays_days_and_charge():
    """The tariff gives no demurrage days or charge for a container inside its free time: today's step stands."""
    check_family("not_on_demurrage")


def test_figures_left_to_todays_code_together():
    """Tanks inside and past their free time, beside dry and reefer boxes."""
    check_family("together")


def test_rule_1_2_limits_reached():
    """200 containers; discharge days 0 and 3,650; stays of 1 and 121 days; rates 1 and 100,000."""
    assert len(load("limits")[0]["release"]["containers"]) == 200
    check_family("limits")


def relabel(row, rng):
    """The same file under a fresh name and ids, containers shuffled and moved in time; the statement follows."""
    r, want = copy.deepcopy(row["release"]), copy.deepcopy(row["statement"])
    ids = set()
    while len(ids) < len(r["containers"]):
        ids.add("".join(rng.choice(CODE) for _ in range(rng.randint(1, 11))))
    ids = sorted(ids)
    order = list(range(len(r["containers"])))
    rng.shuffle(order)
    name = "DM3-" + "".join(rng.choice(CODE) for _ in range(8))
    boxes = []
    for i in order:
        x = r["containers"][i]
        start = rng.randint(0, 3650)
        boxes.append(dict(x, id=ids[i], discharged=start, picked_up=start + x["picked_up"] - x["discharged"]))
    lines = [dict(want["containers"][i], id=ids[i]) for i in order]
    return {"terminal": name, "containers": boxes}, {"terminal": name, "containers": lines, "total": want["total"]}


def test_generated_release_files():
    """Seeded files of dry and reefer containers on demurrage, as sealed and under fresh labels."""
    check_family("generated")
    rng = random.Random(RELABEL_SEED)
    for row in load("generated"):
        r, expected = relabel(row, rng)
        within_limits(r)
        compare(run(r), expected, f"generated {row['release']['terminal']} relabelled (seed {RELABEL_SEED})")


def _unreadable_by_candidate(target):
    probe = f"import os,sys\ntry:\n    os.listdir({target!r}) if os.path.isdir({target!r}) else open({target!r}).read()\nexcept OSError:\n    sys.exit(0)\nsys.exit(1)"
    code, _, _ = run_as(CANDIDATE_UID, ["python3", "-I", "-S", "-c", probe], "/", 60)
    return code == 0


def test_candidate_cannot_read_verifier_state():
    """The candidate's user cannot read /tests, the expectations, the shipped copy or /logs/verifier."""
    for target in ["/tests", str(EXPECTED / "ROSTER"), str(SHIPPED_RUN), str(SHIPPED_RUN / "app" / "tools" / "demurrage_run.py"), "/logs/verifier"]:
        assert _unreadable_by_candidate(target), f"the candidate's user can read {target}"
    control = Path(tempfile.mkdtemp()) / "control.txt"
    control.write_text("readable\n")
    os.chmod(control.parent, 0o755)
    os.chmod(control, 0o644)
    assert not _unreadable_by_candidate(str(control)), "control: the probe cannot read a world-readable file"


def test_submitted_driver_unchanged():
    """The delivered driver matches the shipped one, and is still the verifier's copy after every run."""
    assert DELIVERED_BYTES == SHIPPED_DRIVER.read_bytes(), "the delivered /app/tools/demurrage_run.py differs from the shipped driver"
    assert DELIVERED_DRIVER.read_bytes() == SHIPPED_DRIVER.read_bytes(), "the driver on the documented path changed during the run"
    for path in [DELIVERED_DRIVER, DELIVERED_DRIVER.parent, DELIVERED_DRIVER.parent.parent]:
        info = path.lstat()
        assert info.st_uid == 0 and not info.st_mode & 0o022, f"{path} is writable by the candidate's user"
