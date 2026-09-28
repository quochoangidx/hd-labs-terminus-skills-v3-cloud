"""Verifier for the metalquant repair (SOP TM-07).

The delivered driver's bytes are read before any candidate code runs; the
verifier's own copy of the driver (tests/shipped/tools/metalquant_run.py) is then
os.replace-d onto /app/tools/metalquant_run.py, and every batch is reduced by
exactly the documented command, python3 /app/tools/metalquant_run.py BATCH, run as
an unprivileged user with an isolated interpreter, from a fresh directory, on a
file with the same neutral name for every batch. The expected
reports were written ahead of time by solution/seal.py from an independent model
of the SOP and are read from tests/expected/, whose SHA-256 sums are pinned in
tests/expected/ROSTER. One test per SOP rule; each compares the complete report
of every batch in its family.
"""

import hashlib
import json
import os
import shutil
import signal
import subprocess
import tempfile
import time
from pathlib import Path

TESTS = Path(__file__).resolve().parent
EXPECTED = TESTS / "expected"
SHIPPED_DRIVER = TESTS / "shipped" / "tools" / "metalquant_run.py"
DELIVERED_DRIVER = Path("/app") / "tools" / SHIPPED_DRIVER.name
DRIVER = str(DELIVERED_DRIVER)
ENV = ["/usr/bin/env", "-i", "PATH=/usr/local/bin:/usr/bin:/bin", "HOME=/nonexistent", "LANG=C.UTF-8", "PYTHONDONTWRITEBYTECODE=1"]
DEADLINE = time.monotonic() + 1500
REL, ABS = 1e-6, 1e-6
TOP_KEYS = {"blank_levels", "samples", "ccvs", "spikes"}
ENTRY_KEYS = {
    "samples": ("id", "analyte", "value", "flag", "ccv_ok"),
    "ccvs": ("id", "analyte", "recovery", "pass"),
    "spikes": ("id", "analyte", "recovery"),
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
    staged = DELIVERED_DRIVER.with_name(".metalquant_run.verifier")
    shutil.copyfile(SHIPPED_DRIVER, staged)
    os.chmod(staged, 0o644)
    os.replace(staged, DELIVERED_DRIVER)
    return delivered


DELIVERED_BYTES = _install_driver()


def load(name):
    """Rows of one family; fails when the file, its digest or its count differ from the roster."""
    path = EXPECTED / name
    digest, count = ROSTER[name]
    raw = path.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == digest, f"{name} does not match the roster"
    text = raw.decode()
    rows = [json.loads(line) for line in text.splitlines() if line]
    assert len(rows) == count, f"{name}: {len(rows)} rows, roster says {count}"
    return rows


def run_unprivileged(argv, cwd, timeout):
    """Run candidate-reachable code as nobody, in its own session; kill the whole group afterwards."""
    proc = subprocess.Popen(
        ["setpriv", "--reuid=65534", "--regid=65534", "--clear-groups", "--no-new-privs", "--"] + ENV + argv,
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


def reduce(batch):
    """Run the verifier-owned driver on one batch as the unprivileged user; return its parsed stdout."""
    stage = tempfile.mkdtemp()
    work = tempfile.mkdtemp()
    os.chmod(stage, 0o755)
    os.chmod(work, 0o777)
    path = os.path.join(stage, "batch.json")
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(batch, handle)
    os.chmod(path, 0o644)
    remaining = DEADLINE - time.monotonic()
    assert remaining > 0, "verifier time budget exhausted"
    code, out, err = run_unprivileged(["python3", "-I", "-S", DRIVER, path], work, remaining)
    assert code == 0, f"driver exited {code}: {err[-2000:]}"
    return json.loads(out)


def _number(actual, expected, where):
    assert isinstance(actual, (int, float)) and not isinstance(actual, bool), f"{where}: {actual!r} is not a number"
    bound = REL * abs(expected) if abs(expected) >= 1 else ABS
    assert abs(actual - expected) <= bound, f"{where}: {actual!r}, expected {expected!r}"


def compare(actual, expected, label):
    assert isinstance(actual, dict) and set(actual) == TOP_KEYS, f"{label}: top-level keys {sorted(actual) if isinstance(actual, dict) else actual!r}"
    levels = actual["blank_levels"]
    assert isinstance(levels, dict) and set(levels) == set(expected["blank_levels"]), f"{label}: blank_levels keys"
    for name, value in expected["blank_levels"].items():
        _number(levels[name], value, f"{label} blank_levels[{name}]")
    for section, keys in ENTRY_KEYS.items():
        got, want = actual[section], expected[section]
        assert isinstance(got, list) and len(got) == len(want), f"{label}: {section} has {len(got) if isinstance(got, list) else got!r} entries, expected {len(want)}"
        for index, (entry, ref) in enumerate(zip(got, want)):
            where = f"{label} {section}[{index}] ({ref['id']}, {ref['analyte']})"
            assert isinstance(entry, dict) and set(entry) == set(keys), f"{where}: keys {entry!r}"
            for key in keys:
                a, e = entry[key], ref[key]
                if key in ("recovery",) or (key == "value" and e is not None):
                    _number(a, e, f"{where} {key}")
                else:
                    assert type(a) is type(e) and a == e, f"{where} {key}: {a!r}, expected {e!r}"


def check_family(name):
    for number, row in enumerate(load(name)):
        compare(reduce(row["batch"]), row["report"], f"{name} batch {number}")


def test_calibration_line_has_fitted_intercept():
    check_family("calibration.jsonl")


def test_blank_level_is_mean_of_results_anywhere():
    check_family("blank_mean.jsonl")


def test_nondetect_blanks_stay_out_of_the_mean():
    check_family("blank_nondetects.jsonl")


def test_single_blank_result_is_the_level():
    check_family("blank_single_result.jsonl")


def test_batch_without_blank_results_keeps_shipped_level():
    check_family("blank_no_results.jsonl")


def test_blank_comes_off_before_dilution():
    check_family("dilution.jsonl")


def test_flags_judged_on_corrected_reading():
    check_family("flag_basis.jsonl")


def test_flags_at_exact_mdl_and_loq():
    check_family("flag_limits.jsonl")


def test_readings_below_nought_are_not_clamped():
    check_family("negative_readings.jsonl")


def test_ccv_pass_on_rounded_recovery_inclusive():
    check_family("ccv_limits.jsonl")


def test_bracketed_runs_need_both_ccvs():
    check_family("ccv_bracketing.jsonl")


def test_unbracketed_runs_keep_shipped_check():
    check_family("ccv_unbracketed.jsonl")


def test_spike_recovery_of_results():
    check_family("spike_recovery.jsonl")


def test_nondetect_spikes_keep_shipped_recovery():
    check_family("spike_nondetects.jsonl")


def test_section_one_limits_reached():
    check_family("section_one_limits.jsonl")


def test_report_order_and_types():
    check_family("report_order.jsonl")


def test_generated_batches():
    check_family("generated-1.jsonl")
    check_family("generated-2.jsonl")


def test_capacity_batch():
    rows = load("capacity.jsonl")
    batch = rows[0]["batch"]
    assert len(batch["runs"]) == 80 and len(batch["analytes"]) == 4 and len(batch["standards"]) == 8
    check_family("capacity.jsonl")


def test_driver_is_unchanged():
    assert DELIVERED_BYTES == SHIPPED_DRIVER.read_bytes()


def _unreadable_by_candidate(target):
    probe = f"import os,sys\ntry:\n    os.listdir({target!r}) if os.path.isdir({target!r}) else open({target!r}).read()\nexcept OSError:\n    sys.exit(0)\nsys.exit(1)"
    code, _, _ = run_unprivileged(["python3", "-I", "-S", "-c", probe], "/", 60)
    assert code == 0, f"the unprivileged user can read {target}"


def test_candidate_cannot_read_expected_reports():
    _unreadable_by_candidate("/tests/expected/ROSTER")


def test_candidate_cannot_read_verifier_logs():
    _unreadable_by_candidate("/logs/verifier")
