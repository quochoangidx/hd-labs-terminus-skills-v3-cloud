"""Verifier for the noisedose repair (noise survey manual HC-4).

Before any candidate code runs, the delivered driver's bytes are recorded, the
verifier's own copy (tests/shipped/app/tools/noisedose_run.py) is os.replace-d onto
/app/tools/noisedose_run.py, and all of /app is made root-owned and unwritable by others. Every survey is then reduced by the documented command,
python3 /app/tools/noisedose_run.py SURVEY.json, as an unprivileged user in its own
session with an isolated interpreter, from a fresh directory, on a file with the same
neutral name for every survey. Expected reports were written ahead of time by
solution/seal.py from an independent model of the manual and are read from
tests/expected/, whose SHA-256 sums and row counts are pinned in tests/expected/ROSTER.
For the figures the manual leaves to today's code, a copy of the shipped package,
owned by its own user and closed to everyone else, is run on survey pairs as a
differential. One test per rule; each compares the complete report of every survey in
its family. The generated family is also reduced under fresh labels drawn at run time
(survey name, worker ids, worker order, runs split in two), a relabelling that leaves
every figure the manual defines unchanged, so a report cannot be looked up by name.
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
SHIPPED_DRIVER = SHIPPED_APP / "tools" / "noisedose_run.py"
DELIVERED_DRIVER = Path("/app/tools/noisedose_run.py")
CANDIDATE_UID = 65534
SHIPPED_UID = 65533
ENV = ["/usr/bin/env", "-i", "PATH=/usr/local/bin:/usr/bin:/bin", "HOME=/nonexistent", "LANG=C.UTF-8", "PYTHONDONTWRITEBYTECODE=1"]
DEADLINE = time.monotonic() + 1500
# instruction: within 1e-11 of its size (1e-11 below one) passes, more than 1e-10 fails; graded at the midpoint.
REL, ABS = 5e-11, 5e-11
# Fresh labels for the relabelled generated surveys; printed in every failure message.
RELABEL_SEED = int.from_bytes(os.urandom(8), "big")
ROW_KEYS = {"id", "group", "dose", "twa", "status", "ceiling", "impulse"}
GROUP_KEYS = {"group", "dose", "twa", "status"}
CODE = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")
# Families allowed to carry an input the manual leaves to today's code; every other family carries none.
TRAP_INPUTS = {
    "paused_runs": {"paused"},
    "below_three_quarters": {"below_three_quarters", "paused"},
    "measured_nothing": {"below_three_quarters", "paused"},
    "above_ceiling": {"above_ceiling"},
    "differential-below_three_quarters": {"below_three_quarters"},
    "differential-measured_nothing": {"below_three_quarters", "paused"},
    "differential-above_ceiling": {"above_ceiling"},
}


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
    staged = DELIVERED_DRIVER.with_name(".noisedose_run.verifier")
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
    candidate code cannot change the driver, or anything else under /app, between reductions."""
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
    return proc.returncode, out, err


def reduce(survey, shipped=False):
    """Run the driver on one survey (the candidate's package, or the shipped copy); return its parsed stdout."""
    stage = tempfile.mkdtemp()
    work = tempfile.mkdtemp()
    os.chmod(stage, 0o755)
    os.chmod(work, 0o777)
    path = os.path.join(stage, "survey.json")
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(survey, handle)
    os.chmod(path, 0o644)
    remaining = DEADLINE - time.monotonic()
    assert remaining > 0, "verifier time budget exhausted"
    uid, driver = (SHIPPED_UID, str(SHIPPED_RUN / "app" / "tools" / "noisedose_run.py")) if shipped else (CANDIDATE_UID, str(DELIVERED_DRIVER))
    code, out, err = run_as(uid, ["python3", "-I", "-S", driver, path], work, remaining)
    shutil.rmtree(stage, ignore_errors=True)
    shutil.rmtree(work, ignore_errors=True)
    assert code == 0, f"driver exited {code}: {err[-2000:]}"
    return json.loads(out)


def sampled_time(log):
    return sum(m for m, level in log if level >= 40.0)


