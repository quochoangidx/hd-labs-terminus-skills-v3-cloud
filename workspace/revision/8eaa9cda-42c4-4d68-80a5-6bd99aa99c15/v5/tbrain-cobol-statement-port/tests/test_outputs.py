"""Verifier for the Python port of the WBILL job step.

The expected statement files are the job step's own output: the verifier image
builds /tests/legacy/WBILL.cbl (the verifier's copy of the program) with
GnuCOBOL 3.1.2 and runs it on every extract pair in /tests/cases while the image
is built, so no compiler is present when the port runs. The port runs in a
separate, unprivileged process group on copies of the inputs, invoked exactly as
the instruction documents under names that do not identify the case, and each
statement file it writes is compared byte for byte. The image itself confines it
to Python and the standard library: the unprivileged user can start and read no
program other than the Python interpreter, and the system interpreter has no
third-party packages installed.
"""

import os
import shutil
import signal
import stat
import subprocess
import tempfile
import time

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
CASES = os.path.join(HERE, "cases")
EXPECTED = os.path.join(HERE, "expected")
PORT = os.environ.get("WBILL_PORT", "/app/port/wbill.py")
PYTHON = "/usr/local/bin/python3" if os.path.exists("/usr/local/bin/python3") else "python3"
# The port has no time limit of its own: every run shares what is left of the
# verifier's 1800 s, less a margin for starting up and reporting.
DEADLINE = time.monotonic() + 1650


def _expected(name):
    with open(os.path.join(EXPECTED, name + ".stmt"), "rb") as fh:
        return fh.read()


