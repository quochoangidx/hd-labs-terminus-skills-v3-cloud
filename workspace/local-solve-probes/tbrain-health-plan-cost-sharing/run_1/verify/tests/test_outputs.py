"""Verifier for the costshare repair.

Every job runs the verifier's own driver (/opt/driver/run_ops.py) as an
unprivileged user against the delivered package in /app/src. Expected values
come from tests/model.py, which works them out from /app/docs/cost-sharing.md
without importing the package. Where the note is silent, the expected value is
also read from the shipped package (/opt/shipped) and the two must agree.
"""

import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import model  # noqa: E402

DRIVER = "/opt/driver/run_ops.py"
CANDIDATE = "/app/src"
SHIPPED = "/opt/shipped"
JOB_ENV = {"PATH": "/usr/local/bin:/usr/bin:/bin", "HOME": "/nonexistent", "LANG": "C.UTF-8"}
DEMOTE = ["setpriv", "--reuid=65534", "--regid=65534", "--clear-groups", "--no-new-privs", "--"]
MEMBERS = ["A", "B", "C"]


def run_job(ops, root=CANDIDATE):
    proc = subprocess.run(
        DEMOTE + [sys.executable, "-I", "-S", "-B", DRIVER, root],
        input=json.dumps(ops),
        capture_output=True,
        text=True,
        timeout=120,
        env=JOB_ENV,
        cwd="/",
        start_new_session=True,
        check=False,
    )
    assert proc.returncode == 0, f"job failed to run: {proc.stderr[-2000:]}"
    return json.loads(proc.stdout)


def plan(**changes):
    base = {
        "deductible": 50_000,
        "family_deductible": 100_000,
        "coinsurance": 2_500,
        "office_copay": 3_000,
        "oop_max": 200_000,
        "family_oop_max": 350_000,
    }
    base.update(changes)
    return base


def line(member, kind, allowed):
    return {"op": "line", "member": member, "kind": kind, "allowed": allowed}


def totals():
    return {"op": "totals", "members": MEMBERS}


def left(member):
    return {"op": "left", "member": member}


def with_totals(ops):
    """Read every total after every priced line."""
    out = []
    for op in ops:
        out.append(op)
        if op["op"] in {"line", "record"}:
            out.append(totals())
    return out


def check(ops, shipped_too=False):
    expected = model.run_ops(ops)
    got = run_job(ops)
    for index, (op, want, have) in enumerate(zip(ops, expected, got)):
        assert have == want, f"step {index} {op}: expected {want}, got {have}"
    assert len(got) == len(expected)
    if shipped_too:
        shipped = run_job(ops, SHIPPED)
        assert shipped == expected, "the model's reading of today's behaviour disagrees with the shipped package"
    return got


# 1. Money and rates


def test_share_rounds_half_to_even():
    cases = [(2, 2_500), (6, 2_500), (10, 2_500), (-6, 2_500), (-10, 2_500), (5, 5_000),
             (7, 5_000), (123_457, 3_333), (99_999, 1), (7, 10_000), (7, 0), (0, 4_000)]
    check([{"op": "share", "amount": a, "rate": r} for a, r in cases])


def test_share_outside_the_described_rates_keeps_todays_rounding():
    cases = [(2, 12_500), (10, 15_000), (1, 25_000), (6, -2_500), (3, -5_000),
             (-2, 12_500), (5, 10_002), (9, -1), (123_456, 20_001)]
    check([{"op": "share", "amount": a, "rate": r} for a, r in cases], shipped_too=True)


def test_facility_coinsurance_rounds_half_to_even():
    ops = [{"op": "new", "plan": plan(deductible=0, family_deductible=0)},
           line("A", "facility", 10), line("A", "facility", 2), line("B", "facility", 14),
           line("B", "facility", 4_006)]
    check(with_totals(ops))


def test_rates_outside_the_whole_price_with_todays_rounding():
    for rate in (12_500, -2_500, 30_000):
        ops = [{"op": "new", "plan": plan(deductible=0, family_deductible=0, coinsurance=rate,
                                          oop_max=0, family_oop_max=0)},
               line("A", "facility", 2), line("A", "facility", 6), line("B", "facility", 10),
               line("C", "facility", 4_002)]
        check(with_totals(ops), shipped_too=True)


# 2. Kinds


def test_other_kinds_are_priced_as_facility_lines():
    ops = [{"op": "new", "plan": plan()},
           line("A", "lab", 30_000), line("A", "imaging", 40_000), line("B", "", 1_000),
           left("A"), left("B")]
    check(with_totals(ops))


