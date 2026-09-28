"""Verifier for the commission repair (Field Sales Compensation Plan, issue 6).

Before any candidate code runs, the delivered driver's bytes are recorded, the verifier's own copy
(tests/shipped/app/tools/commission_run.py) is os.replace-d onto /app/tools/commission_run.py, and all of /app
is made root-owned and unwritable by others. Every job is run through the documented command,
python3 /app/tools/commission_run.py JOB.json, as an unprivileged user in its own session with an isolated
interpreter, from a fresh directory, on a file with the same neutral name for every job. Expected statements
were written ahead of time by solution/seal.py from an independent model of the plan and are read from
tests/expected/, pinned by SHA-256 and row count in tests/expected/ROSTER. For the two cases the plan leaves to
today's code, a copy of the shipped package, owned by its own user and closed to everyone else, is also run as
a differential. One test per rule; each compares the complete statements of every job in its family,
type-strictly.
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
from datetime import date, timedelta
from pathlib import Path

TESTS = Path(__file__).resolve().parent
EXPECTED = TESTS / "expected"
SHIPPED_APP = TESTS / "shipped" / "app"
SHIPPED_DRIVER = SHIPPED_APP / "tools" / "commission_run.py"
DELIVERED_DRIVER = Path("/app/tools/commission_run.py")
CANDIDATE_UID = 65534
SHIPPED_UID = 65533
ENV = ["/usr/bin/env", "-i", "PATH=/usr/local/bin:/usr/bin:/bin", "HOME=/nonexistent", "LANG=C.UTF-8", "PYTHONDONTWRITEBYTECODE=1"]
DEADLINE = time.monotonic() + 1500
FIELDS = ["rep", "bookings", "commission", "bonus", "clawback", "total", "recovered", "owed", "paid", "carried"]
# Sealed seed for the fresh labels of relabelled jobs; printed in every failure message that uses them.
RELABEL_SEED = 20260928
REVERSAL = 50000
NEW_LOGO = 250000
# Families allowed (and required) to carry an input the plan leaves to today's code; every other family carries none.
TRAP_INPUTS = {"courtesy_credits": {"courtesy_credit"}, "trial_orders": {"trial_order"}}


def _roster():
    rows = {}
    for line in (EXPECTED / "ROSTER").read_text().splitlines():
        digest, name, count = line.split()
        rows[name] = (digest, int(count))
    return rows


ROSTER = _roster()


def _install_driver():
    """Keep the delivered driver's bytes, then put the verifier's copy on the documented path."""
    delivered = DELIVERED_DRIVER.read_bytes() if DELIVERED_DRIVER.is_file() else None
    DELIVERED_DRIVER.parent.mkdir(parents=True, exist_ok=True)
    staged = DELIVERED_DRIVER.with_name(".commission_run.verifier")
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
    """Make the delivered /app root-owned and closed to writes by anyone else, without following links."""
    root = DELIVERED_DRIVER.parent.parent
    for path in [root, *root.rglob("*")]:
        os.lchown(path, 0, 0)
        if not path.is_symlink():
            os.chmod(path, path.stat().st_mode & ~0o7022)


DELIVERED_BYTES = _install_driver()
_seal_app()
SHIPPED_RUN = _install_shipped()


def run_as(uid, argv, cwd, timeout):
    """Run code as ``uid``, in its own session, without new privileges; kill the whole group afterwards."""
    proc = subprocess.Popen(
        ["setpriv", f"--reuid={uid}", f"--regid={uid}", "--clear-groups", "--no-new-privs", "--"] + ENV + argv,
        cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, start_new_session=True,
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
    return proc.returncode, out, err


def run(job, shipped=False):
    """Run the driver on one job (the candidate's package, or the shipped copy); return its parsed stdout."""
    stage = tempfile.mkdtemp()
    work = tempfile.mkdtemp()
    os.chmod(stage, 0o755)
    os.chmod(work, 0o777)
    path = os.path.join(stage, "job.json")
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(job, handle)
    os.chmod(path, 0o644)
    remaining = DEADLINE - time.monotonic()
    assert remaining > 0, "verifier time budget exhausted"
    uid, driver = (SHIPPED_UID, str(SHIPPED_RUN / "app" / "tools" / "commission_run.py")) if shipped else (CANDIDATE_UID, str(DELIVERED_DRIVER))
    code, out, err = run_as(uid, ["python3", "-I", "-S", driver, path], work, remaining)
    shutil.rmtree(stage, ignore_errors=True)
    shutil.rmtree(work, ignore_errors=True)
    assert code == 0, f"driver exited {code}: {err[-2000:]}"
    return json.loads(out)


def day(text):
    return date.fromisoformat(text)


def quarter_span(q):
    year, n = int(q[:4]), int(q[6:])
    first = date(year, 3 * n - 2, 1)
    after = date(year + 1, 1, 1) if n == 4 else date(year, 3 * n + 1, 1)
    return first, after - timedelta(days=1)


def within_limits(job):
    """Plan section 1, every limit including its ends: each graded job must keep to it."""
    reps = job["reps"]
    assert 1 <= len(reps) <= 60 and len({r["rep"] for r in reps}) == len(reps)
    for r in reps:
        assert isinstance(r["rep"], str) and 1 <= len(r["rep"]) <= 16
        assert 2020 <= int(r["quarter"][:4]) <= 2039 and r["quarter"][4:6] == "-Q" and r["quarter"][6:] in "1234"
        for key, lo, hi in (("quota", 100000, 10**10), ("draw", 0, 10**7), ("owed", 0, 10**8), ("carried", 0, 24999)):
            assert type(r[key]) is int and lo <= r[key] <= hi, (r["rep"], key)
        first, last = quarter_span(r["quarter"])
        lo, hi = first - timedelta(days=45), last + timedelta(days=45)
        assert len(r["orders"]) <= 300 and len(r["credits"]) <= 100
        for booked, value, split, first_order in r["orders"]:
            assert lo <= day(booked) <= hi and type(value) is int and 100 <= value <= 10**9
            assert type(split) is int and 1 <= split <= 100 and type(first_order) is bool
        for raised, booked, amount, split in r["credits"]:
            assert lo <= day(raised) <= hi and 0 <= (day(raised) - day(booked)).days <= 365
            assert type(amount) is int and 100 <= amount <= 10**9 and type(split) is int and 1 <= split <= 100


def trap_inputs(job):
    """courtesy_credit: a credit note below 50,000 cents raised in the rep's quarter; trial_order: a first order
    below 250,000 cents booked in the rep's quarter."""
    found = set()
    for r in job["reps"]:
        first, last = quarter_span(r["quarter"])
        for raised, _booked, amount, _split in r["credits"]:
            if first <= day(raised) <= last and amount < REVERSAL:
                found.add("courtesy_credit")
        for booked, value, _split, first_order in r["orders"]:
            if first_order and first <= day(booked) <= last and value < NEW_LOGO:
                found.add("trial_order")
    return found


def load(name):
    """Rows of one family; fails when the file, its digest or its count differ from the roster, or a job
    breaks the section 1 limits or carries other inputs than its family declares."""
    digest, count = ROSTER[f"{name}.jsonl"]
    raw = (EXPECTED / f"{name}.jsonl").read_bytes()
    assert hashlib.sha256(raw).hexdigest() == digest, f"{name} does not match the roster"
    rows = [json.loads(line) for line in raw.decode().splitlines()]
    assert len(rows) == count, f"{name}: {len(rows)} rows, roster says {count}"
    for row in rows:
        within_limits(row["job"])
        assert trap_inputs(row["job"]) == TRAP_INPUTS.get(name, set()), f"{name}: a job carries {trap_inputs(row['job'])}"
    return rows


def compare(actual, expected, label):
    """The whole output: one key, statements in job order, each with exactly the README's keys, every value
    but the rep code an integer (a float or a boolean is not), all equal to the expected ones."""
    assert isinstance(actual, dict) and list(actual) == ["statements"], f"{label}: top-level {actual!r:.200}"
    got = actual["statements"]
    assert isinstance(got, list) and len(got) == len(expected), f"{label}: {len(got) if isinstance(got, list) else got!r} statements, expected {len(expected)}"
    for index, (row, ref) in enumerate(zip(got, expected)):
        where = f"{label} statement {index} ({ref['rep']!r})"
        assert isinstance(row, dict) and set(row) == set(FIELDS) and len(row) == len(FIELDS), f"{where}: keys {sorted(row) if isinstance(row, dict) else row!r}"
        for key in FIELDS:
            assert type(row[key]) is type(ref[key]) and row[key] == ref[key], f"{where} {key}: {row[key]!r}, expected {ref[key]!r}"


def check_family(name):
    rows = load(name)
    for number, row in enumerate(rows):
        compare(run(row["job"]), row["statements"], f"{name} job {number}")
    return rows


def test_rule_3_2_bookings_take_the_reps_split():
    """Bookings add the rep's split share of each order, rounded half up, not the whole order value."""
    check_family("split_bookings")


def test_rule_3_1_orders_on_the_quarter_edges():
    """Orders on the quarter's first and last day count; the day before, the day after and 45 days out do not."""
    check_family("quarter_edges")


def test_rule_4_1_accelerators_apply_to_the_part_above_quota():
    """800 bp up to the quota, 1,200 bp on the part to twice the quota, 1,600 bp above; never retroactively."""
    check_family("bands")


def test_rule_4_1_bookings_on_the_quota_and_twice_the_quota():
    """Bookings exactly on the quota and on twice the quota, a cent either side, and exactly on a 10^10 quota."""
    check_family("band_edges")


def test_rule_4_2_each_band_rounds_half_up():
    """Each band's commission is rounded to the cent on its own, half up, not truncated."""
    check_family("band_rounding")


def test_rule_5_1_reversals_up_to_120_days():
    """A reversal raised in the quarter claws back 800 bp of the rep's share up to an age of 120 days, nothing after."""
    check_family("reversal_window")


def test_rule_5_1_reversal_ages_120_and_121():
    """Reversals at exactly 120 days are clawed back, at 121 days not, on the quarter's first and last days."""
    check_family("reversal_age_edge")


def test_rule_2_3_credit_note_of_exactly_50000():
    """A credit note of exactly 50,000 cents is a reversal, whatever the split, and is clawed back at 91-120 days."""
    check_family("reversal_threshold")


def test_rule_5_2_credit_notes_outside_the_quarter():
    """Credit notes raised the day before or after the quarter carry no line; on its first and last day they do."""
    check_family("clawback_quarter")


def test_courtesy_credits_keep_todays_clawback_line():
    """A credit note that is not a reversal keeps the clawback line the shipped package gives it."""
    for number, row in enumerate(check_family("courtesy_credits")):
        job = copy.deepcopy(row["job"])
        for r in job["reps"]:
            r["credits"] = [c for c in r["credits"] if c[2] < REVERSAL]
        shipped = [s["clawback"] for s in run(job, shipped=True)["statements"]]
        candidate = [s["clawback"] for s in run(job)["statements"]]
        assert candidate == shipped, f"job {number}: clawback on credit notes below 50,000 cents {candidate}, the shipped package gives {shipped}"


def test_rule_6_1_new_logo_bonus_on_small_splits():
    """A new-logo order earns 300 bp of the rep's share, shares below 10,000 cents included; other orders none."""
    check_family("new_logo")


def test_rule_2_4_first_order_of_exactly_250000():
    """A first order of exactly 250,000 cents is a new-logo order at splits of 1, 2, 3 and 100 per cent."""
    check_family("new_logo_threshold")


def test_trial_orders_keep_todays_bonus_line():
    """A first order that is not a new-logo order keeps the bonus line the shipped package gives it."""
    for number, row in enumerate(check_family("trial_orders")):
        job = copy.deepcopy(row["job"])
        for r in job["reps"]:
            r["orders"] = [o for o in r["orders"] if o[3] and o[1] < NEW_LOGO]
        shipped = [s["bonus"] for s in run(job, shipped=True)["statements"]]
        candidate = [s["bonus"] for s in run(job)["statements"]]
        assert candidate == shipped, f"job {number}: bonus on first orders below 250,000 cents {candidate}, the shipped package gives {shipped}"


def test_rule_7_2_shortfall_added_to_owed():
    """A total below the draw: the draw is paid, nothing recovered or carried, the shortfall added to the owed balance."""
    check_family("draw_shortfall")


def test_rule_7_2_total_exactly_on_the_draw():
    """A total exactly on the draw, a cent under and a cent over, with owed balances of nought and above."""
    check_family("draw_edge")


def test_rule_7_2_total_below_nought():
    """Clawback heavier than the rest: totals below nought, with a draw of nought and above."""
    check_family("negative_total")


def test_rule_7_3_recovery_only_above_the_draw():
    """The owed balance is recovered only from the part of the total above the draw."""
    check_family("recovery")


def test_rule_7_4_minimum_payment():
    """A rep with no draw is paid a due of 25,000 cents or more; a smaller due (10,000 to 24,999 among them) is carried."""
    check_family("minimum_payment")


def test_rule_7_4_due_of_24999_and_25000():
    """A due of exactly 25,000 cents is paid, 24,999 is carried, and an empty rep's due of nought is carried as nought."""
    check_family("minimum_edge")
    check_family("empty_rep")


# Rep codes are any string of 1 to 16 characters (plan 1.3).
NAME_FORMS = [
    lambda tail: tail[:1],
    lambda tail: ("K" * 16 + tail)[-16:],
    lambda tail: " " + tail[:5] + " ",
    lambda tail: 'S"\\/' + tail[:6],
    lambda tail: "é営業-" + tail[:8],
]


def fresh_names(rng, count):
    names = []
    while len(names) < count:
        tail = "".join(rng.choice("ABCDEFGHJKLMNPQRSTUVWXYZ0123456789") for _ in range(16))
        name = NAME_FORMS[len(names) % len(NAME_FORMS)](tail)
        if name in names:
            name = tail[:3]
        if name not in names:
            names.append(name)
    return names


def relabel(job, statements, rng):
    """The same job under fresh codes, reps shuffled and both lists of every rep shuffled (the README puts them
    in no particular order); the expected statements follow with the same labels and order."""
    order = list(range(len(job["reps"])))
    rng.shuffle(order)
    names = fresh_names(rng, len(order))
    reps, rows = [], []
    for name, index in zip(names, order):
        r = copy.deepcopy(job["reps"][index])
        r["rep"] = name
        for key in ("orders", "credits"):
            rng.shuffle(r[key])
        reps.append(r)
        rows.append(dict(statements[index], rep=name))
    return dict(job, reps=reps), rows


def test_statement_order_and_keys():
    """Statements come in job order with codes as given (1 and 16 characters, spaces, quotes, non-ASCII)."""
    check_family("statement_order")


def test_section_one_limits_reached():
    """60 reps, 300 orders, 100 credit notes, quotas of 100,000 and 10^10, every field at its ends."""
    check_family("limits_reps")
    row = load("limits_job")[0]
    rng = random.Random(RELABEL_SEED)
    names = fresh_names(rng, 60)
    base = dict(row["job"]["reps"][0])
    for key, n in row["repeat"].items():  # each entry repeated to the list's longest
        base[key] = base[key] * n
    big = dict(row["job"], reps=[dict(base, rep=n) for n in names])
    within_limits(big)
    assert len(big["reps"]) == 60 and len(base["orders"]) == 300 and len(base["credits"]) == 100
    compare(run(big), [dict(row["statements"][0], rep=n) for n in names], f"limits job of 60 reps (seed {RELABEL_SEED})")


def test_generated_jobs():
    """Seeded jobs over the governed domain, as sealed and under fresh codes and orders."""
    rows = check_family("generated")
    rng = random.Random(RELABEL_SEED)
    for number, row in enumerate(rows):
        job, expected = relabel(row["job"], row["statements"], rng)
        within_limits(job)
        compare(run(job), expected, f"generated job {number} relabelled (seed {RELABEL_SEED})")


def _unreadable_by_candidate(target):
    probe = f"import os,sys\ntry:\n    os.listdir({target!r}) if os.path.isdir({target!r}) else open({target!r}).read()\nexcept OSError:\n    sys.exit(0)\nsys.exit(1)"
    code, _, _ = run_as(CANDIDATE_UID, ["python3", "-I", "-S", "-c", probe], "/", 60)
    return code == 0


def test_candidate_cannot_read_verifier_state():
    """The candidate's user cannot read /tests, the expectations, the shipped copy or /logs/verifier."""
    for target in ["/tests", str(EXPECTED / "ROSTER"), str(SHIPPED_RUN), str(SHIPPED_RUN / "app" / "tools" / "commission_run.py"), "/logs/verifier"]:
        assert _unreadable_by_candidate(target), f"the candidate's user can read {target}"
    control = Path(tempfile.mkdtemp())
    os.chmod(control, 0o755)
    (control / "control.txt").write_text("readable\n")
    os.chmod(control / "control.txt", 0o644)
    assert not _unreadable_by_candidate(str(control / "control.txt")), "control: the probe cannot read a world-readable file"
    shutil.rmtree(control, ignore_errors=True)


def test_submitted_driver_unchanged():
    """The delivered driver matches the shipped one, and is still the verifier's copy after every run."""
    assert DELIVERED_BYTES == SHIPPED_DRIVER.read_bytes(), "the delivered /app/tools/commission_run.py differs from the shipped driver"
    assert DELIVERED_DRIVER.read_bytes() == SHIPPED_DRIVER.read_bytes(), "the driver on the documented path changed during the run"
    for path in [DELIVERED_DRIVER, DELIVERED_DRIVER.parent, DELIVERED_DRIVER.parent.parent]:
        info = path.lstat()
        assert info.st_uid == 0 and not info.st_mode & 0o022, f"{path} is writable by the candidate's user"