def _run_port_paths(readings_source, payments_source):
    """Run the port on one extract pair as an unprivileged user; return its output bytes.

    The three files sit in different directories of a fresh, randomly named scratch
    tree, under the same neutral names for every case, and the port runs from a
    fourth, empty directory: only the paths it is given lead to them, and nothing it
    can see (argv, cwd, environment) says which case it is running."""
    port_stat = os.lstat(PORT)
    assert stat.S_ISREG(port_stat.st_mode), "the submitted port must be one regular Python file"
    scratch = tempfile.mkdtemp(prefix="wbill-")
    os.chmod(scratch, 0o755)
    dirs = {}
    for role in ("extract", "export", "print", "cwd"):
        dirs[role] = os.path.join(scratch, role)
        os.mkdir(dirs[role])
        os.chmod(dirs[role], 0o777 if role in ("print", "cwd") else 0o755)
    readings = os.path.join(dirs["extract"], "readings.dat")
    payments = os.path.join(dirs["export"], "payments.txt")
    output = os.path.join(dirs["print"], "statement.out")
    shutil.copyfile(readings_source, readings)
    shutil.copyfile(payments_source, payments)
    for path in (readings, payments):
        os.chmod(path, 0o444)
    env = {"PATH": "/usr/local/bin:/usr/bin:/bin", "HOME": dirs["cwd"], "LANG": "C.UTF-8"}
    command = [PYTHON, PORT, readings, payments, output]
    demote = os.geteuid() == 0
    proc = subprocess.Popen(
        ["setpriv", "--reuid=65534", "--regid=65534", "--clear-groups", "--no-new-privs"] + command
        if demote else command,
        cwd=dirs["cwd"], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
    try:
        _, err = proc.communicate(timeout=max(1.0, DEADLINE - time.monotonic()))
    except subprocess.TimeoutExpired:
        err = b"ran past the verifier's time budget"
    finally:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        proc.wait()
    try:
        assert proc.returncode == 0, "the port failed:\n" + err.decode("utf-8", "replace")[-2000:]
        try:
            output_stat = os.lstat(output)
        except FileNotFoundError:
            pytest.fail("the port wrote no output file")
        assert stat.S_ISREG(output_stat.st_mode), "the port output must be a regular file"
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
        fd = os.open(output, flags)
        assert stat.S_ISREG(os.fstat(fd).st_mode), "the opened port output must be a regular file"
        with os.fdopen(fd, "rb") as fh:
            return fh.read()
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def _run_port(name):
    return _run_port_paths(
        os.path.join(CASES, name + ".dat"),
        os.path.join(CASES, name + ".pay"),
    )


def compare(got, want):
    if got == want:
        return
    got_lines, want_lines = got.split(b"\n"), want.split(b"\n")
    for number, (a, b) in enumerate(zip(got_lines, want_lines), start=1):
        if a != b:
            pytest.fail(f"line {number} differs:\n  port: {a!r}\n  job:  {b!r}")
    pytest.fail(f"output has {len(got_lines)} lines where the job step writes {len(want_lines)}")


def check(name):
    compare(_run_port(name), _expected(name))


def test_every_case_has_an_expected_statement():
    cases = sorted(f[:-4] for f in os.listdir(CASES) if f.endswith(".dat"))
    assert cases == sorted(f[:-5] for f in os.listdir(EXPECTED) if f.endswith(".stmt"))
    assert cases == sorted(NAMES + GENERATED)


NAMES = [
    'band_boundaries',
    'blank_line_first',
    'credit_balances',
    'date_and_region',
    'district_run',
    'empty_file',
    'header_date_and_part_region',
    'header_missing',
    'header_only',
    'header_out_of_place',
    'large_commercial_accounts',
    'long_run',
    'meter_rollover',
    'names_of_every_shape',
    'other_record_types',
    'postings_account_identifiers',
    'postings_amount_forms',
    'postings_empty',
    'postings_kinds_and_accounts',
    'postings_memos',
    'postings_ordinary',
    'postings_rounding_modes',
    'postings_with_fewer_fields',
    'rejected_records',
    'rounding_boundaries',
    'short_header',
    'short_lines',
    'two_headers',
    'zero_amounts',
]
# Extract pairs drawn at random, with a fixed seed, from the whole input contract.
GENERATED = [f"generated_{n:02d}" for n in range(1, 25)]


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
    # The instruction promises files of up to 500 records each; this pair is at
    # that size on both streams, so a port with a smaller fixed capacity cannot
    # pass on the shorter fixtures alone.
    with open(os.path.join(CASES, "long_run.dat"), "rb") as fh:
        readings = fh.read().split(b"\n")[:-1]
    with open(os.path.join(CASES, "long_run.pay"), "rb") as fh:
        postings = fh.read().split(b"\n")[:-1]
    assert len(readings) == 500 and sum(r.startswith(b"C") for r in readings) == 499
    assert len(postings) == 500
    check("long_run")


def test_meter_rollover():
    check("meter_rollover")


def test_names_of_every_shape():
    check("names_of_every_shape")


def test_postings_account_identifiers():
    check("postings_account_identifiers")


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


def test_other_record_types():
    check("other_record_types")


def test_short_header():
    check("short_header")


def test_header_date_and_part_region():
    check("header_date_and_part_region")


def test_blank_line_first():
    check("blank_line_first")


def test_generated_01():
    check("generated_01")


def test_generated_02():
    check("generated_02")


def test_generated_03():
    check("generated_03")


def test_generated_04():
    check("generated_04")


def test_generated_05():
    check("generated_05")


def test_generated_06():
    check("generated_06")


def test_generated_07():
    check("generated_07")


def test_generated_08():
    check("generated_08")


def test_generated_09():
    check("generated_09")


def test_generated_10():
    check("generated_10")


def test_generated_11():
    check("generated_11")


def test_generated_12():
    check("generated_12")


def test_generated_13():
    check("generated_13")


def test_generated_14():
    check("generated_14")


def test_generated_15():
    check("generated_15")


def test_generated_16():
    check("generated_16")


def test_generated_17():
    check("generated_17")


def test_generated_18():
    check("generated_18")


def test_generated_19():
    check("generated_19")


def test_generated_20():
    check("generated_20")


def test_generated_21():
    check("generated_21")


def test_generated_22():
    check("generated_22")


def test_generated_23():
    check("generated_23")


def test_generated_24():
    check("generated_24")