def within_limits(survey):
    """Manual 1.4, every limit including its ends: each graded survey must keep to it."""
    workers = survey["workers"]
    assert isinstance(survey["survey"], str) and 1 <= len(workers) <= 300
    assert len({w["group"] for w in workers}) <= 40 and len({w["id"] for w in workers}) == len(workers)
    for w in workers:
        assert 1 <= len(w["id"]) <= 12 and set(w["id"]) <= CODE | {"-"}
        assert 1 <= len(w["group"]) <= 8 and set(w["group"]) <= CODE
        assert type(w["shift_minutes"]) is int and 60 <= w["shift_minutes"] <= 1440
        assert len(w["log"]) <= 1500 and sum(m for m, _ in w["log"]) <= 2880
        assert all(type(m) is int and 1 <= m <= 1440 for m, _ in w["log"])
        assert all(type(v) is float and (v == 0.0 or 40.0 <= v <= 140.0) for _, v in w["log"])
        assert len(w["peaks"]) <= 500 and all(type(p) is float and 60.0 <= p <= 170.0 for p in w["peaks"])


def trap_inputs(survey):
    out = set()
    for w in survey["workers"]:
        if any(v == 0.0 for _, v in w["log"]):
            out.add("paused")
        if any(v > 115.0 for _, v in w["log"]):
            out.add("above_ceiling")
        if 4 * sampled_time(w["log"]) < 3 * w["shift_minutes"]:
            out.add("below_three_quarters")
    return out


def load(name):
    """Rows of one family; fails when the file, its digest or its count differ from the roster, or a
    survey breaks the section 1 limits or carries an input its family does not declare."""
    digest, count = ROSTER[f"{name}.jsonl"]
    raw = (EXPECTED / f"{name}.jsonl").read_bytes()
    assert hashlib.sha256(raw).hexdigest() == digest, f"{name} does not match the roster"
    rows = [json.loads(line) for line in raw.decode().splitlines() if line]
    assert len(rows) == count, f"{name}: {len(rows)} rows, roster says {count}"
    for row in rows:
        for survey in [row[k] for k in ("survey", "a", "b") if k in row]:
            within_limits(survey)
            assert trap_inputs(survey) <= TRAP_INPUTS.get(name, set()), f"{name}: {survey['survey']} carries {trap_inputs(survey)}"
    return rows


def _number(actual, expected, where):
    assert isinstance(actual, (int, float)) and not isinstance(actual, bool), f"{where}: {actual!r} is not a number"
    bound = REL * abs(expected) if abs(expected) >= 1 else ABS
    assert abs(actual - expected) <= bound, f"{where}: {actual!r}, expected {expected!r}"


def _row(actual, expected, keys, where):
    """Every key the README lists, compared; a group row carries no ceiling or impulse flag (6.1); any other
    further key is not part of the contract and is ignored."""
    assert isinstance(actual, dict) and set(actual) >= keys, f"{where}: keys {actual!r}"
    if keys == GROUP_KEYS:
        assert not {"ceiling", "impulse"} & set(actual), f"{where}: a group carries no ceiling or impulse flag, got {actual!r}"
    for key in sorted(keys):
        a, e = actual[key], expected[key]
        if key == "dose":
            _number(a, e, f"{where} dose")
        elif key == "twa" and e is not None:
            assert isinstance(a, (int, float)) and not isinstance(a, bool) and a == e, f"{where} twa: {a!r}, expected {e!r}"
        else:
            assert type(a) is type(e) and a == e, f"{where} {key}: {a!r}, expected {e!r}"


def compare(actual, expected, label):
    assert isinstance(actual, dict) and set(actual) >= {"survey", "workers", "groups"}, f"{label}: top-level keys"
    assert type(actual["survey"]) is str and actual["survey"] == expected["survey"], f"{label}: survey name"
    for section, keys in (("workers", ROW_KEYS), ("groups", GROUP_KEYS)):
        got, want = actual[section], expected[section]
        assert isinstance(got, list) and len(got) == len(want), f"{label}: {section} has {len(got) if isinstance(got, list) else got!r} rows, expected {len(want)}"
        for index, (row, ref) in enumerate(zip(got, want)):
            _row(row, ref, keys, f"{label} {section}[{index}] ({ref.get('id', ref['group'])})")


def check_family(name):
    for row in load(name):
        compare(reduce(row["survey"]), row["report"], f"{name} {row['survey']['survey']}")


