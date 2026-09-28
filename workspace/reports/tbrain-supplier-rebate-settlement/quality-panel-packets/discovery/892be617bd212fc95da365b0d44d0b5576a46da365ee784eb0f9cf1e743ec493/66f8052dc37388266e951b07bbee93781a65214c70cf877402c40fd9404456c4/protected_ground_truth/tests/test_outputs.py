"""Verifier for the rebate repair (Schedule R, edition R-4).

Before any candidate code runs, the delivered driver's bytes are recorded, the verifier's own copy
(tests/shipped/app/tools/rebate_run.py) is os.replace-d onto /app/tools/rebate_run.py, and all of /app is
made root-owned and unwritable by others. Every job is run through the documented command,
python3 /app/tools/rebate_run.py JOB.json, as an unprivileged user in its own session with an isolated
interpreter, from a fresh directory, on a file with the same neutral name for every job. Expected
settlements were written ahead of time by solution/seal.py from an independent model of the schedule and
are read from tests/expected/, pinned by SHA-256 and row count in tests/expected/ROSTER. For the three cases
the schedule leaves to today's code, a copy of the shipped package, owned by its own user and closed to
everyone else, is also run as a differential. One test per rule; each compares the complete settlements of
every job in its family, type-strictly.
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
SHIPPED_DRIVER = SHIPPED_APP / "tools" / "rebate_run.py"
DELIVERED_DRIVER = Path("/app/tools/rebate_run.py")
CANDIDATE_UID = 65534
SHIPPED_UID = 65533
ENV = ["/usr/bin/env", "-i", "PATH=/usr/local/bin:/usr/bin:/bin", "HOME=/nonexistent", "LANG=C.UTF-8", "PYTHONDONTWRITEBYTECODE=1"]
DEADLINE = time.monotonic() + 1500
FIELDS = ["account", "purchases", "returns", "net", "tier_bp", "rebate", "growth", "protection", "chargebacks", "total", "paid", "carried"]
# Fresh labels for relabelled jobs; printed in every failure message that uses them.
RELABEL_SEED = int.from_bytes(os.urandom(8), "big")
CARTON = 12
PRICE_DROP = 250
CONTRACT_GAP = 100
# Families allowed (and required) to carry an input the schedule leaves to today's code; every other family carries none.
TRAP_INPUTS = {"loose_units": {"loose_edge"}, "tidy_ups": {"tidy_up"}, "price_match": {"price_match"}}


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
    staged = DELIVERED_DRIVER.with_name(".rebate_run.verifier")
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
    uid, driver = (SHIPPED_UID, str(SHIPPED_RUN / "app" / "tools" / "rebate_run.py")) if shipped else (CANDIDATE_UID, str(DELIVERED_DRIVER))
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
    """Schedule section 1, every limit including its ends: each graded job must keep to it."""
    tiers, accounts = job["tiers"], job["accounts"]
    assert 1 <= len(tiers) <= 12 and tiers[0]["from"] == 0 and 1 <= len(accounts) <= 100
    for k, row in enumerate(tiers):
        assert type(row["from"]) is int and type(row["bp"]) is int and 0 <= row["from"] <= 10**11 and 0 <= row["bp"] <= 1500
        assert k == 0 or row["from"] > tiers[k - 1]["from"]
    assert len({a["account"] for a in accounts}) == len(accounts)
    for a in accounts:
        assert isinstance(a["account"], str) and 1 <= len(a["account"]) <= 16
        assert 2020 <= int(a["quarter"][:4]) <= 2039 and a["quarter"][4:6] == "-Q" and a["quarter"][6:] in "1234"
        assert type(a["prior"]) is int and 0 <= a["prior"] <= 10**11
        first, last = quarter_span(a["quarter"])
        lo, hi = first - timedelta(days=45), last + timedelta(days=45)
        assert len(a["purchases"]) <= 400 and len(a["returns"]) <= 100 and len(a["notices"]) <= 50 and len(a["sales"]) <= 200
        for d, u, c in a["purchases"] + a["returns"]:
            assert lo <= day(d) <= hi and 1 <= u <= 5000 and 100 <= c <= 10**6
        for d, o, n, h in a["notices"]:
            assert lo <= day(d) <= hi and 1 <= n < o <= 10**6 and 100 <= h <= 50000
        for d, u, c, p in a["sales"]:
            assert lo <= day(d) <= hi and 1 <= u <= 5000 and 100 <= c <= 10**6 and 1 <= p < c


def trap_inputs(job):
    """loose_edge: a line below a carton whose invoice day and fourth day after sit on different sides of a
    quarter edge; tidy_up: a notice in the quarter that is not a price drop; price_match: a sale in the quarter
    that is not a contract sale."""
    found = set()
    for a in job["accounts"]:
        first, last = quarter_span(a["quarter"])
        inq = lambda d: first <= d <= last  # noqa: E731
        for inv, u, _c in a["purchases"]:
            if u < CARTON and inq(day(inv)) != inq(day(inv) + timedelta(days=4)):
                found.add("loose_edge")
        for e, o, n, _h in a["notices"]:
            if inq(day(e)) and o - n < PRICE_DROP:
                found.add("tidy_up")
        for s, _u, c, p in a["sales"]:
            if inq(day(s)) and c - p < CONTRACT_GAP:
                found.add("price_match")
    return found


def load(name):
    """Rows of one family; fails when the file, its digest or its count differ from the roster, or a job
    breaks the section 1 limits or carries other inputs than its family declares."""
    digest, count = ROSTER[f"{name}.jsonl"]
    raw = (EXPECTED / f"{name}.jsonl").read_bytes()
    assert hashlib.sha256(raw).hexdigest() == digest, f"{name} does not match the roster"
    rows = [json.loads(line) for line in raw.decode().splitlines() if line]
    assert len(rows) == count, f"{name}: {len(rows)} rows, roster says {count}"
    for row in rows:
        within_limits(row["job"])
        assert trap_inputs(row["job"]) == TRAP_INPUTS.get(name, set()), f"{name}: a job carries {trap_inputs(row['job'])}"
    return rows


def compare(actual, expected, label):
    """The whole output: one key, settlements in job order, each with exactly the README's keys, every value
    but the account code an integer (a float or a boolean is not), all equal to the expected ones."""
    assert isinstance(actual, dict) and list(actual) == ["settlements"], f"{label}: top-level {actual!r:.200}"
    got = actual["settlements"]
    assert isinstance(got, list) and len(got) == len(expected), f"{label}: {len(got) if isinstance(got, list) else got!r} settlements, expected {len(expected)}"
    for index, (row, ref) in enumerate(zip(got, expected)):
        where = f"{label} settlement {index} ({ref['account']!r})"
        assert isinstance(row, dict) and set(row) == set(FIELDS) and len(row) == len(FIELDS), f"{where}: keys {sorted(row) if isinstance(row, dict) else row!r}"
        for key in FIELDS:
            assert type(row[key]) is type(ref[key]) and row[key] == ref[key], f"{where} {key}: {row[key]!r}, expected {ref[key]!r}"


def check_family(name):
    rows = load(name)
    for number, row in enumerate(rows):
        compare(run(row["job"]), row["settlements"], f"{name} job {number}")
    return rows


def test_rule_3_1_carton_shipment_counts_by_receipt():
    """A carton shipment counts toward the quarter it is received in, the fourth day after its invoice."""
    check_family("carton_receipt")


def test_rule_2_2_line_of_exactly_12_units_is_a_carton():
    """Lines of exactly 12 units invoiced in the four days before either quarter edge move with their receipt."""
    check_family("carton_threshold")


def test_rule_3_3_returns_less_40_cents_a_unit():
    """Returns taken back in the quarter are credited at their value less 40 cents a unit."""
    check_family("returns_charge")


def test_rule_3_3_returns_on_the_quarter_edges():
    """Returns on the first and last day count; the day before and the day after do not."""
    check_family("returns_edges")


def test_rule_3_5_tier_is_picked_on_net_purchases():
    """Returns that take net purchases below a threshold that gross purchases pass drop the tier."""
    check_family("tier_net")


def test_rule_2_6_net_exactly_on_a_threshold():
    """Net purchases exactly on a threshold reach that tier, directly and after returns; a cent short does not."""
    check_family("tier_threshold")


def test_rule_2_6_net_below_nought_reaches_no_tier():
    """Returns heavier than purchases: net below nought, rate and rebate nought."""
    check_family("net_below_nought")


def test_rule_3_6_volume_rebate_rounded_half_up():
    """The volume rebate is rounded to the nearest cent, an exact half going up."""
    check_family("rebate_rounding")


def test_rule_4_1_growth_bonus_on_the_increase():
    """The growth bonus is 200 basis points of the increase over last year's net purchases."""
    check_family("growth_increase")


