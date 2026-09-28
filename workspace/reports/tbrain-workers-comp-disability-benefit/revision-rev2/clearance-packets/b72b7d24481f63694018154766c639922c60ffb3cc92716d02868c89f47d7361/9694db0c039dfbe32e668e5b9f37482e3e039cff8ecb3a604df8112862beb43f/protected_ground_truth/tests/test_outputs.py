"""Verifier for the tdbenefit repair (temporary disability benefits manual TD-7).

Before any candidate code runs, the delivered driver's bytes are recorded, the verifier's own copy
(tests/shipped/app/tools/tdbenefit_run.py) is os.replace-d onto /app/tools/tdbenefit_run.py, and all of
/app is made root-owned and unwritable by others. Every job is then run through the documented command,
python3 /app/tools/tdbenefit_run.py JOB.json, as an unprivileged user in its own session with an isolated
interpreter, from a fresh directory, on a file with the same neutral name for every job. Expected
statements were written ahead of time by solution/seal.py from an independent model of the manual and are
read from tests/expected/, whose SHA-256 sums and row counts are pinned in tests/expected/ROSTER; four
claims whose rate a single row figure decides are worked by hand in this file. For the
two cases the manual leaves to today's code, a copy of the shipped package, owned by its own user and closed
to everyone else, is also run on job pairs as a differential. Jobs with fresh figures are also drawn at run
time and graded against tests/manual_model.py, a copy of that independent model. One test per rule; each
compares the complete statements of every job in its family, type-strictly.
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

import manual_model

TESTS = Path(__file__).resolve().parent
EXPECTED = TESTS / "expected"
SHIPPED_APP = TESTS / "shipped" / "app"
SHIPPED_DRIVER = SHIPPED_APP / "tools" / "tdbenefit_run.py"
DELIVERED_DRIVER = Path("/app/tools/tdbenefit_run.py")
CANDIDATE_UID = 65534
SHIPPED_UID = 65533
ENV = ["/usr/bin/env", "-i", "PATH=/usr/local/bin:/usr/bin:/bin", "HOME=/nonexistent", "LANG=C.UTF-8", "PYTHONDONTWRITEBYTECODE=1"]
DEADLINE = time.monotonic() + 1500
FIELDS = {"claim", "aww", "rate", "waiting_days", "retro_days", "ttd_days", "ttd", "tpd_weeks", "tpd", "total"}
# Fresh labels for relabelled jobs; printed in every failure message that uses them.
RELABEL_SEED = int.from_bytes(os.urandom(8), "big")
WEEKS_PAY = 2_000
PARTIAL_WEEK = 1_000
# Families allowed to carry an input the manual leaves to today's code; every other family carries none.
TRAP_INPUTS = {
    "corrections": {"correction"},
    "differential-corrections": {"correction"},
    "low_partial_weeks": {"low_week"},
    "differential-low_partial_weeks": {"low_week"},
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
    staged = DELIVERED_DRIVER.with_name(".tdbenefit_run.verifier")
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
    uid, driver = (SHIPPED_UID, str(SHIPPED_RUN / "app" / "tools" / "tdbenefit_run.py")) if shipped else (CANDIDATE_UID, str(DELIVERED_DRIVER))
    code, out, err = run_as(uid, ["python3", "-I", "-S", driver, path], work, remaining)
    shutil.rmtree(stage, ignore_errors=True)
    shutil.rmtree(work, ignore_errors=True)
    assert code == 0, f"driver exited {code}: {err[-2000:]}"
    return json.loads(out)


def day(text):
    return date.fromisoformat(text)


def sunday(d):
    return d + timedelta(days=6 - d.weekday())


def base_weeks(injury):
    s = sunday(day(injury))
    return {s - timedelta(days=7 * k) for k in range(1, 14)}


def within_limits(job):
    """Manual section 1, every limit including its ends: each graded job must keep to it."""
    lo, hi = date(2016, 1, 1), date(2035, 12, 31)
    rates, claims = job["rates"], job["claims"]
    assert 1 <= len(rates) <= 40 and 1 <= len(claims) <= 200
    for k, row in enumerate(rates):
        assert lo <= day(row["from"]) <= hi and 20_000 <= row["max"] <= 400_000 and 1_000 <= row["min"] < row["max"]
        assert k == 0 or day(row["from"]) > day(rates[k - 1]["from"])
    assert len({c["claim"] for c in claims}) == len(claims)
    for c in claims:
        inj = day(c["injury"])
        assert isinstance(c["claim"], str) and 1 <= len(c["claim"]) <= 24 and lo <= inj <= hi and inj >= day(rates[0]["from"])
        assert len(c["wages"]) <= 120
        paydays = [p for p, cents in c["wages"] if cents >= WEEKS_PAY]
        assert len(paydays) == len(set(paydays)), "1.4: one line of a week's wages per payday"
        for paid, cents in c["wages"]:
            d = day(paid)
            assert lo <= d <= hi and d.weekday() == 4 and inj - timedelta(days=400) <= d <= inj + timedelta(days=30)
            assert type(cents) is int and 1 <= cents <= 500_000
        assert 1 <= len(c["disability"]) <= 12
        prev = None
        for first, last in c["disability"]:
            f, end = day(first), day(last)
            assert lo <= f <= end <= hi and end < f + timedelta(days=400)
            assert f >= inj if prev is None else f > prev
            prev = end
        assert len(c["earnings"]) <= 104
        prevw = None
        for week, earned in c["earnings"]:
            w = day(week)
            assert lo <= w <= hi and w.weekday() == 6 and type(earned) is int and 0 <= earned <= 500_000
            assert w - timedelta(days=6) > prev and (prevw is None or w > prevw)
            prevw = w


def trap_inputs(job):
    """correction: a line below a week's pay on a payday whose week and the week before it fall on different
    sides of the base period's edge; low_week: a week of the partial earnings below 1,000 cents."""
    out = set()
    for c in job["claims"]:
        weeks = base_weeks(c["injury"])
        for paid, cents in c["wages"]:
            w = sunday(day(paid))
            if cents < WEEKS_PAY and (w in weeks) != (w - timedelta(days=7) in weeks):
                out.add("correction")
        if any(e < PARTIAL_WEEK for _w, e in c["earnings"]):
            out.add("low_week")
    return out


