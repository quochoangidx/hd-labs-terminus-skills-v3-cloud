"""Verifier for the Python port of the WBILL job step.

The expected statement files are the job step's own output: the verifier image
builds /tests/legacy/WBILL.cbl (the verifier's copy of the program) with
GnuCOBOL 3.1.2 and runs it on every extract pair in /tests/cases while the image
is built, so no compiler is present when the port runs. The port runs in a
separate, unprivileged process group on copies of the inputs, and each statement
file it writes is compared byte for byte.
"""

import os
import shutil
import signal
import subprocess
import tempfile

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
CASES = os.path.join(HERE, "cases")
EXPECTED = os.path.join(HERE, "expected")
PORT = os.environ.get("WBILL_PORT", "/app/port/wbill.py")
PYTHON = "/usr/local/bin/python3" if os.path.exists("/usr/local/bin/python3") else "python3"


def _expected(name):
    with open(os.path.join(EXPECTED, name + ".stmt"), "rb") as fh:
        return fh.read()


def _run_port(name):
    """Run the port on one extract pair as an unprivileged user; return its output bytes."""
    scratch = tempfile.mkdtemp(prefix="wbill-")
    os.chmod(scratch, 0o777)
    readings = os.path.join(scratch, "custin.dat")
    payments = os.path.join(scratch, "payin.dat")
    output = os.path.join(scratch, "stmtout.txt")
    shutil.copyfile(os.path.join(CASES, name + ".dat"), readings)
    shutil.copyfile(os.path.join(CASES, name + ".pay"), payments)
    for path in (readings, payments):
        os.chmod(path, 0o444)
    env = {"PATH": "/usr/local/bin:/usr/bin:/bin", "HOME": scratch, "LANG": "C.UTF-8"}
    command = [PYTHON, "-s", "-S", PORT, readings, payments, output]
    demote = os.geteuid() == 0
    proc = subprocess.Popen(
        ["setpriv", "--reuid=65534", "--regid=65534", "--clear-groups", "--no-new-privs"] + command
        if demote else command,
        cwd=scratch, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
    try:
        _, err = proc.communicate(timeout=120)
    except subprocess.TimeoutExpired:
        err = b"timed out after 120 s"
    finally:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        proc.wait()
    try:
        assert proc.returncode == 0, "the port failed:\n" + err.decode("utf-8", "replace")[-2000:]
        assert os.path.exists(output), "the port wrote no output file"
        with open(output, "rb") as fh:
            return fh.read()
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def check(name):
    got, want = _run_port(name), _expected(name)
    if got == want:
        return
    got_lines, want_lines = got.split(b"\n"), want.split(b"\n")
    for number, (a, b) in enumerate(zip(got_lines, want_lines), start=1):
        if a != b:
            pytest.fail(f"line {number} differs:\n  port: {a!r}\n  job:  {b!r}")
    pytest.fail(f"output has {len(got_lines)} lines where the job step writes {len(want_lines)}")


def test_every_case_has_an_expected_statement():
    cases = sorted(f[:-4] for f in os.listdir(CASES) if f.endswith(".dat"))
    assert cases == sorted(f[:-5] for f in os.listdir(EXPECTED) if f.endswith(".stmt"))
    assert cases == sorted(NAMES)


NAMES = ['band_boundaries', 'credit_balances', 'date_and_region', 'district_run', 'empty_file', 'header_missing', 'header_only', 'header_out_of_place', 'large_commercial_accounts', 'long_run', 'meter_rollover', 'names_of_every_shape', 'postings_amount_forms', 'postings_empty', 'postings_kinds_and_accounts', 'postings_memos', 'postings_ordinary', 'postings_rounding_modes', 'postings_with_fewer_fields', 'rejected_records', 'rounding_boundaries', 'short_lines', 'two_headers', 'zero_amounts']


def test_band_boundaries():
    check("band_boundaries")


def test_credit_balances():
    check("credit_balances")


def test_date_and_region():
    check("date_and_region")


def test_district_run():
    check("district_run")


def test_empty_file():
    check("empty_file")


def test_header_missing():
    check("header_missing")


def test_header_only():
    check("header_only")


def test_header_out_of_place():
    check("header_out_of_place")


def test_large_commercial_accounts():
    check("large_commercial_accounts")


def test_long_run():
    check("long_run")


def test_meter_rollover():
    check("meter_rollover")


def test_names_of_every_shape():
    check("names_of_every_shape")


def test_postings_amount_forms():
    check("postings_amount_forms")


def test_postings_empty():
    check("postings_empty")


def test_postings_kinds_and_accounts():
    check("postings_kinds_and_accounts")


def test_postings_memos():
    check("postings_memos")


def test_postings_ordinary():
    check("postings_ordinary")


def test_postings_rounding_modes():
    check("postings_rounding_modes")


def test_postings_with_fewer_fields():
    check("postings_with_fewer_fields")


def test_rejected_records():
    check("rejected_records")


def test_rounding_boundaries():
    check("rounding_boundaries")


def test_short_lines():
    check("short_lines")


def test_two_headers():
    check("two_headers")


def test_zero_amounts():
    check("zero_amounts")