# 3. Preventive lines


def test_preventive_line_is_free_and_adds_nothing():
    ops = [{"op": "new", "plan": plan()},
           line("A", "facility", 20_000), line("A", "preventive", 30_000),
           line("B", "preventive", 5_000), left("A"), line("A", "facility", 40_000)]
    check(with_totals(ops))


# 4. Office lines


def test_office_copay_is_the_allowed_amount_when_smaller():
    ops = [{"op": "new", "plan": plan()},
           line("A", "office", 1_800), line("A", "office", 1), line("B", "office", 2_999),
           line("B", "office", 3_000), line("C", "office", 3_001)]
    check(with_totals(ops))


def test_office_line_of_zero_or_less_still_charges_the_copay():
    ops = [{"op": "new", "plan": plan()},
           line("A", "office", 0), line("A", "office", -2_500), line("B", "office", -1)]
    check(with_totals(ops))


def test_office_line_takes_no_deductible_or_coinsurance():
    ops = [{"op": "new", "plan": plan()},
           line("A", "office", 20_000), left("A"), line("A", "office", 3_004),
           line("A", "facility", 10_000)]
    check(with_totals(ops))


# 5. Facility lines


def test_deductible_is_met_part_way_across_lines():
    ops = [{"op": "new", "plan": plan()},
           line("A", "facility", 30_000), left("A"), line("A", "facility", 30_000), left("A"),
           line("A", "facility", 1_000), left("A")]
    check(with_totals(ops))


def test_family_deductible_limits_what_is_left():
    ops = [{"op": "new", "plan": plan(family_deductible=60_000)},
           line("A", "facility", 40_000), left("B"), line("B", "facility", 30_000),
           left("A"), left("C"), line("C", "facility", 8_000)]
    check(with_totals(ops))


def test_plan_without_family_deductible_uses_the_member_remainder():
    for family in (0, -1):
        ops = [{"op": "new", "plan": plan(family_deductible=family)},
               line("A", "facility", 40_000), left("B"), line("B", "facility", 30_000),
               left("B"), line("C", "facility", 60_000)]
        check(with_totals(ops))


def test_deductible_left_is_not_clamped():
    ops = [{"op": "new", "plan": plan(deductible=-2_000, family_deductible=0)},
           left("A"), line("A", "facility", 10_000), left("A"), line("B", "facility", 400)]
    check(with_totals(ops))


def test_coinsurance_is_taken_on_what_the_deductible_leaves():
    ops = [{"op": "new", "plan": plan()},
           line("A", "facility", 50_400), line("B", "facility", 20_000), line("B", "facility", 40_000)]
    check(with_totals(ops))


# 6. Out-of-pocket maximums


def test_member_maximum_cuts_the_share():
    ops = [{"op": "new", "plan": plan(deductible=10_000, oop_max=20_000)},
           line("A", "facility", 30_000), line("A", "facility", 40_000), line("A", "office", 5_000),
           line("A", "facility", 9_000)]
    check(with_totals(ops))


def test_family_maximum_cuts_before_a_member_reaches_their_own():
    ops = [{"op": "new", "plan": plan(deductible=10_000, family_deductible=0, oop_max=20_000,
                                      family_oop_max=30_000)},
           line("A", "facility", 42_000), line("B", "facility", 18_000), line("C", "facility", 20_000),
           line("C", "office", 4_000), line("A", "facility", 1_000)]
    check(with_totals(ops))


def test_family_maximum_applies_without_a_member_maximum():
    for member_max in (0, -5):
        ops = [{"op": "new", "plan": plan(deductible=10_000, family_deductible=0, oop_max=member_max,
                                          family_oop_max=25_000)},
               line("A", "facility", 42_000), line("B", "office", 5_000), line("B", "facility", 20_000),
               line("C", "facility", 3_000)]
        check(with_totals(ops))


def test_share_landing_exactly_on_a_maximum_leaves_no_room():
    ops = [{"op": "new", "plan": plan(deductible=10_000, family_deductible=0, oop_max=15_000,
                                      family_oop_max=0)},
           line("A", "facility", 30_000), line("A", "office", 5_000), line("A", "facility", 800)]
    check(with_totals(ops))