def check_differential(name):
    """Surveys a and b differ only in a field the kept step does not use: the shipped package gives each
    worker the same dose in both, and so must the candidate."""
    for number, row in enumerate(load(f"differential-{name}")):
        shipped = [reduce(row[k], shipped=True)["workers"] for k in ("a", "b")]
        candidate = [reduce(row[k])["workers"] for k in ("a", "b")]
        for sa, sb, ca, cb in zip(*shipped, *candidate):
            assert sa["dose"] == sb["dose"], f"{name} pair {number}: the shipped step is not the same in both"
            _number(ca["dose"], cb["dose"], f"{name} pair {number} worker {ca.get('id')}: dose of b against a")
            if sa["dose"] == 0.0:
                _number(ca["dose"], 0.0, f"{name} pair {number} worker {ca.get('id')}: the shipped dose is 0.0")


def test_rule_3_1_reference_duration_uses_85_dba_and_3_db():
    """Doses follow the 85 dBA criterion and 3 dB exchange rate, at levels from 80.0 to 115.0 dBA."""
    check_family("reference_duration")


def test_rule_2_3_reading_at_the_threshold_counts():
    """A reading exactly at 80.0 dBA adds dose; 79.9 dBA does not."""
    check_family("threshold")


def test_rule_2_4_sampled_time_includes_readings_below_threshold():
    """Sampled time counts every reading, quiet ones at 40.0 to 79.9 dBA included."""
    check_family("sampled_time")


def test_rule_2_2_run_logged_at_nought_is_not_a_reading():
    """A run logged at 0.0 is not a reading, so its minutes stay out of sampled time."""
    check_family("paused_runs")


def test_rule_3_3_partial_survey_projected_to_own_shift():
    """A partial survey is projected to the worker's own shift, not to eight hours."""
    check_family("partial_surveys")


def test_rule_3_3_survey_as_long_as_shift_keeps_measured_dose():
    """A survey of the whole shift or longer keeps its measured dose."""
    check_family("whole_shift")


def test_rule_2_5_partial_survey_at_exactly_three_quarters():
    """Sampled time of exactly three quarters of the shift is a partial survey, on shifts of 60 to 1,440 minutes."""
    check_family("three_quarters")


def test_survey_below_three_quarters_keeps_todays_projection():
    """The manual gives no rule for the shift dose of a survey below three quarters: today's step stands."""
    check_family("below_three_quarters")
    check_differential("below_three_quarters")


def test_survey_that_measured_nothing_keeps_todays_dose():
    """A survey that measured nothing keeps today's shift dose of nought."""
    check_family("measured_nothing")
    check_differential("measured_nothing")


def test_reading_above_ceiling_keeps_todays_counted_level():
    """A reading above the ceiling level is counted where today's step counts it, and flags the ceiling."""
    check_family("above_ceiling")
    check_differential("above_ceiling")


def test_rule_5_1_reading_at_the_ceiling_level_is_not_flagged():
    """A reading of exactly 115.0 dBA does not flag the ceiling."""
    check_family("ceiling_level")


def test_rule_5_2_impulse_at_140_dbc():
    """A peak of 140.0 dBC is an impulse and makes the worker "over"; 139.9 dBC is not."""
    check_family("impulse")


def test_rule_4_1_twa_formula():
    """The TWA is 85 + 3 log2(D / 100); a dose of nought has no TWA."""
    check_family("twa")


def test_rule_1_2_twa_rounded_to_nearest_tenth():
    """The reported TWA is the nearest tenth, on both sides of each tenth."""
    check_family("rounding")


def test_rule_5_3_status_bands_at_82_and_85():
    """Status bands at 82.0 and 85.0 dB on the reported TWA, and "over" for a flagged worker."""
    check_family("status")


def test_rule_6_1_group_dose_is_mean_of_shift_doses():
    """A group's dose is the mean of its members' shift doses; its TWA and status follow from it."""
    check_family("groups")


def test_rule_6_1_quiet_member_counts_in_group_mean():
    """A quiet member's shift dose of nought counts in the group mean."""
    check_family("quiet_members")


def test_report_order_and_group_codes():
    """Workers stay in survey order; groups come in ascending character order of their codes."""
    check_family("report_order")


