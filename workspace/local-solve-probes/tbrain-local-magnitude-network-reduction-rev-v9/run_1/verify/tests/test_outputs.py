"""Verifier for the mlnet repair (NPM-4, local magnitude).

The delivered driver's bytes are read before any candidate code runs; the
verifier's own copy (tests/shipped/tools/ml_bulletin.py) is then os.replace-d
onto /app/tools/ml_bulletin.py, and every bulletin is reduced by the documented
command (that driver with the bulletin's path), run as an unprivileged user
with an isolated interpreter, from a fresh directory, on a file with the same
neutral name for every bulletin. Expected reports were written ahead of time by
solution/seal.py from a model of NPM-4 and are read from tests/expected/, whose
SHA-256 sums and row counts are pinned in tests/expected/ROSTER. One test per
NPM-4 rule or case; each compares the complete report of every bulletin in its
file. Every bulletin is checked against section 1 of NPM-4 when it is loaded,
and only three files may carry the inputs their test is about.
"""

import hashlib
import json
import math
import os
import shutil
import signal
import subprocess
import tempfile
import time
from pathlib import Path

TESTS = Path(__file__).resolve().parent
EXPECTED = TESTS / "expected"
SHIPPED_DRIVER = TESTS / "shipped" / "tools" / "ml_bulletin.py"
DELIVERED_DRIVER = Path("/app") / "tools" / SHIPPED_DRIVER.name
ENV = ["/usr/bin/env", "-i", "PATH=/usr/local/bin:/usr/bin:/bin", "HOME=/nonexistent", "LANG=C.UTF-8", "PYTHONDONTWRITEBYTECODE=1"]
DEADLINE = time.monotonic() + 1500
TOL = 1e-6
# expected values are stored to 9 decimals, within 5.1e-10 of the exact figures; this
# allowance keeps an output within TOL of the exact figure from ever being rejected
SLACK = 1e-9
# the only files whose bulletins may carry these inputs
CARRIERS = {"readings.jsonl": {"sub_noise"}, "off_table.jsonl": {"off_table"}, "shared_station.jsonl": {"shared_station"}}


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
    staged = DELIVERED_DRIVER.with_name(".ml_bulletin.verifier")
    shutil.copyfile(SHIPPED_DRIVER, staged)
    os.chmod(staged, 0o644)
    os.replace(staged, DELIVERED_DRIVER)
    return delivered


DELIVERED_BYTES = _install_driver()


def _classes(bulletin):
    """Section 1 of NPM-4, and which of the three special input classes a bulletin carries."""
    codes = {s["code"]: s["correction"] for s in bulletin["stations"]}
    assert 1 <= len(codes) == len(bulletin["stations"]) <= 200
    assert all(-1.0 <= c <= 1.0 for c in codes.values())
    assert 1 <= len(bulletin["events"]) <= 50
    found = set()
    for event in bulletin["events"]:
        assert 0 <= event["depth_km"] <= 60 and 1 <= len(event["recordings"]) <= 40
        seen = {}
        for rec in event["recordings"]:
            assert rec["code"] in codes and 0 <= rec["epi_km"] <= 1000 and 1 <= len(rec["amplitudes"]) <= 2
            seen[rec["code"]] = seen.get(rec["code"], 0) + 1
            distance = math.hypot(rec["epi_km"], event["depth_km"])
            assert distance >= 1.0
            assert abs(distance - 10.0) > 0.001 and abs(distance - 600.0) > 0.001
            if not 10.0 <= distance <= 600.0:
                found.add("off_table")
            for a in rec["amplitudes"]:
                assert 0.1 <= a["amplitude_nm"] <= 1e8 and 0.01 <= a["noise_nm"] <= 1e7
                assert type(a["channel"]) is str and len(a["channel"]) == 3
                assert abs(a["amplitude_nm"] - 3 * a["noise_nm"]) > 0.003 * a["noise_nm"]
                if a["amplitude_nm"] < 3 * a["noise_nm"]:
                    found.add("sub_noise")
            assert any(a["amplitude_nm"] >= 3 * a["noise_nm"] for a in rec["amplitudes"])
        assert max(seen.values()) <= 2
        if max(seen.values()) == 2:
            found.add("shared_station")
    return found