def load(name):
    """Rows of one family; fails when the file, its digest or its count differ from the roster, or a job
    breaks the section 1 limits or carries an input its family does not declare."""
    digest, count = ROSTER[f"{name}.jsonl"]
    raw = (EXPECTED / f"{name}.jsonl").read_bytes()
    assert hashlib.sha256(raw).hexdigest() == digest, f"{name} does not match the roster"
    rows = [json.loads(line) for line in raw.decode().splitlines() if line]
    assert len(rows) == count, f"{name}: {len(rows)} rows, roster says {count}"
    allowed = TRAP_INPUTS.get(name, set())
    for row in rows:
        for job in [row[k] for k in ("job", "a", "b") if k in row]:
            within_limits(job)
            carried = trap_inputs(job)
            assert carried <= allowed, f"{name}: a job carries {carried}"
            if allowed and "job" in row:
                assert carried, f"{name}: a job carries none of its inputs"
    return rows


def compare(actual, expected, label):
    """The whole output: one key, statements in job order, each with exactly the README's keys, every value
    but the claim number an integer (a float or a boolean is not), all equal to the expected ones."""
    assert isinstance(actual, dict) and list(actual) == ["statements"], f"{label}: top-level keys {list(actual) if isinstance(actual, dict) else actual!r}"
    got, want = actual["statements"], expected["statements"]
    assert isinstance(got, list) and len(got) == len(want), f"{label}: {len(got) if isinstance(got, list) else got!r} statements, expected {len(want)}"
    for index, (row, ref) in enumerate(zip(got, want)):
        where = f"{label} statement {index} ({ref['claim']!r})"
        assert isinstance(row, dict) and set(row) == FIELDS, f"{where}: keys {sorted(row) if isinstance(row, dict) else row!r}"
        for key in sorted(FIELDS):
            assert type(row[key]) is type(ref[key]) and row[key] == ref[key], f"{where} {key}: {row[key]!r}, expected {ref[key]!r}"