def test_rule_4_1_growth_exactly_110_per_cent():
    """Net purchases of exactly 110 per cent of last year's earn the bonus; a cent short does not."""
    check_family("growth_110")


def test_rule_4_1_no_prior_purchases_no_bonus():
    """Last year's net purchases of nought earn no bonus; one cent does."""
    check_family("growth_no_prior")


def test_rule_5_1_price_drop_earns_cut_times_on_hand():
    """A price drop in the quarter earns the cut times the units on hand; one outside the quarter earns nothing."""
    check_family("price_drop")


def test_rule_2_4_cut_of_exactly_250_cents_is_a_price_drop():
    """A cut of exactly 250 cents on 100 units is a price drop earning 25,000 cents."""
    check_family("price_drop_threshold")


def test_rule_5_2_contract_sale_chargeback():
    """A contract sale in the quarter earns the amount below cost times the units."""
    check_family("contract_sale")


def test_rule_2_5_sale_exactly_100_cents_under_cost_is_a_contract_sale():
    """A sale exactly 100 cents under cost is a contract sale."""
    check_family("contract_threshold")


def test_rule_6_2_minimum_settlement():
    """Settlements below 25,000 cents are carried whole, not paid."""
    check_family("minimum_settlement")


def test_rule_6_2_settlement_of_exactly_25000_cents():
    """A settlement of exactly 25,000 cents is paid; 24,999 is carried; an empty account settles nought."""
    check_family("settlement_edge")