def test_cut_takes_coinsurance_then_copay_then_deductible():
    ops = [{"op": "new", "plan": plan(deductible=10_000, family_deductible=0, oop_max=12_000,
                                      family_oop_max=0)},
           line("A", "facility", 30_000),
           {"op": "new", "plan": plan(deductible=10_000, family_deductible=0, oop_max=4_000,
                                      family_oop_max=0)},
           line("B", "facility", 30_000),
           {"op": "new", "plan": plan(deductible=0, family_deductible=0, oop_max=1_000,
                                      family_oop_max=0)},
           line("C", "office", 8_000)]
    check(with_totals(ops))


def test_a_part_at_or_below_zero_gives_nothing_to_the_cut():
    ops = [{"op": "new", "plan": plan(deductible=1_000, family_deductible=0, coinsurance=-1_000,
                                      oop_max=500, family_oop_max=0)},
           line("A", "facility", 2_000), left("A"), line("A", "facility", 300)]
    check(with_totals(ops))


# 7. Totals


def test_deductible_total_counts_the_deductible_part_after_the_cut():
    ops = [{"op": "new", "plan": plan(deductible=30_000, family_deductible=0, oop_max=40_000,
                                      family_oop_max=0)},
           line("A", "office", 5_000), line("A", "office", 5_000), line("A", "office", 5_000),
           line("A", "office", 5_000), line("A", "office", 5_000), line("A", "office", 5_000),
           line("A", "office", 5_000), line("A", "office", 5_000), line("A", "office", 5_000),
           line("A", "office", 5_000), line("A", "facility", 20_000), left("A"),
           line("A", "facility", 20_000)]
    check(with_totals(ops))


def test_out_of_pocket_totals_include_the_copay():
    ops = [{"op": "new", "plan": plan()},
           line("A", "office", 5_000), line("B", "office", 2_000), line("A", "facility", 20_000),
           line("C", "office", 0)]
    check(with_totals(ops))


def test_family_total_without_a_family_maximum_keeps_todays_sum():
    for family_max in (0, -3):
        ops = [{"op": "new", "plan": plan(deductible=0, family_deductible=0, coinsurance=0,
                                          family_oop_max=family_max)},
               line("A", "office", 5_000), line("B", "facility", 7_000), line("B", "office", 4_000)]
        check(with_totals(ops), shipped_too=True)
        ops = [{"op": "new", "plan": plan(family_oop_max=family_max)},
               line("A", "office", 5_000), line("A", "facility", 60_000), line("B", "office", 1_200),
               line("B", "facility", 9_000)]
        check(with_totals(ops))


def test_ledger_record_called_directly():
    for family_max in (350_000, 0):
        ops = [{"op": "new", "plan": plan(family_oop_max=family_max)},
               {"op": "record", "member": "A", "deductible": 1_000, "copay": 3_000, "coinsurance": 250},
               {"op": "record", "member": "B", "deductible": 0, "copay": 4_000, "coinsurance": 0},
               {"op": "record", "member": "A", "deductible": -500, "copay": -3_000, "coinsurance": 7},
               left("A"), left("B")]
        check(with_totals(ops))


# Whole sessions


def lcg_session(seed, settings, count):
    state = seed
    ops = [{"op": "new", "plan": plan(**settings)}]
    kinds = ["facility", "facility", "office", "preventive", "facility", "lab"]
    for _ in range(count):
        state = (state * 6364136223846793005 + 1442695040888963407) % (1 << 64)
        member = MEMBERS[(state >> 20) % 3]
        kind = kinds[(state >> 30) % len(kinds)]
        allowed = (state >> 33) % 60_000 - 2_000
        if (state >> 10) % 11 == 0:
            allowed = (state >> 40) % 7
        ops.append(line(member, kind, allowed))
        if (state >> 50) % 5 == 0:
            ops.append(left(member))
    return with_totals(ops)


def test_long_session_ordinary_plan():
    check(lcg_session(11, {}, 250))


def test_long_session_tight_maximums():
    check(lcg_session(23, {"deductible": 40_000, "family_deductible": 70_000, "coinsurance": 3_500,
                           "oop_max": 90_000, "family_oop_max": 150_000}, 300))


def test_long_session_unusual_settings():
    check(lcg_session(37, {"deductible": 25_000, "family_deductible": 0, "coinsurance": 11_500,
                           "oop_max": 0, "family_oop_max": 120_000}, 250))
    check(lcg_session(41, {"family_deductible": -4, "coinsurance": 1_500, "oop_max": 60_000,
                           "family_oop_max": 0}, 250))


def test_driver_runs_the_delivered_package():
    out = run_job([{"op": "share", "amount": 1, "rate": 1}])
    assert out == [{"share": 0}]