def check_family(name):
    for number, row in enumerate(load(name)):
        compare(run(row["job"]), row["statements"], f"{name} job {number}")


def test_rule_3_1_weeks_pay_counts_toward_the_week_it_pays():
    """A week's pay counts toward the week before its payday's week, for injuries on every day of the week."""
    check_family("weeks_pay")


def test_rule_2_2_line_of_exactly_2000_cents_is_a_weeks_pay():
    """A line of exactly 2,000 cents on an edge payday is a week's pay and moves to the week it pays."""
    check_family("weeks_pay_threshold")


def test_rule_2_3_base_period_ends_before_the_week_of_injury():
    """The base period is the thirteen weeks before the week of injury; wages outside it do not count."""
    check_family("base_period")


def test_rule_3_3_average_weekly_wage_divides_by_thirteen():
    """The base-period wages are divided by thirteen whether one, five, nine, twelve or thirteen weeks were paid."""
    check_family("average_weekly_wage")


def test_rule_3_3_no_week_paid_gives_nought():
    """With nothing counting toward the base period the average weekly wage, rate and amounts are nought."""
    check_family("no_base_wages")


def test_rule_3_4_rate_is_two_thirds():
    """The weekly rate is two thirds of the average weekly wage, and so is a partial week's share of its loss."""
    check_family("rate_two_thirds")


def test_rule_3_4_maximum_and_minimum_bound_the_rate():
    """Two thirds of the average weekly wage at, above and below the maximum and the minimum."""
    check_family("rate_bounds")


def test_rule_2_4_row_in_force_on_the_date_of_injury():
    """The maximum and minimum come from the row in force on the date of injury: the day before, on and after a change."""
    check_family("row_in_force")


def test_rule_3_5_low_wage_rate_is_the_aww():
    """An average weekly wage below the minimum is itself the weekly rate; one at the minimum is not below it."""
    check_family("low_wage_rate")


def test_rule_2_5_both_ends_of_a_period_count():
    """Disability days include the first and last day of every period: one-day periods, 399 days, twelve periods."""
    check_family("disability_days")


def test_rule_2_6_three_waiting_days():
    """The waiting period is the first three disability days, or all of them when there are fewer."""
    check_family("waiting_period")


def test_rule_4_1_retroactive_from_fourteen_days():
    """The waiting days are paid back from fourteen disability days (13, 14 in one and three periods, 15)."""
    check_family("retroactive_days")


def test_rule_4_3_amount_rounded_to_the_cent():
    """The total-disability amount is rate times paid days over seven, to the nearest cent (every remainder)."""
    check_family("ttd_rounding")


def test_rule_5_1_partial_week_pays_two_thirds_capped_at_the_rate():
    """A week of partial disability pays two thirds of its wage loss, no more than the weekly rate."""
    check_family("partial_benefit")


def test_rule_2_8_week_of_exactly_1000_cents_is_partial_disability():
    """A week earning exactly 1,000 cents is a week of partial disability."""
    check_family("partial_week_threshold")


def test_rule_2_7_week_earning_the_aww_has_no_wage_loss():
    """A week earning the average weekly wage or more has no wage loss."""
    check_family("no_wage_loss")


def test_correction_below_a_weeks_pay_keeps_its_paydays_week():
    """A line below a week's pay keeps counting toward its payday's week, as the shipped package counts it."""
    check_family("corrections")
    for number, row in enumerate(load("differential-corrections")):
        shipped = [run(row[k], shipped=True)["statements"][0]["aww"] for k in ("a", "b")]
        candidate = [run(row[k])["statements"][0]["aww"] for k in ("a", "b")]
        assert shipped[0] == shipped[1], f"pair {number}: the shipped step is not the same in both"
        assert candidate[0] == candidate[1], f"pair {number}: average weekly wage {candidate[1]!r} with the line on an edge payday, {candidate[0]!r} without it"


