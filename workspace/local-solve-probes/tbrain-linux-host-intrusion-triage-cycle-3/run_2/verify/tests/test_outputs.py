"""Verifier for the SSH intrusion triage analyzer (/app/triage.py).

Evidence sets were generated at authoring time by solution/seal.py from solution/model.py and
sealed into tests/evidence/<family>.tar.gz; the reports expected for them were derived from each
generated scenario (never by parsing the evidence) and sealed as plain JSON, one case per line,
into tests/expected/<family>.jsonl. tests/expected/ROSTER pins every file's SHA-256 and case count.
This verifier holds no model and no generator: it only loads those files.

Every case is staged in a fresh prefix-less temporary directory under the neutral name `evidence`,
owned by root and read-only, and the documented command
    python3 /app/triage.py <evidence_dir> <out.json>
is run as an unprivileged user (setpriv --no-new-privs, uid 65534, isolated interpreter
`python3 -I -S`, empty environment, own session) writing into its own scratch directory. /app holds
only the delivered triage.py and the task's docs, root-owned and unwritable. Each report is
compared with the expected one: exactly the seven keys, the three list fields as sets of strings
without duplicates, every other value type-strictly and exactly. One test per rule or family.
"""

import hashlib
import json
import os
import shutil
import subprocess
import tarfile
import tempfile
import time
from pathlib import Path

TESTS = Path(__file__).resolve().parent
EXPECTED = TESTS / "expected"
EVIDENCE = TESTS / "evidence"
APP = Path("/app")
CANDIDATE_UID = 65534
ENV = ["/usr/bin/env", "-i", "PATH=/usr/local/bin:/usr/bin:/bin", "HOME=/nonexistent", "LANG=C.UTF-8",
       "PYTHONDONTWRITEBYTECODE=1"]
DEMOTE = ["setpriv", f"--reuid={CANDIDATE_UID}", f"--regid={CANDIDATE_UID}", "--clear-groups", "--no-new-privs"]
KEYS = {"initial_access", "sources", "accounts", "privilege_escalation", "persistence", "first_activity", "last_activity"}
SETS = ("sources", "accounts", "persistence")
DEADLINE = time.monotonic() + 1650


def _roster():
    rows = {}
    for line in (EXPECTED / "ROSTER").read_text().splitlines():
        digest, name, count = line.split()
        rows[name] = (digest, int(count))
    return rows


ROSTER = _roster()


def _seal_app():
    """/app keeps only the delivered analyzer and the task docs, root-owned and read-only."""
    delivered = (APP / "triage.py").read_bytes() if (APP / "triage.py").is_file() else b""
    for entry in list(APP.iterdir()) if APP.is_dir() else []:
        if entry.is_dir() and not entry.is_symlink():
            shutil.rmtree(entry)
        else:
            entry.unlink()
    APP.mkdir(exist_ok=True)
    (APP / "triage.py").write_bytes(delivered)
    shutil.copytree(TESTS / "shipped" / "docs", APP / "docs")
    for p in [APP] + list(APP.rglob("*")):
        os.lchown(p, 0, 0)
        os.chmod(p, 0o755 if p.is_dir() else 0o644)


_seal_app()


def _load(family):
    """Check both sealed files against the roster, then return (tar path, expected rows)."""
    ev, exp = EVIDENCE / f"{family}.tar.gz", EXPECTED / f"{family}.jsonl"
    for path, key in ((ev, f"evidence/{family}.tar.gz"), (exp, f"expected/{family}.jsonl")):
        digest, _ = ROSTER[key]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == digest, f"{key} does not match the roster"
    rows = [json.loads(line) for line in exp.read_text().splitlines() if line.strip()]
    assert len(rows) == ROSTER[f"expected/{family}.jsonl"][1]
    return ev, rows


def _unprivileged(cmd, cwd, timeout):
    return subprocess.run(DEMOTE + ENV + cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout,
                          start_new_session=True, check=False)


