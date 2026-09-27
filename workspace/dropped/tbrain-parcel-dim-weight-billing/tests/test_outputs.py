"""Verifier for the parcelbill repair (parcel billing rules PB-4).

Before any candidate code runs, the delivered driver's bytes are recorded, the verifier's own copy
(tests/shipped/app/tools/parcelbill_run.py) is os.replace-d onto /app/tools/parcelbill_run.py, and all of /app is
made root-owned and unwritable by others. Every manifest is billed by the documented command,
python3 /app/tools/parcelbill_run.py MANIFEST.json, as an unprivileged user in its own session with an isolated
interpreter, from a fresh directory, on a file with the same neutral name for every job. Expected invoices were
written ahead of time by solution/seal.py from an independent model of the rules and are read from
tests/expected/, whose SHA-256 sums and row counts are pinned in tests/expected/ROSTER.

One test per rule. Three figures are left by the rules to today's code: the dimensional divisor of a parcel that
is not a box, the residential surcharge of an express parcel going to a home, and the fuel surcharge of an express
parcel. A parcel carrying any of them appears only in the tests that grade it.
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
SHIPPED_DRIVER = SHIPPED_APP / "tools" / "parcelbill_run.py"
DELIVERED_DRIVER = Path("/app/tools/parcelbill_run.py")
CANDIDATE_UID = 65534
SHIPPED_UID = 65533
ENV = ["/usr/bin/env", "-i", "PATH=/usr/local/bin:/usr/bin:/bin", "HOME=/nonexistent", "LANG=C.UTF-8", "PYTHONDONTWRITEBYTECODE=1"]
DEADLINE = time.monotonic() + 1500
# Fresh labels for the relabelled generated files; printed in every failure message.
RELABEL_SEED = int.from_bytes(os.urandom(8), "big")
PARCEL_KEYS = ("id", "billable", "transport", "residential", "fuel", "total")
CODE = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-"
# Figures left by the rules to today's code that a family grades; a parcel carrying one appears only in a family
# that grades it.
GRADES = {"not_a_box": {"not_box"}, "express_fuel": {"express"}, "express_home": {"express", "express_home"},
          "together": {"not_box", "express", "express_home"}}


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
    staged = DELIVERED_DRIVER.with_name(".parcelbill_run.verifier")
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


def invoice(manifest, shipped=False):
    """Run the driver on one manifest (the candidate's package, or the shipped copy); return its parsed stdout."""
    stage = tempfile.mkdtemp()
    work = tempfile.mkdtemp()
    os.chmod(stage, 0o755)
    os.chmod(work, 0o777)
    path = os.path.join(stage, "manifest.json")
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(manifest, handle)
    os.chmod(path, 0o644)
    remaining = DEADLINE - time.monotonic()
    assert remaining > 0, "verifier time budget exhausted"
    uid, driver = (SHIPPED_UID, str(SHIPPED_RUN / "app" / "tools" / "parcelbill_run.py")) if shipped else (CANDIDATE_UID, str(DELIVERED_DRIVER))
    code, out, err = run_as(uid, ["python3", "-I", "-S", driver, path], work, remaining)
    shutil.rmtree(stage, ignore_errors=True)
    shutil.rmtree(work, ignore_errors=True)
    assert code == 0, f"driver exited {code}: {err[-2000:]}"
    return json.loads(out)


def silent(parcel):
    """The figures the rules leave to today's code that this parcel carries."""
    out = set()
    if min(parcel["sides"]) < 2:
        out.add("not_box")
    if parcel["service"] == "EXPRESS":
        out.add("express")
        if parcel["residential"]:
            out.add("express_home")
    return out


def within_limits(m):
    """Rule 1.3, every limit including its ends: each graded manifest must keep to it."""
    parcels = m["parcels"]
    assert isinstance(m["manifest"], str) and 1 <= len(parcels) <= 300
    assert len({x["id"] for x in parcels}) == len(parcels)
    for x in parcels:
        assert 1 <= len(x["id"]) <= 12 and set(x["id"]) <= set(CODE)
        assert len(x["sides"]) == 3 and all(type(s) is int and 1 <= s <= 108 for s in x["sides"])
        assert type(x["weight"]) is int and 1 <= x["weight"] <= 1500
        assert x["service"] in ("GROUND", "EXPRESS") and type(x["zone"]) is int and 2 <= x["zone"] <= 8
        assert type(x["residential"]) is bool


def load(name):
    """Rows of one family; fails when the file, its digest or its count differ from the roster, or a manifest breaks
    rule 1.3 or carries a parcel with a figure left to today's code into a family that does not grade it."""
    file, digest, count = ROSTER[name]
    raw = (EXPECTED / file).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == digest, f"{name} does not match the roster"
    rows = [json.loads(line) for line in raw.decode().splitlines() if line]
    assert len(rows) == count, f"{name}: {len(rows)} rows, roster says {count}"
    for row in rows:
        within_limits(row["manifest"])
        for x in row["manifest"]["parcels"]:
            assert silent(x) <= GRADES.get(name, set()), f"{name}: {row['manifest']['manifest']} parcel {x['id']} is not graded here"
    return rows


def _same(actual, expected, where):
    assert type(actual) is type(expected) and actual == expected, f"{where}: {actual!r}, expected {expected!r}"


def compare(actual, expected, label):
    """Every key the README lists, as a JSON integer or string; further keys are ignored."""
    assert isinstance(actual, dict) and set(actual) >= {"manifest", "parcels", "total"}, f"{label}: top-level keys"
    _same(actual["manifest"], expected["manifest"], f"{label} manifest")
    _same(actual["total"], expected["total"], f"{label} total")
    got, want = actual["parcels"], expected["parcels"]
    assert isinstance(got, list) and len(got) == len(want), f"{label}: {len(got) if isinstance(got, list) else got!r} parcels, expected {len(want)}"
    for index, (row, ref) in enumerate(zip(got, want)):
        assert isinstance(row, dict) and set(row) >= set(PARCEL_KEYS), f"{label} parcels[{index}]: keys {row!r}"
        for key in PARCEL_KEYS:
            _same(row[key], ref[key], f"{label} parcels[{index}] ({ref['id']}) {key}")


def check_family(name):
    for row in load(name):
        compare(invoice(row["manifest"]), row["invoice"], f"{name} {row['manifest']['manifest']}")


def test_rule_2_2_box_divisor():
    """A box's dimensional weight is its volume over 139; sides in any order, smallest and largest boxes."""
    check_family("box_divisor")


def test_rule_2_3_billable_weight_rounded_up():
    """The larger weight rounded up to the next whole pound; a whole pound stays."""
    check_family("rounding_up")


def test_rule_3_2_ground_parcel_to_a_home():
    """A ground parcel going to a home carries 530 cents; a business delivery carries none."""
    check_family("ground_home")


def test_rule_3_3_fuel_on_transport_and_residential():
    """A ground parcel's fuel: 14.25 per cent of transport and residential together, an exact half cent going up."""
    check_family("fuel")


def test_rule_3_4_totals_and_parcel_order():
    """Every parcel's total and the manifest total, parcels in manifest order, ids of one to twelve characters."""
    check_family("order_and_totals")


def test_parcel_that_is_not_a_box_keeps_todays_divisor():
    """The rules give no divisor for a parcel with a side under 2 inches: today's step stands."""
    check_family("not_a_box")


def test_express_parcel_keeps_todays_fuel_surcharge():
    """The rules give no fuel rule for an express parcel: today's step stands."""
    check_family("express_fuel")


def test_express_parcel_to_a_home_keeps_todays_surcharge():
    """The rules give no residential amount for an express parcel going to a home: today's step stands."""
    check_family("express_home")


def test_figures_left_to_todays_code_together():
    """Parcels that are not boxes and express parcels, some going to homes, beside ground boxes."""
    check_family("together")


def test_rule_1_3_limits_reached():
    """300 ground parcels; sides of 2 and 108 inches; weights of 1 and 1,500 tenths; every zone."""
    assert len(load("limits")[0]["manifest"]["parcels"]) == 300
    check_family("limits")


def relabel(row, rng):
    """The same manifest under a fresh name and ids, parcels shuffled and sides reordered; the invoice follows."""
    m, want = copy.deepcopy(row["manifest"]), copy.deepcopy(row["invoice"])
    ids = set()
    while len(ids) < len(m["parcels"]):
        ids.add("".join(rng.choice(CODE) for _ in range(rng.randint(1, 12))))
    ids = sorted(ids)
    order = list(range(len(m["parcels"])))
    rng.shuffle(order)
    name = "PB4-" + "".join(rng.choice(CODE[:36]) for _ in range(8))
    parcels = [dict(m["parcels"][i], id=ids[i], sides=rng.sample(m["parcels"][i]["sides"], 3)) for i in order]
    lines = [dict(want["parcels"][i], id=ids[i]) for i in order]
    return {"manifest": name, "parcels": parcels}, {"manifest": name, "parcels": lines, "total": want["total"]}


def test_generated_manifests():
    """Seeded manifests of ground boxes, as sealed and under fresh labels."""
    check_family("generated")
    rng = random.Random(RELABEL_SEED)
    for row in load("generated"):
        m, expected = relabel(row, rng)
        within_limits(m)
        compare(invoice(m), expected, f"generated {row['manifest']['manifest']} relabelled (seed {RELABEL_SEED})")


def _unreadable_by_candidate(target):
    probe = f"import os,sys\ntry:\n    os.listdir({target!r}) if os.path.isdir({target!r}) else open({target!r}).read()\nexcept OSError:\n    sys.exit(0)\nsys.exit(1)"
    code, _, _ = run_as(CANDIDATE_UID, ["python3", "-I", "-S", "-c", probe], "/", 60)
    return code == 0


def test_candidate_cannot_read_verifier_state():
    """The candidate's user cannot read /tests, the expectations, the shipped copy or /logs/verifier."""
    for target in ["/tests", str(EXPECTED / "ROSTER"), str(SHIPPED_RUN), str(SHIPPED_RUN / "app" / "tools" / "parcelbill_run.py"), "/logs/verifier"]:
        assert _unreadable_by_candidate(target), f"the candidate's user can read {target}"
    control = Path(tempfile.mkdtemp()) / "control.txt"
    control.write_text("readable\n")
    os.chmod(control.parent, 0o755)
    os.chmod(control, 0o644)
    assert not _unreadable_by_candidate(str(control)), "control: the probe cannot read a world-readable file"


def test_submitted_driver_unchanged():
    """The delivered driver matches the shipped one, and is still the verifier's copy after every run."""
    assert DELIVERED_BYTES == SHIPPED_DRIVER.read_bytes(), "the delivered /app/tools/parcelbill_run.py differs from the shipped driver"
    assert DELIVERED_DRIVER.read_bytes() == SHIPPED_DRIVER.read_bytes(), "the driver on the documented path changed during the run"
    for path in [DELIVERED_DRIVER, DELIVERED_DRIVER.parent, DELIVERED_DRIVER.parent.parent]:
        info = path.lstat()
        assert info.st_uid == 0 and not info.st_mode & 0o022, f"{path} is writable by the candidate's user"