def load(name):
    """Rows of one file; fails when the file, its digest, its count or its inputs differ from the plan."""
    digest, count = ROSTER[name]
    raw = (EXPECTED / name).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == digest, f"{name} does not match the roster"
    rows = [json.loads(line) for line in raw.decode().splitlines() if line]
    assert len(rows) == count, f"{name}: {len(rows)} rows, roster says {count}"
    carried = set()
    for row in rows:
        carried |= _classes(row["bulletin"])
    assert carried == CARRIERS.get(name, set()), f"{name} carries {sorted(carried)}"
    return rows


def run_unprivileged(argv, cwd, timeout):
    """Run candidate-reachable code as nobody, in its own session; kill the whole group afterwards."""
    proc = subprocess.Popen(
        ["setpriv", "--reuid=65534", "--regid=65534", "--clear-groups", "--no-new-privs", "--"] + ENV + argv,
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


def reduce(bulletin):
    """Run the documented command on one bulletin as the unprivileged user; return its parsed stdout."""
    stage, work = tempfile.mkdtemp(), tempfile.mkdtemp()
    os.chmod(stage, 0o755)
    os.chmod(work, 0o777)
    path = os.path.join(stage, "bulletin.json")
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(bulletin, handle)
    os.chmod(path, 0o644)
    remaining = DEADLINE - time.monotonic()
    assert remaining > 0, "verifier time budget exhausted"
    code, out, err = run_unprivileged(["python3", "-I", "-S", str(DELIVERED_DRIVER), path], work, remaining)
    assert code == 0, f"driver exited {code}: {err[-2000:]}"
    return json.loads(out)


def _number(actual, expected, where):
    if expected is None:
        assert actual is None, f"{where}: {actual!r}, expected null"
        return
    assert isinstance(actual, (int, float)) and not isinstance(actual, bool), f"{where}: {actual!r} is not a number"
    assert abs(actual - expected) <= TOL + SLACK, f"{where}: {actual!r}, expected {expected!r}"


def compare(actual, expected, label):
    assert isinstance(actual, dict) and set(actual) == {"events"}, f"{label}: top-level keys"
    got, want = actual["events"], expected["events"]
    assert isinstance(got, list) and len(got) == len(want), f"{label}: {len(want)} events expected"
    for event, ref in zip(got, want):
        where = f"{label} event {ref['id']}"
        assert isinstance(event, dict) and set(event) == {"id", "ml", "stations"}, f"{where}: keys"
        assert type(event["id"]) is str and event["id"] == ref["id"], f"{where}: id {event['id']!r}"
        _number(event["ml"], ref["ml"], f"{where} ml")
        rows = event["stations"]
        assert isinstance(rows, list) and len(rows) == len(ref["stations"]), f"{where}: station rows"
        for index, (row, exp) in enumerate(zip(rows, ref["stations"])):
            at = f"{where} station {index} ({exp['code']})"
            assert isinstance(row, dict) and set(row) == {"code", "distance_km", "ml", "contributes"}, f"{at}: keys"
            assert type(row["code"]) is str and row["code"] == exp["code"], f"{at}: code {row['code']!r}"
            _number(row["distance_km"], exp["distance_km"], f"{at} distance_km")
            _number(row["ml"], exp["ml"], f"{at} ml")
            assert type(row["contributes"]) is bool and row["contributes"] is exp["contributes"], f"{at}: contributes"


def check_file(name):
    for number, row in enumerate(load(name)):
        compare(reduce(row["bulletin"]), row["report"], f"{name} bulletin {number}")


def test_rule_2_2_record_amplitude_uses_magnification_2080():
    """Station magnitudes at listed distances, depth 0: the record amplitude uses magnification 2080."""
    check_file("gain.jsonl")


def test_rule_2_2_record_amplitude_is_half_peak_to_peak():
    """Single readings at listed distances with no correction: the record amplitude is half the peak-to-peak value."""
    check_file("half.jsonl")


def test_rule_2_3_station_mean_leaves_out_amplitudes_under_three_times_noise():
    """Only amplitudes at least three times their channel's noise enter a station's mean, on either side close to the line."""
    check_file("readings.jsonl")


def test_rule_3_1_distance_is_hypocentral():
    """The distance reported, corrected for and tested against the table is the hypocentral distance."""
    check_file("hypocentral.jsonl")


def test_rule_3_3_correction_linear_between_listed_distances():
    """Between two listed distances the correction is interpolated linearly in distance."""
    check_file("interpolation.jsonl")


def test_rule_3_3_listed_distances_and_table_ends():
    """At listed distances the correction is the listed value; stations just inside either end of the table contribute."""
    check_file("table_ends.jsonl")


def test_station_beyond_the_table_keeps_the_shipped_correction():
    """A station nearer than 10 km or beyond 600 km keeps today's correction calculation and does not contribute."""
    check_file("off_table.jsonl")


def test_rule_4_2_station_correction_is_added():
    """Station corrections from -1.0 to +1.0 are added to each channel magnitude."""
    check_file("correction.jsonl")


def test_rule_4_3_station_magnitude_is_mean_of_channel_magnitudes():
    """A station's magnitude is the mean of its readings' channel magnitudes, whatever their channel codes, not its largest channel."""
    check_file("station_mean.jsonl")


def test_two_sensors_of_one_site_are_one_station():
    """A station with two recordings pools their readings and counts once in the median and the three-station minimum."""
    check_file("shared_station.jsonl")


def test_rule_5_2_network_magnitude_is_median_of_contributors():
    """With an odd number of contributing stations the network magnitude is the middle one."""
    check_file("median.jsonl")


def test_rule_5_2_even_number_takes_mean_of_middle_two():
    """With an even number of contributing stations the network magnitude is the mean of the two middle ones."""
    check_file("median_even.jsonl")


def test_rule_5_3_fewer_than_three_contributors_has_no_network_magnitude():
    """Events with one or two contributing stations report a null network magnitude."""
    check_file("fewer_than_three.jsonl")


def test_rule_5_3_three_contributors_give_a_network_magnitude():
    """Events with exactly three contributing stations get a network magnitude."""
    check_file("three.jsonl")


def test_section_one_limits_reached():
    """Fifty events, two hundred stations, forty recordings, and every amplitude, noise, depth and correction limit."""
    rows = load("limits.jsonl")
    bulletin = rows[0]["bulletin"]
    assert len(bulletin["events"]) == 50 and len(bulletin["stations"]) == 200
    assert max(len(e["recordings"]) for e in bulletin["events"]) == 40
    check_file("limits.jsonl")


def test_report_keeps_file_and_recording_order():
    """Events keep file order and station rows keep recording order, whatever the ids and codes, at any length they may have."""
    check_file("order.jsonl")


def test_generated_bulletins():
    """Generated bulletins across the envelope: depths, distances, one or two channels, corrections, event sizes."""
    check_file("generated.jsonl")


def _unreadable_by_candidate(target):
    probe = f"import os,sys\ntry:\n    os.listdir({target!r}) if os.path.isdir({target!r}) else open({target!r}).read()\nexcept OSError:\n    sys.exit(0)\nsys.exit(1)"
    code, _, _ = run_unprivileged(["python3", "-I", "-S", "-c", probe], "/", 60)
    assert code == 0, f"the unprivileged user can read {target}"


def test_sandbox_cannot_read_ground_truth():
    """The unprivileged bulletin user can read neither the expectations, the verifier's files nor its logs."""
    for target in ("/tests", "/tests/expected/ROSTER", "/tests/test_outputs.py", "/logs/verifier"):
        _unreadable_by_candidate(target)


def test_submitted_driver_matches_ours():
    """The driver left in /app/tools is byte-identical to ours, before and after the bulletins were reduced."""
    assert DELIVERED_BYTES == SHIPPED_DRIVER.read_bytes()
    assert DELIVERED_DRIVER.read_bytes() == SHIPPED_DRIVER.read_bytes()
