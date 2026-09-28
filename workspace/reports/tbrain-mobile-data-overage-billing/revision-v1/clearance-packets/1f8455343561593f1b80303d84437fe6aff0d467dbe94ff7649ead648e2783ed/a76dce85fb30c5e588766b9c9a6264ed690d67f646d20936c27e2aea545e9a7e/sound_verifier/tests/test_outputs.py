"""Verifier for the usagebill repair (data usage tariff MD-2).

Before any candidate code runs, the delivered driver's bytes are recorded, the verifier's own copy
(tests/shipped/app/tools/usagebill_run.py) is os.replace-d onto /app/tools/usagebill_run.py, and all of /app is
made root-owned and unwritable by others. Every account file is billed by the documented command,
python3 /app/tools/usagebill_run.py USAGE.json, as an unprivileged user in its own session with an isolated
interpreter, from a fresh directory, on a file with the same neutral name for every job. Expected statements were
written ahead of time by solution/seal.py from an independent model of the tariff and are read from
tests/expected/, whose SHA-256 sums and row counts are pinned in tests/expected/ROSTER.

One test per rule. Two figures are left by the tariff to today's code: the allowance of a FLEX line, and the overage
and charge of a line that is not over its allowance. A line carrying either appears only in the tests that grade it.
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
SHIPPED_DRIVER = SHIPPED_APP / "tools" / "usagebill_run.py"
DELIVERED_DRIVER = Path("/app/tools/usagebill_run.py")
CANDIDATE_UID = 65534
SHIPPED_UID = 65533
ENV = ["/usr/bin/env", "-i", "PATH=/usr/local/bin:/usr/bin:/bin", "HOME=/nonexistent", "LANG=C.UTF-8", "PYTHONDONTWRITEBYTECODE=1"]
DEADLINE = time.monotonic() + 1500
# Fresh labels for the relabelled generated files; printed in every failure message.
RELABEL_SEED = int.from_bytes(os.urandom(8), "big")
LINE_KEYS = ("id", "used", "allowance", "over", "charge")
CODE = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
ALLOWANCE = {"BASIC": 2048, "PLUS": 10240}
# The README gives an account's name as any string, returned as given: each relabelled pass also bills the seeded
# files under names no sealed file carries (lower case, empty, very long, spaces at the edges and inside, quotes,
# backslashes, non-ASCII) and under one fresh name drawn from all of those characters.
NAME_CHARS = CODE + "abcdefghijklmnopqrstuvwxyz -_.,&'\"\\/\täöüßøéçñ東京モバイル🚀"
NAMES = ["a", "", "  Fjord  Ltd\t ", 'Müller & Söhne "Nord" \\ Ølstad', "mD2-0001 kontor", "東京モバイル株式会社 🚀", "0042", "Ab" * 600]
# Figures left by the tariff to today's code that a family grades; a line carrying one appears only in a family
# that grades it.
GRADES = {"flex": {"flex"}, "not_over": {"idle"}, "together": {"flex", "idle"}}


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
    staged = DELIVERED_DRIVER.with_name(".usagebill_run.verifier")
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


def run(usage, shipped=False):
    """Run the driver on one account file (the candidate's package, or the shipped copy); return its parsed stdout."""
    stage = tempfile.mkdtemp()
    work = tempfile.mkdtemp()
    os.chmod(stage, 0o755)
    os.chmod(work, 0o777)
    path = os.path.join(stage, "usage.json")
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(usage, handle)
    os.chmod(path, 0o644)
    remaining = DEADLINE - time.monotonic()
    assert remaining > 0, "verifier time budget exhausted"
    uid, driver = (SHIPPED_UID, str(SHIPPED_RUN / "app" / "tools" / "usagebill_run.py")) if shipped else (CANDIDATE_UID, str(DELIVERED_DRIVER))
    code, out, err = run_as(uid, ["python3", "-I", "-S", driver, path], work, remaining)
    shutil.rmtree(stage, ignore_errors=True)
    shutil.rmtree(work, ignore_errors=True)
    assert code == 0, f"driver exited {code}: {err[-2000:]}"
    return json.loads(out)


def _megabytes(entry):
    return sum(-(-kb // 1024) for kb in entry["sessions"])


def silent(entry):
    """The figures the tariff leaves to today's code that this line carries."""
    out = set()
    if entry["plan"] not in ALLOWANCE:
        out.add("flex")
    if _megabytes(entry) <= ALLOWANCE.get(entry["plan"], 5120):
        out.add("idle")
    return out


def within_limits(u):
    """Rule 1.2, every limit including its ends: each graded file must keep to it."""
    items = u["lines"]
    assert isinstance(u["account"], str) and 1 <= len(items) <= 200
    assert len({x["id"] for x in items}) == len(items)
    for x in items:
        assert 1 <= len(x["id"]) <= 10 and set(x["id"]) <= set(CODE)
        assert x["plan"] in ("BASIC", "PLUS", "FLEX")
        assert isinstance(x["sessions"], list) and len(x["sessions"]) <= 60
        assert all(type(k) is int and 1 <= k <= 2000000 for k in x["sessions"])
        assert type(x["rate"]) is int and 1 <= x["rate"] <= 500


def load(name):
    """Rows of one family; fails when the file, its digest or its count differ from the roster, or a file breaks
    rule 1.2 or carries a line with a figure left to today's code into a family that does not grade it."""
    file, digest, count = ROSTER[name]
    raw = (EXPECTED / file).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == digest, f"{name} does not match the roster"
    rows = [json.loads(line) for line in raw.decode().splitlines() if line]
    assert len(rows) == count, f"{name}: {len(rows)} rows, roster says {count}"
    for row in rows:
        within_limits(row["usage"])
        for x in row["usage"]["lines"]:
            assert silent(x) <= GRADES.get(name, set()), f"{name}: {row['usage']['account']} line {x['id']} is not graded here"
    return rows


def _same(actual, expected, where):
    assert type(actual) is type(expected) and actual == expected, f"{where}: {actual!r}, expected {expected!r}"


def compare(actual, expected, label):
    """Every key the README lists, as a JSON integer or string; further keys are ignored."""
    assert isinstance(actual, dict) and set(actual) >= {"account", "lines", "total"}, f"{label}: top-level keys"
    _same(actual["account"], expected["account"], f"{label} account")
    _same(actual["total"], expected["total"], f"{label} total")
    got, want = actual["lines"], expected["lines"]
    assert isinstance(got, list) and len(got) == len(want), f"{label}: {len(got) if isinstance(got, list) else got!r} lines, expected {len(want)}"
    for index, (row, ref) in enumerate(zip(got, want)):
        assert isinstance(row, dict) and set(row) >= set(LINE_KEYS), f"{label} lines[{index}]: keys {row!r}"
        for key in LINE_KEYS:
            _same(row[key], ref[key], f"{label} lines[{index}] ({ref['id']}) {key}")


def check_family(name):
    for row in load(name):
        compare(run(row["usage"]), row["statement"], f"{name} {row['usage']['account']}")


def test_rule_2_1_sessions_in_whole_megabytes():
    """Each session in whole megabytes, a part megabyte counting as a whole one."""
    check_family("sessions")


def test_rule_2_2_plan_allowances():
    """BASIC 2,048 MB and PLUS 10,240 MB; one megabyte over each."""
    check_family("plans")


def test_rule_3_1_one_cent_after_the_first_1024_mb():
    """The rate for each of the first 1,024 MB of overage, 1 cent for each megabyte after."""
    check_family("later_rate")


def test_rule_3_2_total_and_line_order():
    """Every charge and the total, lines in file order, ids of one to ten characters."""
    check_family("order_and_total")


def test_flex_line_keeps_todays_allowance():
    """The tariff gives no allowance for a FLEX line: today's step stands."""
    check_family("flex")


def test_line_not_over_keeps_todays_overage_and_charge():
    """The tariff gives no overage or charge for a line inside its allowance: today's step stands."""
    check_family("not_over")


def test_figures_left_to_todays_code_together():
    """FLEX lines inside and past their allowance, beside BASIC and PLUS lines."""
    check_family("together")


def test_rule_1_2_limits_reached():
    """200 lines; 60 sessions; sessions of 1 and 2,000,000 kB; rates 1 and 500."""
    assert len(load("limits")[0]["usage"]["lines"]) == 200
    check_family("limits")


def relabel(row, rng, name):
    """The same file under the given name and fresh ids, lines and their sessions shuffled; the statement follows."""
    u, want = copy.deepcopy(row["usage"]), copy.deepcopy(row["statement"])
    ids = set()
    while len(ids) < len(u["lines"]):
        ids.add("".join(rng.choice(CODE) for _ in range(rng.randint(1, 10))))
    ids = sorted(ids)
    order = list(range(len(u["lines"])))
    rng.shuffle(order)
    items = [dict(u["lines"][i], id=ids[i], sessions=rng.sample(u["lines"][i]["sessions"], len(u["lines"][i]["sessions"]))) for i in order]
    lines = [dict(want["lines"][i], id=ids[i]) for i in order]
    return {"account": name, "lines": items}, {"account": name, "lines": lines, "total": want["total"]}


def test_generated_account_files():
    """Seeded files of BASIC and PLUS lines over their allowance, as sealed and under fresh labels, the account's
    name among them any string at all."""
    check_family("generated")
    rng = random.Random(RELABEL_SEED)
    rows = load("generated")
    names = NAMES + ["".join(rng.choice(NAME_CHARS) for _ in range(rng.randint(1, 40))) for _ in rows]
    for index, name in enumerate(names):
        row = rows[index % len(rows)]
        u, expected = relabel(row, rng, name)
        within_limits(u)
        compare(run(u), expected, f"generated {row['usage']['account']} relabelled as {name[:60]!r} (seed {RELABEL_SEED})")


def _unreadable_by_candidate(target):
    probe = f"import os,sys\ntry:\n    os.listdir({target!r}) if os.path.isdir({target!r}) else open({target!r}).read()\nexcept OSError:\n    sys.exit(0)\nsys.exit(1)"
    code, _, _ = run_as(CANDIDATE_UID, ["python3", "-I", "-S", "-c", probe], "/", 60)
    return code == 0


def test_candidate_cannot_read_verifier_state():
    """The candidate's user cannot read /tests, the expectations, the shipped copy or /logs/verifier."""
    for target in ["/tests", str(EXPECTED / "ROSTER"), str(SHIPPED_RUN), str(SHIPPED_RUN / "app" / "tools" / "usagebill_run.py"), "/logs/verifier"]:
        assert _unreadable_by_candidate(target), f"the candidate's user can read {target}"
    control = Path(tempfile.mkdtemp()) / "control.txt"
    control.write_text("readable\n")
    os.chmod(control.parent, 0o755)
    os.chmod(control, 0o644)
    assert not _unreadable_by_candidate(str(control)), "control: the probe cannot read a world-readable file"


def test_submitted_driver_unchanged():
    """The delivered driver matches the shipped one, and is still the verifier's copy after every run."""
    assert DELIVERED_BYTES == SHIPPED_DRIVER.read_bytes(), "the delivered /app/tools/usagebill_run.py differs from the shipped driver"
    assert DELIVERED_DRIVER.read_bytes() == SHIPPED_DRIVER.read_bytes(), "the driver on the documented path changed during the run"
    for path in [DELIVERED_DRIVER, DELIVERED_DRIVER.parent, DELIVERED_DRIVER.parent.parent]:
        info = path.lstat()
        assert info.st_uid == 0 and not info.st_mode & 0o022, f"{path} is writable by the candidate's user"