def test_loose_units_keep_their_invoice_quarter():
    """A line below a carton keeps counting toward the quarter of its invoice date, as the shipped package counts it."""
    rows = check_family("loose_units")
    for number, row in enumerate(rows):
        job = copy.deepcopy(row["job"])
        for a in job["accounts"]:
            a["purchases"] = [line for line in a["purchases"] if line[1] < CARTON]
        shipped = [s["purchases"] for s in run(job, shipped=True)["settlements"]]
        candidate = [s["purchases"] for s in run(job)["settlements"]]
        assert candidate == shipped, f"job {number}: loose-unit purchases {candidate}, the shipped package counts {shipped}"


def test_tidy_up_notices_keep_todays_credit():
    """A price notice that is not a price drop keeps the credit the shipped package gives it."""
    for number, row in enumerate(check_family("tidy_ups")):
        shipped = [s["protection"] for s in run(row["job"], shipped=True)["settlements"]]
        candidate = [s["protection"] for s in run(row["job"])["settlements"]]
        assert candidate == shipped, f"job {number}: price protection {candidate}, the shipped package gives {shipped}"


def test_price_match_sales_keep_todays_chargeback():
    """A sale below cost that is not a contract sale keeps the chargeback the shipped package gives it."""
    for number, row in enumerate(check_family("price_match")):
        shipped = [s["chargebacks"] for s in run(row["job"], shipped=True)["settlements"]]
        candidate = [s["chargebacks"] for s in run(row["job"])["settlements"]]
        assert candidate == shipped, f"job {number}: chargebacks {candidate}, the shipped package gives {shipped}"


