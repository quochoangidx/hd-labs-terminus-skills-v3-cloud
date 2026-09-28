"""Verifier for the coopsum repair (network handbook CN-7 part 3).

Before any candidate code runs, the delivered driver's bytes are recorded, the verifier's own copy
(tests/shipped/app/tools/coopsum_run.py) is os.replace-d onto /app/tools/coopsum_run.py, and all of /app is
made root-owned and unwritable by others. Every form is summarised by the documented command,
python3 /app/tools/coopsum_run.py FORM.json, as an unprivileged user in its own session with an isolated
interpreter, from a fresh directory, on a file with the same neutral name for every form. Expected summaries
were written ahead of time by solution/seal.py from an independent model of the handbook and are read from
tests/expected/ (each entry stored as "MAX MIN PRECIP", each station's figures in KEYS order), whose SHA-256
sums and row counts are pinned in tests/expected/ROSTER. For the two places where the handbook leaves a
reading or a month to what the package does today, a copy of the shipped package, owned by its own user and
closed to everyone else, is run as a differential. One test per rule; each compares the complete summary of
every form in its family. The generated family is also summarised under fresh labels drawn at run time
(network name, station ids, station order), which leave every figure unchanged.
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
SHIPPED_DRIVER = SHIPPED_APP / "tools" / "coopsum_run.py"
DELIVERED_DRIVER = Path("/app/tools/coopsum_run.py")
CANDIDATE_UID = 65534
SHIPPED_UID = 65533
ENV = ["/usr/bin/env", "-i", "PATH=/usr/local/bin:/usr/bin:/bin", "HOME=/nonexistent", "LANG=C.UTF-8", "PYTHONDONTWRITEBYTECODE=1"]
DEADLINE = time.monotonic() + 1500
RELABEL_SEED = int.from_bytes(os.urandom(8), "big")
KEYS = ["id", "complete", "lacking_max", "lacking_min", "mean_max", "mean_min", "mean", "highest", "highest_day",
        "lowest", "lowest_day", "heating_dd", "cooling_dd", "days_max_90", "days_max_32", "days_min_32",
        "days_min_0", "precip", "precip_days", "precip_days_10", "precip_days_100", "greatest", "greatest_day"]
INTEGER_KEYS = {"lacking_max", "lacking_min", "heating_dd", "cooling_dd", "days_max_90", "days_max_32", "days_min_32",
                "days_min_0", "precip_days", "precip_days_10", "precip_days_100"}
NUMBER_KEYS = {"mean_max", "mean_min", "mean", "highest", "lowest", "precip", "greatest"}
PRECIP_KEYS = ["precip", "precip_days", "precip_days_10", "precip_days_100", "greatest", "greatest_day"]
# Families allowed to carry an input the handbook leaves to today's code; every other family carries none.
TRAP_INPUTS = {"accumulated_morning": {"accumulated_at_morning"}, "gappy_months": {"gap_count_above_five"}}


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
    staged = DELIVERED_DRIVER.with_name(".coopsum_run.verifier")
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


def summarize(form, shipped=False):
    """Run the driver on one form (the candidate's package, or the shipped copy); return its parsed stdout."""
    stage = tempfile.mkdtemp()
    work = tempfile.mkdtemp()
    os.chmod(stage, 0o755)
    os.chmod(work, 0o777)
    path = os.path.join(stage, "form.json")
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(form, handle)
    os.chmod(path, 0o644)
    remaining = DEADLINE - time.monotonic()
    assert remaining > 0, "verifier time budget exhausted"
    uid, driver = (SHIPPED_UID, str(SHIPPED_RUN / "app" / "tools" / "coopsum_run.py")) if shipped else (CANDIDATE_UID, str(DELIVERED_DRIVER))
    code, out, err = run_as(uid, ["python3", "-I", "-S", driver, path], work, remaining)
    shutil.rmtree(stage, ignore_errors=True)
    shutil.rmtree(work, ignore_errors=True)
    assert code == 0, f"driver exited {code}: {err[-2000:]}"
    return json.loads(out)


def entry(text):
    high, low, precip = text.split(" ")
    return {"max": high, "min": low, "precip": precip}


def expand(row):
    """The sealed compact form in the README's layout, and the summary as section 6 lays it out."""
    f = row["form"]
    form = {"network": f["network"], "month": f["month"], "stations": [
        {"id": s["id"], "hour": s["hour"], "days": [entry(e) for e in s["days"]], "next": entry(s["next"])}
        for s in f["stations"]]}
    s = row["summary"]
    summary = {"network": s["network"], "month": s["month"], "stations": [dict(zip(KEYS, v)) for v in s["stations"]]}
    return form, summary


def days_in(month):
    year, mon = int(month[:4]), int(month[5:])
    return [31, 29 if year % 4 == 0 and (year % 100 or year % 400 == 0) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][mon - 1]


def tenths(text):
    whole, frac = text.lstrip("-").split(".")
    assert whole.isdigit() and len(frac) == 1 and frac.isdigit(), text
    return (-1 if text.startswith("-") else 1) * (int(whole) * 10 + int(frac))


def within_limits(form):
    """Handbook 1.5, every limit including its ends: each graded form must keep to it."""
    assert "1950-01" <= form["month"] <= "2099-12" and len(form["month"]) == 7
    stations = form["stations"]
    assert 1 <= len(stations) <= 40 and len({s["id"] for s in stations}) == len(stations)
    for s in stations:
        assert type(s["hour"]) is int and 0 <= s["hour"] <= 23
        assert len(s["days"]) == days_in(form["month"])
        entries = s["days"] + [s["next"]]
        run = 0
        for k, e in enumerate(entries):
            for key in ("max", "min"):
                assert e[key] == "M" or -600 <= tenths(e[key]) <= 1300, e[key]
            p = e["precip"]
            if p == "A":
                run += 1
                assert run <= 6 and k < len(entries) - 1
                continue
            assert not (run and p == "M")
            run = 0
            if p not in ("M", "T"):
                whole, frac = p.split(".")
                assert whole.isdigit() and len(frac) == 2 and frac.isdigit() and 0 <= int(whole) * 100 + int(frac) <= 2000, p


def accumulated(station):
    """Positions (0-based in days + next) of the amounts entered after unread (A) observations (1.3)."""
    out, unread = [], False
    for k, e in enumerate(station["days"] + [station["next"]]):
        if e["precip"] == "A":
            unread = True
            continue
        if unread:
            out.append(k)
        unread = False
    return out


def gap_count(station, month):
    n = days_in(month)
    shift = 1 if station["hour"] <= 11 else 0
    entries = station["days"] + [station["next"]]
    highs = {k + 1 - shift for k, e in enumerate(entries) if e["max"] != "M"}
    lows = {k + 1 for k, e in enumerate(entries) if e["min"] != "M"}
    return max(n - len(highs & set(range(1, n + 1))), n - len(lows & set(range(1, n + 1))))


def trap_inputs(form):
    out = set()
    for s in form["stations"]:
        if s["hour"] <= 11 and accumulated(s):
            out.add("accumulated_at_morning")
        if gap_count(s, form["month"]) > 5:
            out.add("gap_count_above_five")
    return out


def load(name):
    """Rows of one family; fails when the file, its digest or its count differ from the roster, or a form
    breaks the section 1.5 limits or carries an input its family does not declare."""
    digest, count = ROSTER[f"{name}.jsonl"]
    raw = (EXPECTED / f"{name}.jsonl").read_bytes()
    assert hashlib.sha256(raw).hexdigest() == digest, f"{name} does not match the roster"
    rows = [expand(json.loads(line)) for line in raw.decode().splitlines() if line]
    assert len(rows) == count, f"{name}: {len(rows)} rows, roster says {count}"
    for form, _ in rows:
        within_limits(form)
        assert trap_inputs(form) == TRAP_INPUTS.get(name, set()), f"{name}: {form['month']} carries {trap_inputs(form)}"
    return rows


def _value(actual, expected, where):
    if expected is None or isinstance(expected, (bool, str)):
        assert type(actual) is type(expected) and actual == expected, f"{where}: {actual!r}, expected {expected!r}"
    elif where.rsplit(" ", 1)[-1] in INTEGER_KEYS:
        assert type(actual) is int and actual == expected, f"{where}: {actual!r}, expected the integer {expected!r}"
    else:
        assert isinstance(actual, (int, float)) and not isinstance(actual, bool) and actual == expected, f"{where}: {actual!r}, expected {expected!r}"


def compare(actual, expected, label, keys=KEYS):
    assert isinstance(actual, dict) and set(actual) >= {"network", "month", "stations"}, f"{label}: top-level keys"
    for key in ("network", "month"):
        _value(actual[key], expected[key], f"{label} {key}")
    got, want = actual["stations"], expected["stations"]
    assert isinstance(got, list) and len(got) == len(want), f"{label}: {len(got) if isinstance(got, list) else got!r} stations, expected {len(want)}"
    for index, (row, ref) in enumerate(zip(got, want)):
        assert isinstance(row, dict) and set(row) >= set(keys), f"{label} station {index}: keys {sorted(row) if isinstance(row, dict) else row!r}"
        for key in keys:
            _value(row[key], ref[key], f"{label} station {index} ({ref['id']}) {key}")


def check_family(name):
    for form, summary in load(name):
        compare(summarize(form), summary, f"{name} {form['month']}")


def test_rule_1_2_trace_counts_nought():
    """A trace adds nothing to a day, a month or a count, also in a month of traces only."""
    check_family("traces")


def test_rule_2_2_hour_eleven_is_morning_and_noon_is_not():
    """Observations at hours 0 and 11 are morning observations; 12 and 23 are afternoon ones."""
    check_family("hour_edges")


def test_rule_3_1_morning_maximum_on_the_day_before():
    """A morning maximum goes to the day before its form day (next's to the last day); minima stay put."""
    check_family("morning_maximum")


def test_rule_3_3_morning_precipitation_on_the_day_before():
    """A day's precipitation at a morning observation goes to the day before, also after a lost (M) reading."""
    check_family("morning_precipitation")


def test_rule_2_7_gap_count_from_credited_days():
    """Lacking days and the gap count come from the credited days; a gap count of five is well-observed."""
    check_family("gap_count")


def test_rule_4_1_means_to_tenths_half_up():
    """Mean maximum and minimum to tenths, an exact half going to the higher tenth, below nought too."""
    check_family("means")


def test_rule_4_2_tied_extremes_take_the_latest_day():
    """A highest or lowest temperature reached on two days is given with the later day."""
    check_family("tied_temperatures")


def test_rule_4_3_mean_of_a_well_observed_month():
    """A well-observed month's mean is the average of its mean maximum and mean minimum."""
    check_family("well_observed_mean")


def test_rule_4_4_degree_days_from_the_rounded_daily_mean():
    """Each day's mean is rounded to the whole degree before the 65 F base; halves both sides of nought."""
    check_family("degree_days")


def test_rule_4_5_threshold_days_include_their_value():
    """Maxima of 90.0 and 32.0 and minima of 32.0 and 0.0 are counted; a tenth away is not."""
    check_family("thresholds")


def test_rule_5_3_heavy_days_include_their_threshold():
    """Days of exactly 0.10 and 1.00 inch count toward the heavier counts; 0.09 and 0.99 do not."""
    check_family("heavy_days")


def test_rule_5_4_tied_greatest_takes_the_latest_day():
    """A greatest precipitation reached on two days is given with the later day."""
    check_family("tied_precipitation")


def test_accumulated_amount_keeps_its_form_day():
    """The catch entered after unread observations at a morning station stays on the day the package credits
    it today: the full summaries, and the shipped differential on the precipitation figures."""
    check_family("accumulated_morning")
    for form, _ in load("accumulated_morning"):
        alone = copy.deepcopy(form)
        for s in alone["stations"]:
            keep = set(accumulated(s))
            for k, e in enumerate(s["days"] + [s["next"]]):
                if k not in keep and e["precip"] not in ("A", "M"):
                    e["precip"] = "0.00"
        want, got = summarize(alone, shipped=True), summarize(alone)
        compare(got, want, f"accumulated_morning differential {form['month']}", PRECIP_KEYS)


def test_month_with_gaps_keeps_its_mean_of_daily_means():
    """A month with a gap count above five keeps the package's mean temperature, the mean of its days' means:
    the full summaries, and the shipped differential on `mean` with every station read in the afternoon."""
    check_family("gappy_months")
    for form, _ in load("gappy_months"):
        afternoon = copy.deepcopy(form)
        for s in afternoon["stations"]:
            s["hour"] = 17
        want, got = summarize(afternoon, shipped=True), summarize(afternoon)
        compare(got, want, f"gappy_months differential {form['month']}", ["id", "mean"])


def test_section_one_limits_reached():
    """Forty stations, February of a leap year, 1950-01 and 2099-12, -60.0 and 130.0, 20.00 inches, six unread days."""
    rows = load("limits")
    assert len(rows[0][0]["stations"]) == 40
    check_family("limits")


# Network names for the relabelled forms: empty, edge spaces, quotes, a backslash, non-ASCII and a very long one.
NAME_FORMS = ["", "  spaced  ", "Réseau \"Est\" \\ 2 ", "N" * 300, "Station-Netz S\u00fcd \u2014 "]


def relabel(form, summary, rng, number):
    """The same form under a fresh network name (NAME_FORMS in turn), fresh station ids and a shuffled
    station order in which the ids run from highest to lowest, so no order is sorted by id."""
    form, summary = copy.deepcopy(form), copy.deepcopy(summary)
    order = list(range(len(form["stations"])))
    rng.shuffle(order)
    ids = set()
    while len(ids) < len(order):
        ids.add("".join(rng.choice("ABCDEFGHJKLMNPQRSTUVWXYZ0123456789-") for _ in range(12)))
    stations, rows = [], []
    for new_id, index in zip(sorted(ids, reverse=True), order):
        stations.append(dict(form["stations"][index], id=new_id))
        rows.append(dict(summary["stations"][index], id=new_id))
    name = NAME_FORMS[number % len(NAME_FORMS)] + str(rng.randint(0, 10 ** 6))
    return dict(form, network=name, stations=stations), dict(summary, network=name, stations=rows)


def test_generated_forms():
    """Seeded forms over the rest of the handbook's domain, as sealed and under fresh labels."""
    check_family("generated")
    rng = random.Random(RELABEL_SEED)
    for number, (form, summary) in enumerate(load("generated")):
        f2, s2 = relabel(form, summary, rng, number)
        compare(summarize(f2), s2, f"generated {form['month']} relabelled (seed {RELABEL_SEED})")


def _unreadable_by_candidate(target):
    probe = f"import os,sys\ntry:\n    os.listdir({target!r}) if os.path.isdir({target!r}) else open({target!r}).read()\nexcept OSError:\n    sys.exit(0)\nsys.exit(1)"
    code, _, _ = run_as(CANDIDATE_UID, ["python3", "-I", "-S", "-c", probe], "/", 60)
    return code == 0


def test_candidate_cannot_read_verifier_state():
    """The candidate's user cannot read /tests, the expectations, the shipped copy or /logs/verifier."""
    for target in ["/tests", str(EXPECTED / "ROSTER"), str(SHIPPED_RUN), str(SHIPPED_RUN / "app" / "tools" / "coopsum_run.py"), "/logs/verifier"]:
        assert _unreadable_by_candidate(target), f"the candidate's user can read {target}"
    assert not _unreadable_by_candidate("/app/README.md"), "control: the probe cannot read a world-readable file"


def test_submitted_driver_unchanged():
    """The delivered driver matches the shipped one, and is still the verifier's copy after every run."""
    assert DELIVERED_BYTES == SHIPPED_DRIVER.read_bytes(), "the delivered /app/tools/coopsum_run.py differs from the shipped driver"
    assert DELIVERED_DRIVER.read_bytes() == SHIPPED_DRIVER.read_bytes(), "the driver on the documented path changed during the run"
    for path in [DELIVERED_DRIVER, DELIVERED_DRIVER.parent, DELIVERED_DRIVER.parent.parent]:
        info = path.lstat()
        assert info.st_uid == 0 and not info.st_mode & 0o022, f"{path} is writable by the candidate's user"