def test_week_below_1000_cents_keeps_todays_share():
    """A week of the partial earnings below 1,000 cents keeps the share the shipped package pays it."""
    check_family("low_partial_weeks")
    # Jobs whose AWW and weekly rate today's code and the manual agree on, every partial week under 1,000 cents:
    # the shipped package's partial amount (capped at the rate, or 3/5 rounded to the cent) is the answer.
    for number, row in enumerate(load("differential-low_partial_weeks")):
        shipped = run(row["job"], shipped=True)["statements"][0]
        candidate = run(row["job"])["statements"][0]
        assert (candidate["aww"], candidate["rate"]) == (shipped["aww"], shipped["rate"]), f"job {number}: AWW and rate differ from the shipped package's"
        assert candidate["tpd"] == shipped["tpd"], f"job {number}: partial amount {candidate['tpd']!r}, the shipped package pays {shipped['tpd']!r}"


# Claim numbers are any string of 1 to 24 characters (manual 1.3): one character, twenty-four, spaces at either
# end, punctuation, quotes, backslashes and characters outside ASCII, each ending in a fresh draw.
NAME_FORMS = [
    lambda tail: tail[:1],
    lambda tail: ("C" * 24 + tail)[-24:],
    lambda tail: " " + tail[:6] + " ",
    lambda tail: 'W"\\/' + tail[:8],
    lambda tail: "é事故-" + tail[:10],
]


def fresh_names(rng, count):
    """count distinct claim numbers cycling through NAME_FORMS (a taken one-character name becomes two)."""
    names = []
    while len(names) < count:
        tail = "".join(rng.choice("ABCDEFGHJKLMNPQRSTUVWXYZ0123456789") for _ in range(24))
        name = NAME_FORMS[len(names) % len(NAME_FORMS)](tail)
        if name in names:
            name = tail[:2]
        if name not in names:
            names.append(name)
    return names


def relabel(job, statements, rng):
    """The same job under fresh claim numbers, claims shuffled and each claim's wage lines shuffled (the README
    puts them in no particular order); the expected statements follow with the same labels and order."""
    job, statements = copy.deepcopy(job), copy.deepcopy(statements)
    order = list(range(len(job["claims"])))
    rng.shuffle(order)
    names = fresh_names(rng, len(order))
    claims, rows = [], []
    for name, index in zip(names, order):
        claim = dict(job["claims"][index], claim=name)
        claim["wages"] = list(claim["wages"])
        rng.shuffle(claim["wages"])
        claims.append(claim)
        rows.append(dict(statements["statements"][index], claim=name))
    return dict(job, claims=claims), {"statements": rows}


def test_statement_order_and_keys():
    """Statements come in job order with claim numbers as given, exactly the README's keys, integer figures."""
    check_family("statement_order")


def test_section_one_limits_reached():
    """40 rate rows, 200 claims, 120 wage lines, 12 periods, 104 partial weeks, 1 and 500,000 cents, 2016 and 2035."""
    check_family("limits_claims")
    row = load("limits_job")[0]
    job, statements = row["job"], row["statements"]
    rng = random.Random(RELABEL_SEED)
    names = fresh_names(rng, 200)
    claims = [dict(job["claims"][k % len(job["claims"])], claim=names[k]) for k in range(200)]
    rows = [dict(statements["statements"][k % len(job["claims"])], claim=names[k]) for k in range(200)]
    big = dict(job, claims=claims)
    within_limits(big)
    assert len(big["rates"]) == 40 and len(big["claims"]) == 200
    compare(run(big), {"statements": rows}, f"limits job of 200 claims (seed {RELABEL_SEED})")


def _worked(name, injury, lines, aww, rate):
    """One claim, one disability day on the date of injury, no earnings; its statement worked by hand."""
    claim = {"claim": name, "injury": injury, "wages": [list(line) for line in lines], "disability": [[injury, injury]], "earnings": []}
    statement = {"claim": name, "aww": aww, "rate": rate, "waiting_days": 1, "retro_days": 0, "ttd_days": 0, "ttd": 0,
                 "tpd_weeks": 0, "tpd": 0, "total": 0}
    return claim, statement