# Account codes are any string of 1 to 16 characters (schedule 1.3).
NAME_FORMS = [
    lambda tail: tail[:1],
    lambda tail: ("K" * 16 + tail)[-16:],
    lambda tail: " " + tail[:5] + " ",
    lambda tail: 'S"\\/' + tail[:6],
    lambda tail: "é仕入-" + tail[:8],
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


def relabel(job, settlements, rng):
    """The same job under fresh codes, accounts shuffled and every list of an account shuffled (the README puts
    them in no particular order); the expected settlements follow with the same labels and order."""
    order = list(range(len(job["accounts"])))
    rng.shuffle(order)
    names = fresh_names(rng, len(order))
    accounts, rows = [], []
    for name, index in zip(names, order):
        a = copy.deepcopy(job["accounts"][index])
        a["account"] = name
        for key in ("purchases", "returns", "notices", "sales"):
            rng.shuffle(a[key])
        accounts.append(a)
        rows.append(dict(settlements[index], account=name))
    return dict(job, accounts=accounts), rows


def test_statement_order_and_keys():
    """Settlements come in job order with codes as given (1 and 16 characters, spaces, quotes, non-ASCII)."""
    check_family("statement_order")


def test_section_one_limits_reached():
    """12 tier rows, thresholds of 10^11, 100 accounts, 400 lines, 100 returns, 50 notices, 200 sales, every field end."""
    check_family("limits_accounts")
    row = load("limits_job")[0]
    rng = random.Random(RELABEL_SEED)
    names = fresh_names(rng, 100)
    base = dict(row["job"]["accounts"][0])
    for key, n in row["repeat"].items():  # each entry repeated to the list's longest
        base[key] = base[key] * n
    big = dict(row["job"], accounts=[dict(base, account=n) for n in names])
    within_limits(big)
    assert len(big["tiers"]) == 12 and len(big["accounts"]) == 100 and len(base["purchases"]) == 400
    compare(run(big), [dict(row["settlements"][0], account=n) for n in names], f"limits job of 100 accounts (seed {RELABEL_SEED})")


def test_generated_jobs():
    """Seeded jobs over the governed domain, as sealed and under fresh codes and orders."""
    rows = check_family("generated")
    rng = random.Random(RELABEL_SEED)
    for number, row in enumerate(rows):
        job, expected = relabel(row["job"], row["settlements"], rng)
        within_limits(job)
        compare(run(job), expected, f"generated job {number} relabelled (seed {RELABEL_SEED})")


def _unreadable_by_candidate(target):
    probe = f"import os,sys\ntry:\n    os.listdir({target!r}) if os.path.isdir({target!r}) else open({target!r}).read()\nexcept OSError:\n    sys.exit(0)\nsys.exit(1)"
    code, _, _ = run_as(CANDIDATE_UID, ["python3", "-I", "-S", "-c", probe], "/", 60)
    return code == 0


def test_candidate_cannot_read_verifier_state():
    """The candidate's user cannot read /tests, the expectations, the shipped copy or /logs/verifier."""
    for target in ["/tests", str(EXPECTED / "ROSTER"), str(SHIPPED_RUN), str(SHIPPED_RUN / "app" / "tools" / "rebate_run.py"), "/logs/verifier"]:
        assert _unreadable_by_candidate(target), f"the candidate's user can read {target}"
    control = Path(tempfile.mkdtemp())
    os.chmod(control, 0o755)
    (control / "control.txt").write_text("readable\n")
    os.chmod(control / "control.txt", 0o644)
    assert not _unreadable_by_candidate(str(control / "control.txt")), "control: the probe cannot read a world-readable file"
    shutil.rmtree(control, ignore_errors=True)


def test_submitted_driver_unchanged():
    """The delivered driver matches the shipped one, and is still the verifier's copy after every run."""
    assert DELIVERED_BYTES == SHIPPED_DRIVER.read_bytes(), "the delivered /app/tools/rebate_run.py differs from the shipped driver"
    assert DELIVERED_DRIVER.read_bytes() == SHIPPED_DRIVER.read_bytes(), "the driver on the documented path changed during the run"
    for path in [DELIVERED_DRIVER, DELIVERED_DRIVER.parent, DELIVERED_DRIVER.parent.parent]:
        info = path.lstat()
        assert info.st_uid == 0 and not info.st_mode & 0o022, f"{path} is writable by the candidate's user"