def test_section_one_limits_reached():
    """300 workers under 40 codes, a 1,500-run log, a 2,880-minute log, 500 peaks and the range ends."""
    rows = load("limits_workers") + load("limits_logs")
    workers = rows[0]["survey"]["workers"]
    assert len(workers) == 300 and len({w["group"] for w in workers}) == 40
    logs = rows[1]["survey"]["workers"]
    assert len(logs[0]["log"]) == 1500 and sum(m for m, _ in logs[1]["log"]) == 2880 and len(logs[2]["peaks"]) == 500
    check_family("limits_workers")
    check_family("limits_logs")


# The survey name is any string (README): the relabelled surveys carry an empty name, long ones, spaces at
# either end, punctuation, quotes, backslashes and characters outside ASCII, each ending in a fresh draw.
NAME_FORMS = [
    lambda tail: "",
    lambda tail: "A" * 100 + tail,
    lambda tail: 'Press shop, line 4 / "B" crew \\ day 2026-09-27; ' * 40 + tail,
    lambda tail: "Pressenwerk S\u00fcd \u2014 Schicht 2 \u2713 \u9a12\u97f3 " + tail,
    lambda tail: "  spaced name " + tail + "  ",
]


def relabel(row, rng, form=1):
    """The same survey under a fresh name (one of NAME_FORMS) and fresh worker ids, workers shuffled and every run of two or more
    minutes split into two runs at its level; the expected report follows with the same labels and order."""
    survey, report = copy.deepcopy(row["survey"]), copy.deepcopy(row["report"])
    name = NAME_FORMS[form]("".join(rng.choice(sorted(CODE)) for _ in range(10)))
    ids = set()
    while len(ids) < len(survey["workers"]):
        ids.add("".join(rng.choice(sorted(CODE | {"-"})) for _ in range(12)))
    order = list(range(len(survey["workers"])))
    rng.shuffle(order)
    workers, rows = [], []
    for new_id, index in zip(sorted(ids), order):
        worker, expected = survey["workers"][index], report["workers"][index]
        log = []
        for minutes, level in worker["log"]:
            cut = rng.randint(1, minutes - 1) if minutes > 1 else minutes
            log += [[cut, level], [minutes - cut, level]] if cut < minutes else [[minutes, level]]
        workers.append(dict(worker, id=new_id, log=log))
        rows.append(dict(expected, id=new_id))
    return {"survey": name, "workers": workers}, {"survey": name, "workers": rows, "groups": report["groups"]}


def test_generated_surveys():
    """Seeded surveys over the rest of the section 1 domain, as sealed and under fresh labels."""
    check_family("generated")
    rng = random.Random(RELABEL_SEED)
    for form, row in enumerate(load("generated")):
        survey, expected = relabel(row, rng, form % len(NAME_FORMS))
        within_limits(survey)
        compare(reduce(survey), expected, f"generated {row['survey']['survey']} relabelled (seed {RELABEL_SEED})")


def _unreadable_by_candidate(target):
    probe = f"import os,sys\ntry:\n    os.listdir({target!r}) if os.path.isdir({target!r}) else open({target!r}).read()\nexcept OSError:\n    sys.exit(0)\nsys.exit(1)"
    code, _, _ = run_as(CANDIDATE_UID, ["python3", "-I", "-S", "-c", probe], "/", 60)
    return code == 0


def test_candidate_cannot_read_verifier_state():
    """The candidate's user cannot read /tests, the expectations, the shipped copy or /logs/verifier."""
    for target in ["/tests", str(EXPECTED / "ROSTER"), str(SHIPPED_RUN), str(SHIPPED_RUN / "app" / "tools" / "noisedose_run.py"), "/logs/verifier"]:
        assert _unreadable_by_candidate(target), f"the candidate's user can read {target}"
    assert not _unreadable_by_candidate("/app/README.md"), "control: the probe cannot read a world-readable file"


def test_submitted_driver_unchanged():
    """The delivered driver matches the shipped one, and is still the verifier's copy after every run."""
    assert DELIVERED_BYTES == SHIPPED_DRIVER.read_bytes(), "the delivered /app/tools/noisedose_run.py differs from the shipped driver"
    assert DELIVERED_DRIVER.read_bytes() == SHIPPED_DRIVER.read_bytes(), "the driver on the documented path changed during the run"
    for path in [DELIVERED_DRIVER, DELIVERED_DRIVER.parent, DELIVERED_DRIVER.parent.parent]:
        info = path.lstat()
        assert info.st_uid == 0 and not info.st_mode & 0o022, f"{path} is writable by the candidate's user"