def _figures_jobs():
    daily = [{"from": (date(2035, 11, 22) + timedelta(days=k)).isoformat(), "max": 400_000, "min": 1_000} for k in range(40)]
    daily[-1]["max"] = 20_000
    return [
        # 2.4 over all 40 rows: the row taking effect on 2035-12-31 is in force; 500,000 / 13 = 38,462, two thirds 25,641
        (daily, [_worked("R40", "2035-12-31", [("2035-12-28", 500_000)], 38_462, 20_000)]),
        # 3.4 with a 20,000 maximum: 390,013 / 13 = 30,001, two thirds 20,001, held at 20,000; and a 1,000 minimum
        # lifting two thirds of 1,200 (800), which is not below the minimum's 3.5 test
        ([{"from": "2016-01-01", "max": 20_000, "min": 1_000}],
         [_worked("MAX", "2025-04-07", [("2025-04-04", 390_013)], 30_001, 20_000),
          _worked("MIN", "2025-04-07", [("2025-04-04", 15_600)], 1_200, 1_000)]),
        # 3.4 with a 100,001 minimum: 1,300,013 / 13 = 100,001, two thirds 66,667, lifted to 100,001
        ([{"from": "2016-01-01", "max": 400_000, "min": 100_001}],
         [_worked("HIMIN", "2025-04-07", [("2025-03-21", 500_000), ("2025-03-28", 500_000), ("2025-04-04", 300_013)], 100_001, 100_001)]),
    ]


def test_rule_3_4_row_figures_at_their_ends_decide_the_rate():
    """The fortieth row in force, a 20,000 maximum, a 1,000 minimum and a 100,001 minimum each set the weekly rate."""
    for number, (rates, worked) in enumerate(_figures_jobs()):
        job = {"rates": rates, "claims": [c for c, _s in worked]}
        within_limits(job)
        assert not trap_inputs(job)
        compare(run(job), {"statements": [s for _c, s in worked]}, f"hand-worked row-figure job {number}")


def test_generated_jobs():
    """Seeded jobs over the governed domain, as sealed and under fresh claim numbers and orders."""
    check_family("generated")
    rng = random.Random(RELABEL_SEED)
    for number, row in enumerate(load("generated")):
        job, expected = relabel(row["job"], row["statements"], rng)
        within_limits(job)
        compare(run(job), expected, f"generated job {number} relabelled (seed {RELABEL_SEED})")


def _unreadable_by_candidate(target):
    probe = f"import os,sys\ntry:\n    os.listdir({target!r}) if os.path.isdir({target!r}) else open({target!r}).read()\nexcept OSError:\n    sys.exit(0)\nsys.exit(1)"
    code, _, _ = run_as(CANDIDATE_UID, ["python3", "-I", "-S", "-c", probe], "/", 60)
    return code == 0


def test_candidate_cannot_read_verifier_state():
    """The candidate's user cannot read /tests, the expectations, the shipped copy or /logs/verifier."""
    for target in ["/tests", str(EXPECTED / "ROSTER"), str(SHIPPED_RUN), str(SHIPPED_RUN / "app" / "tools" / "tdbenefit_run.py"), "/logs/verifier"]:
        assert _unreadable_by_candidate(target), f"the candidate's user can read {target}"
    assert not _unreadable_by_candidate("/app/README.md"), "control: the probe cannot read a world-readable file"


def test_submitted_driver_unchanged():
    """The delivered driver matches the shipped one, and is still the verifier's copy after every run."""
    assert DELIVERED_BYTES == SHIPPED_DRIVER.read_bytes(), "the delivered /app/tools/tdbenefit_run.py differs from the shipped driver"
    assert DELIVERED_DRIVER.read_bytes() == SHIPPED_DRIVER.read_bytes(), "the driver on the documented path changed during the run"
    for path in [DELIVERED_DRIVER, DELIVERED_DRIVER.parent, DELIVERED_DRIVER.parent.parent]:
        info = path.lstat()
        assert info.st_uid == 0 and not info.st_mode & 0o022, f"{path} is writable by the candidate's user"