def _run_case(tar_path, case_id):
    stage = Path(tempfile.mkdtemp())
    out = Path(tempfile.mkdtemp())
    try:
        with tarfile.open(tar_path) as tar:
            members = [m for m in tar.getmembers() if m.name == case_id or m.name.startswith(case_id + "/")]
            tar.extractall(stage, members=members, filter="data")
        evidence = stage / "evidence"
        (stage / case_id).rename(evidence)
        for p in [stage] + list(stage.rglob("*")):
            os.lchown(p, 0, 0)
            os.chmod(p, 0o555 if p.is_dir() else 0o444)
        os.chown(out, CANDIDATE_UID, CANDIDATE_UID)
        os.chmod(out, 0o700)
        remaining = max(30.0, DEADLINE - time.monotonic())
        proc = _unprivileged(["python3", "-I", "-S", "/app/triage.py", str(evidence), str(out / "report.json")],
                             out, min(300.0, remaining))
        try:
            return json.loads((out / "report.json").read_text()), proc
        except (OSError, ValueError) as exc:
            return {"_unreadable": repr(exc)}, proc
    finally:
        shutil.rmtree(stage, ignore_errors=True)
        shutil.rmtree(out, ignore_errors=True)


def _differences(got, want):
    if not isinstance(got, dict) or set(got) != KEYS:
        return ["<report keys>"]
    bad = []
    for key in sorted(KEYS):
        g, w = got[key], want[key]
        if key in SETS:
            ok = isinstance(g, list) and all(type(x) is str for x in g) and len(g) == len(set(g)) and sorted(g) == sorted(w)
        elif key == "initial_access":
            ok = isinstance(g, dict) and set(g) == set(w) and all(type(g[k]) is str and g[k] == w[k] for k in w)
        else:
            ok = type(g) is type(w) and g == w
        if not ok:
            bad.append(key)
    return bad


def _check_family(family):
    tar_path, rows = _load(family)
    failures = []
    for row in rows:
        got, proc = _run_case(tar_path, row["case"])
        bad = _differences(got, row["report"])
        if bad:
            failures.append(f"{row['case']}: {', '.join(bad)} (exit {proc.returncode}; stderr {proc.stderr[-300:]!r})")
    assert not failures, f"{len(failures)} of {len(rows)} {family} cases wrong: " + "; ".join(failures)


def test_case_1_visible_collection():
    _check_family("case1")


def test_rule_1_host_clock_error_is_corrected_in_every_source():
    _check_family("clock")


def test_rule_1_year_is_placed_across_new_year():
    _check_family("year")


def test_rule_1_local_offsets_convert_to_utc():
    _check_family("tz")


def test_rule_2_hostile_address_five_failures_within_600_seconds():
    _check_family("brute")


def test_rule_2_btmp_keeps_failures_rotated_out_of_auth_log():
    _check_family("rotation")


def test_rule_4_planted_key_ties_a_second_address():
    _check_family("key")


def test_rule_5_escalation_is_on_the_intruder_terminal():
    _check_family("sudo")


def test_rule_5_escalation_by_a_root_login_without_sudo():
    _check_family("rootlogin")


def test_rule_6_persistence_by_ctime_and_not_package_writes():
    _check_family("ctime")


def test_rule_7_activity_with_a_session_still_open():
    _check_family("open")


def test_range_ends_low():
    _check_family("edge_lo")


def test_range_ends_high():
    _check_family("edge_hi")


def test_range_ends_late_year():
    _check_family("edge_late")


def test_broad_hosts():
    _check_family("broad")


def test_candidate_cannot_read_verifier_files():
    probe = ("import os,sys\n"
             "for p in sys.argv[1:]:\n"
             "    try:\n"
             "        os.listdir(p) if os.path.isdir(p) else open(p,'rb').read(1)\n"
             "        print('READ', p)\n"
             "    except OSError:\n"
             "        pass\n")
    targets = ["/tests", "/tests/expected/ROSTER", "/tests/expected/case1.jsonl", "/tests/evidence", "/logs/verifier"]
    proc = _unprivileged(["python3", "-I", "-S", "-c", probe] + targets, "/", 60)
    assert proc.returncode == 0, proc.stderr
    assert "READ" not in proc.stdout, proc.stdout
    control = _unprivileged(["python3", "-I", "-S", "-c", "import os; print(sorted(os.listdir('/app')))"], "/", 60)
    assert control.returncode == 0 and "triage.py" in control.stdout
