"""Verifier for the pdcmeasure repair (adherence measure specification AM-2).

Before any candidate code runs, the delivered driver's bytes are recorded, the verifier's own copy
(tests/shipped/app/tools/pdc_run.py) is os.replace-d onto /app/tools/pdc_run.py, and all of /app is made
root-owned and unwritable by others. Every claims file is then measured by the documented command,
python3 /app/tools/pdc_run.py CLAIMS.json, as an unprivileged user in its own session with an isolated
interpreter, from a fresh directory, on a file with the same neutral name for every job. Expected reports
were written ahead of time by solution/seal.py from an independent model of the specification and are read
from tests/expected/, whose SHA-256 sums and row counts are pinned in tests/expected/ROSTER.

One test per rule. Three figures are left by the specification to today's code: the period, covered days
and PDC of a member outside the measure, the rate of a class that is not reportable, and the days a fill
above the supply limit covers. Each is graded only in its own test (with a shipped differential where the
kept step can be isolated); the other tests compare every other figure of every report in their family.
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
from datetime import date
from pathlib import Path

TESTS = Path(__file__).resolve().parent
EXPECTED = TESTS / "expected"
SHIPPED_APP = TESTS / "shipped" / "app"
SHIPPED_DRIVER = SHIPPED_APP / "tools" / "pdc_run.py"
DELIVERED_DRIVER = Path("/app/tools/pdc_run.py")
CANDIDATE_UID = 65534
SHIPPED_UID = 65533
ENV = ["/usr/bin/env", "-i", "PATH=/usr/local/bin:/usr/bin:/bin", "HOME=/nonexistent", "LANG=C.UTF-8", "PYTHONDONTWRITEBYTECODE=1"]
DEADLINE = time.monotonic() + 1500
# Fresh labels for the relabelled generated files; printed in every failure message.
RELABEL_SEED = int.from_bytes(os.urandom(8), "big")
ROW_KEYS = ("id", "class", "index", "in_measure", "period", "covered", "pdc", "adherent")
CLASS_KEYS = ("class", "members", "in_measure", "adherent", "rate")
CODE = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
SUPPLY_LIMIT = 100
REPORTABLE = 10
MAX_MEMBERS = 100
# The figures the specification leaves to today's code that a family grades; a fill above the supply limit
# may appear only in a family that grades it, and a claim line with no days supply only in its own family.
GRADES_SILENT = {
    "outside_measure": {"outside"},
    "small_class": {"small_class"},
    "over_limit": {"over_limit"},
    "traps_combined": {"outside", "small_class", "over_limit"},
    "adjustment_lines": {"no_supply"},
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
    staged = DELIVERED_DRIVER.with_name(".pdc_run.verifier")
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


def measure(claims, shipped=False):
    """Run the driver on one claims file (the candidate's package, or the shipped copy); return its parsed stdout."""
    stage = tempfile.mkdtemp()
    work = tempfile.mkdtemp()
    os.chmod(stage, 0o755)
    os.chmod(work, 0o777)
    path = os.path.join(stage, "claims.json")
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(claims, handle)
    os.chmod(path, 0o644)
    remaining = DEADLINE - time.monotonic()
    assert remaining > 0, "verifier time budget exhausted"
    uid, driver = (SHIPPED_UID, str(SHIPPED_RUN / "app" / "tools" / "pdc_run.py")) if shipped else (CANDIDATE_UID, str(DELIVERED_DRIVER))
    code, out, err = run_as(uid, ["python3", "-I", "-S", driver, path], work, remaining)
    shutil.rmtree(stage, ignore_errors=True)
    shutil.rmtree(work, ignore_errors=True)
    assert code == 0, f"driver exited {code}: {err[-2000:]}"
    return json.loads(out)


def within_limits(claims):
    """Rule 1.3, every limit including its ends: each graded file must keep to it."""
    year = claims["year"]
    assert type(year) is int and 2000 <= year <= 2099
    members = claims["members"]
    assert isinstance(claims["plan"], str) and 1 <= len(members) <= MAX_MEMBERS
    assert len({m["id"] for m in members}) == len(members)
    fills = [f for m in members for f in m["fills"]]
    assert len({f["class"] for f in fills}) <= 40
    assert len({f["drug"] for f in fills}) == len({(f["drug"], f["class"]) for f in fills}), "a drug code under two classes"
    for m in members:
        assert 1 <= len(m["id"]) <= 12 and set(m["id"]) <= set(CODE + "-")
        assert len(m["fills"]) <= 400 and len(m["stays"]) <= 10
        for f in m["fills"]:
            assert date.fromisoformat(f["date"]).year == year
            assert 1 <= len(f["drug"]) <= 11 and set(f["drug"]) <= set("0123456789")
            assert 1 <= len(f["class"]) <= 8 and set(f["class"]) <= set(CODE)
            assert type(f["days"]) is int and 0 <= f["days"] <= 365
        days = []
        for admission, discharge in m["stays"]:
            a, b = date.fromisoformat(admission), date.fromisoformat(discharge)
            assert a.year == year == b.year and a <= b
            days += range(a.toordinal(), b.toordinal() + 1)
        assert len(days) == len(set(days)) <= 60


def over_limit(claims):
    return any(f["days"] > SUPPLY_LIMIT for m in claims["members"] for f in m["fills"])


def no_supply(claims):
    return any(f["days"] == 0 for m in claims["members"] for f in m["fills"])


def load(name, grades=frozenset()):
    """Rows of one family; fails when the file, its digest or its count differ from the roster, or a claims
    file breaks rule 1.3 or carries a fill above the supply limit into a family that does not grade it."""
    digest, count = ROSTER[f"{name}.jsonl"]
    raw = (EXPECTED / f"{name}.jsonl").read_bytes()
    assert hashlib.sha256(raw).hexdigest() == digest, f"{name} does not match the roster"
    rows = [json.loads(line) for line in raw.decode().splitlines() if line]
    assert len(rows) == count, f"{name}: {len(rows)} rows, roster says {count}"
    for row in rows:
        for claims in [row[k] for k in ("claims", "a", "b") if k in row]:
            within_limits(claims)
            assert not over_limit(claims) or "over_limit" in grades, f"{name}: {claims['plan']} has a fill above the limit"
            assert not no_supply(claims) or "no_supply" in grades, f"{name}: {claims['plan']} has a line with no days supply"
    return rows


def _same(actual, expected, where):
    assert type(actual) is type(expected) and actual == expected, f"{where}: {actual!r}, expected {expected!r}"


def _percentage(actual, expected, where):
    """A PDC or rate: the reported tenth, as a JSON number."""
    assert isinstance(actual, (int, float)) and not isinstance(actual, bool), f"{where}: {actual!r} is not a number"
    assert actual == expected, f"{where}: {actual!r}, expected {expected!r}"


def compare(actual, expected, label, grades=frozenset()):
    """Every key the README lists, compared; further keys are not part of the contract and are ignored. The
    period, covered days and PDC of a member outside the measure are compared only where ``grades`` holds
    "outside", and the rate of a class that is not reportable only where it holds "small_class"."""
    assert isinstance(actual, dict) and set(actual) >= {"plan", "year", "members", "classes"}, f"{label}: top-level keys"
    _same(actual["plan"], expected["plan"], f"{label} plan")
    _same(actual["year"], expected["year"], f"{label} year")
    for section, keys in (("members", ROW_KEYS), ("classes", CLASS_KEYS)):
        got, want = actual[section], expected[section]
        assert isinstance(got, list) and len(got) == len(want), f"{label}: {section} has {len(got) if isinstance(got, list) else got!r} rows, expected {len(want)}"
        for index, (row, ref) in enumerate(zip(got, want)):
            where = f"{label} {section}[{index}] ({ref.get('id', '')} {ref['class']})"
            assert isinstance(row, dict) and set(row) >= set(keys), f"{where}: keys {row!r}"
            for key in keys:
                if section == "members" and key in ("period", "covered", "pdc") and not ref["in_measure"] and "outside" not in grades:
                    continue
                if section == "classes" and key == "rate" and ref["in_measure"] < REPORTABLE and "small_class" not in grades:
                    continue
                if key in ("pdc", "rate"):
                    _percentage(row[key], ref[key], f"{where} {key}")
                else:
                    _same(row[key], ref[key], f"{where} {key}")


def check_family(name):
    grades = GRADES_SILENT.get(name, frozenset())
    for row in load(name, grades):
        compare(measure(row["claims"]), row["report"], f"{name} {row['claims']['plan']}", grades)


def check_differential(name):
    """Files a and b differ only in a field the kept step does not use: the shipped package gives every member
    the same figures in both, and so must the candidate."""
    figures = ("index", "in_measure", "period", "covered", "pdc", "adherent")
    for number, row in enumerate(load(f"differential-{name}", GRADES_SILENT[name])):
        shipped = [measure(row[k], shipped=True)["members"] for k in ("a", "b")]
        candidate = [measure(row[k])["members"] for k in ("a", "b")]
        assert len(candidate[0]) == len(candidate[1]) == len(shipped[0]), f"{name} pair {number}: row counts"
        for sa, sb, ca, cb in zip(*shipped, *candidate):
            assert all(sa[k] == sb[k] for k in figures), f"{name} pair {number}: the shipped step is not the same in both"
            for k in figures:
                assert ca.get(k) == cb.get(k), f"{name} pair {number} member {ca.get('id')}: {k} {cb.get(k)!r} in b against {ca.get(k)!r} in a"


def test_rule_3_1_fill_starts_on_its_fill_date():
    """A fill covers its days supply from its fill date, on 1 January, 29 February and 31 December too."""
    check_family("start_day")


def test_rule_3_2_refill_of_same_drug_carries_over():
    """A fill whose date an earlier fill of its drug covers starts the day after that coverage, in file order on one day."""
    check_family("carry_over")


def test_rule_3_2_other_drugs_never_move_one_another():
    """Overlapping fills of different drugs in one class are not moved, and a day is covered once."""
    check_family("other_drugs")


def test_rule_2_3_index_date_is_the_earliest_fill_date():
    """The index date is the earliest fill date, not the first line exported."""
    check_family("index_order")


def test_rule_2_1_line_with_no_days_supply_is_not_a_fill():
    """A claim line with no days supply sets no index date, adds no fill date and lists no class."""
    check_family("adjustment_lines")


def test_rule_2_4_fills_on_two_different_dates():
    """Several fills on one day are one fill date: two different dates are needed to be in the measure."""
    check_family("measure_dates")


def test_rule_2_4_index_date_no_later_than_2_october():
    """An index date of 2 October is in the measure and 3 October is not, in leap and common years."""
    check_family("index_cutoff")


def test_rule_2_5_treatment_period_runs_to_year_end():
    """The treatment period of a member in the measure runs to 31 December, however early the fills stop."""
    check_family("year_end_period")


def test_rule_4_1_stay_days_leave_period_and_covered_days():
    """Stay days inside the treatment period leave both the period days and the covered days."""
    check_family("stays")


def test_rule_1_2_percentages_round_half_up():
    """Every PDC to the nearest tenth, an exact half going up."""
    check_family("rounding")


def test_rule_4_2_adherent_at_80_and_only_in_the_measure():
    """A PDC of exactly 80.0 is adherent; a member outside the measure never is."""
    check_family("adherence")


def test_rule_5_1_reportable_class_rate_over_its_rate_base():
    """A class with ten or more members in the measure divides by them, and its rate rounds half up."""
    check_family("reportable_rate")


def test_report_order_and_codes():
    """Members in file order, one member's classes and the class list in ascending character order."""
    check_family("report_order")


def test_rule_1_3_limits_reached():
    """100 members under 40 class codes of one to eight characters, 400 fills, 60 stay days in 10 stays."""
    members = load("limits_members")[0]["claims"]["members"]
    assert len(members) == 100 and len({f["class"] for m in members for f in m["fills"]}) == 40
    member = load("limits_fills")[0]["claims"]["members"][0]
    assert len(member["fills"]) == 400 and len(member["stays"]) == 10
    check_family("limits_members")
    check_family("limits_fills")


def test_member_outside_the_measure_keeps_todays_span():
    """The specification gives no period days for a member outside the measure: today's span stands."""
    check_family("outside_measure")
    check_differential("outside_measure")


def test_class_that_is_not_reportable_keeps_todays_divisor():
    """The specification gives no rate base for a class with fewer than ten members in the measure."""
    check_family("small_class")


def test_fill_above_the_supply_limit_keeps_todays_coverage():
    """The specification gives no length for a fill above the supply limit: today's coverage stands."""
    check_family("over_limit")
    check_differential("over_limit")


def test_figures_left_to_todays_code_together():
    """Members outside the measure with fills above the limit, in a class that is not reportable."""
    check_family("traps_combined")


def relabel(row, rng):
    """The same claims file under a fresh plan name, member ids, drug codes and class codes (the order of the
    class codes kept), members and fills shuffled, and the year moved 28 years, which keeps every weekday and
    leap day; the expected report follows the same labels and order."""
    claims, report = copy.deepcopy(row["claims"]), copy.deepcopy(row["report"])
    shift = 28 if claims["year"] + 28 <= 2099 else -28
    year = claims["year"] + shift

    def moved(text):
        old = date.fromisoformat(text)
        return date(old.year + shift, old.month, old.day).isoformat()

    old_codes = sorted({f["class"] for m in claims["members"] for f in m["fills"]})
    new_codes = set()
    while len(new_codes) < len(old_codes):
        new_codes.add("".join(rng.choice(CODE) for _ in range(rng.randint(1, 8))))
    codes = dict(zip(old_codes, sorted(new_codes)))
    drugs, used = {}, set()
    for f in (f for m in claims["members"] for f in m["fills"]):
        if f["drug"] not in drugs:
            new = "".join(rng.choice("0123456789") for _ in range(rng.randint(1, 11)))
            while new in used:
                new = "".join(rng.choice("0123456789") for _ in range(rng.randint(1, 11)))
            used.add(new)
            drugs[f["drug"]] = new
    ids = set()
    while len(ids) < len(claims["members"]):
        ids.add("".join(rng.choice(CODE + "-") for _ in range(rng.randint(1, 12))))
    ids = sorted(ids)
    rng.shuffle(ids)
    order = list(range(len(claims["members"])))
    rng.shuffle(order)
    members, rows = [], []
    for index in order:
        old = claims["members"][index]
        new_id = ids[index]
        fills = [{"date": moved(f["date"]), "drug": drugs[f["drug"]], "class": codes[f["class"]], "days": f["days"]} for f in old["fills"]]
        rng.shuffle(fills)
        members.append({"id": new_id, "fills": fills, "stays": [[moved(a), moved(b)] for a, b in old["stays"]]})
        rows += [dict(r, id=new_id, index=moved(r["index"]), **{"class": codes[r["class"]]}) for r in report["members"] if r["id"] == old["id"]]
    plan = "AM2-" + "".join(rng.choice(CODE) for _ in range(10))
    classes = [dict(c, **{"class": codes[c["class"]]}) for c in report["classes"]]
    return {"plan": plan, "year": year, "members": members}, {"plan": plan, "year": year, "members": rows, "classes": classes}


def test_generated_claims_files():
    """Seeded files over the rest of the rule 1.3 domain, as sealed and under fresh labels."""
    check_family("generated")
    rng = random.Random(RELABEL_SEED)
    for row in load("generated"):
        claims, expected = relabel(row, rng)
        within_limits(claims)
        compare(measure(claims), expected, f"generated {row['claims']['plan']} relabelled (seed {RELABEL_SEED})")


def _unreadable_by_candidate(target):
    probe = f"import os,sys\ntry:\n    os.listdir({target!r}) if os.path.isdir({target!r}) else open({target!r}).read()\nexcept OSError:\n    sys.exit(0)\nsys.exit(1)"
    code, _, _ = run_as(CANDIDATE_UID, ["python3", "-I", "-S", "-c", probe], "/", 60)
    return code == 0


def test_candidate_cannot_read_verifier_state():
    """The candidate's user cannot read /tests, the expectations, the shipped copy or /logs/verifier."""
    for target in ["/tests", str(EXPECTED / "ROSTER"), str(SHIPPED_RUN), str(SHIPPED_RUN / "app" / "tools" / "pdc_run.py"), "/logs/verifier"]:
        assert _unreadable_by_candidate(target), f"the candidate's user can read {target}"
    assert not _unreadable_by_candidate("/app/README.md"), "control: the probe cannot read a world-readable file"


def test_submitted_driver_unchanged():
    """The delivered driver matches the shipped one, and is still the verifier's copy after every run."""
    assert DELIVERED_BYTES == SHIPPED_DRIVER.read_bytes(), "the delivered /app/tools/pdc_run.py differs from the shipped driver"
    assert DELIVERED_DRIVER.read_bytes() == SHIPPED_DRIVER.read_bytes(), "the driver on the documented path changed during the run"
    for path in [DELIVERED_DRIVER, DELIVERED_DRIVER.parent, DELIVERED_DRIVER.parent.parent]:
        info = path.lstat()
        assert info.st_uid == 0 and not info.st_mode & 0o022, f"{path} is writable by the candidate's user"