def test_register_of_more_than_52_distinct_paydays():
    """1.4 allows a register of every Friday for 400 days before the injury to 30 after: 53 and 57 distinct
    paydays of 2,000 cents, 12 and 13 of them counting toward the base period, worked by hand."""
    rates = [{"from": "2016-01-01", "max": 400_000, "min": 1_000}]
    for lines, aww, rate in [(53, 1_846, 1_231), (57, 2_000, 1_333)]:
        paydays = [((date(2024, 1, 5) + timedelta(days=7 * k)).isoformat(), 2_000) for k in range(lines)]
        claim, statement = _worked(f"SPAN{lines}", "2025-01-06", paydays, aww, rate)
        job = {"rates": rates, "claims": [claim]}
        within_limits(job)
        assert not trap_inputs(job) and len({p for p, _c in claim["wages"]}) == lines
        assert manual_model.statements(job) == {"statements": [statement]}
        compare(run(job), {"statements": [statement]}, f"register of {lines} distinct paydays")


# Figures drawn afresh on every run, so no sealed statement can stand in for the calculation.
DRAW_SEED = int.from_bytes(os.urandom(8), "big")


def _draw_job(rng):
    """One job inside section 1 carrying neither input the manual leaves to today's code: fresh rate rows,
    injuries on any weekday, registers from empty to every Friday in the window (up to 62 distinct paydays),
    small non-edge corrections, 1 to 12 periods and partial weeks of 1,000 to 500,000 cents or none."""
    lo = date(2016, 1, 1)
    count = rng.randint(1, 40)
    starts = sorted(rng.sample(range(0, 4_000), count))
    rates = []
    for k in starts:
        top = rng.randint(20_000, 400_000)
        rates.append({"from": (lo + timedelta(days=k)).isoformat(), "max": top, "min": rng.randint(1_000, top - 1)})
    first = day(rates[0]["from"])
    claims = []
    for name in fresh_names(rng, rng.randint(20, 60)):
        # The first claim is injured late enough that its whole 431-day window lies after 2016-01-01.
        earliest = first if claims else max(first, date(2017, 2, 6))
        inj = earliest + timedelta(days=rng.randint(0, (date(2031, 6, 30) - earliest).days))
        window = [d for d in (inj - timedelta(days=400) + timedelta(days=k) for k in range(431))
                  if d.weekday() == 4 and lo <= d]
        shape = rng.random() if claims else 0.3  # the first claim of every job is paid every Friday of its window
        if shape < 0.1:
            fridays = []
        elif shape < 0.5:
            fridays = window
        else:
            fridays = sorted(rng.sample(window, rng.randint(1, len(window))))
        scale = rng.choice([2_000, 30_000, 150_000, 500_000])
        wages = [[d.isoformat(), rng.randint(2_000, scale)] for d in fridays]
        weeks = base_weeks(inj.isoformat())
        for d in rng.sample(window, min(len(window), rng.randint(0, 6))):
            w = sunday(d)
            if (w in weeks) == (w - timedelta(days=7) in weeks) and len(wages) < 120:
                wages.append([d.isoformat(), rng.randint(1, 1_999)])
        rng.shuffle(wages)
        periods, start = [], inj + timedelta(days=rng.randint(0, 10))
        for _ in range(rng.randint(1, 12)):
            length = rng.choice([1, 2, 3, 4, 13, 14, 15, rng.randint(1, 60)])
            periods.append([start.isoformat(), (start + timedelta(days=length - 1)).isoformat()])
            start += timedelta(days=length + rng.randint(1, 20))
        earnings, week = [], sunday(day(periods[-1][1])) + timedelta(days=7)
        for _ in range(rng.choice([0, 0, rng.randint(1, 30)])):
            earnings.append([week.isoformat(), rng.randint(1_000, rng.choice([5_000, 100_000, 500_000]))])
            week += timedelta(days=7 * rng.randint(1, 3))
        claims.append({"claim": name, "injury": inj.isoformat(), "wages": wages, "disability": periods, "earnings": earnings})
    return {"rates": rates, "claims": claims}


def test_jobs_drawn_at_run_time():
    """Jobs with every figure and date drawn on this run, graded against the verifier's copy of the model."""
    rng = random.Random(DRAW_SEED)
    for number in range(4):
        job = _draw_job(rng)
        within_limits(job)
        assert not trap_inputs(job), f"drawn job {number} carries {trap_inputs(job)}"
        assert len({p for p, c in job["claims"][0]["wages"] if c >= WEEKS_PAY}) > 52
        compare(run(job), manual_model.statements(job), f"drawn job {number} (seed {DRAW_SEED})")
