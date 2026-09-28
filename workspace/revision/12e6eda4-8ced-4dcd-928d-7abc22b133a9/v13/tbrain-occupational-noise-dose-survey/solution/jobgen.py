"""Graded surveys for the noisedose verifier, one family per rule of manual HC-4.

Authoring code: solution/seal.py runs it, has solution/model.py work out every
expected report, and writes both into tests/expected/. Nothing here runs at
grading time. Random draws come from the constant SEED, never from candidate
files. Families that carry an input the manual leaves to today's code are named
in TRAP_INPUTS; every other family is kept free of such inputs by construction
and by the predicate in seal.py.
"""

import math
import random

SEED = 20260926

CODE_CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
ID_CHARS = CODE_CHARS + "-"


def W(wid, group, shift, log, peaks=()):
    return {"id": wid, "group": group, "shift_minutes": shift, "log": [[m, lv] for m, lv in log], "peaks": list(peaks)}


def S(name, *workers):
    return {"survey": name, "workers": list(workers)}


def steady(wid, group, level, shift=480, minutes=None, peaks=()):
    return W(wid, group, shift, [(minutes or shift, level)], peaks)


def dose_of(log):
    """Measured dose of a log of counted readings no higher than 115.0 dBA."""
    return 100.0 * sum(m * 2.0 ** ((lv - 85.0) / 3.0) / 480.0 for m, lv in log if lv >= 80.0)


def twa_of(dose):
    return 85.0 + 3.0 * math.log2(dose / 100.0)


def log_for_twa(lo, hi, rng):
    """A 480-minute full-shift log of two readings (the first counted) whose unrounded TWA lies in [lo, hi)."""
    for _ in range(200000):
        a = rng.randint(30, 450)
        l1, l2 = round(rng.uniform(80.0, 90.0), 1), round(rng.uniform(60.0, 90.0), 1)
        log = [(a, l1), (480 - a, l2)]
        t = twa_of(dose_of(log))
        if lo <= t < hi:
            return log
    raise AssertionError((lo, hi))


def families():
    rng = random.Random(SEED)
    fam = {}

    fam["reference_duration"] = [
        S("RD-1", steady("A1", "G1", 85.0), steady("A2", "G2", 88.0), steady("A3", "G3", 91.0),
          steady("A4", "G4", 80.0), steady("A5", "G5", 100.0), steady("A6", "G6", 110.5), steady("A7", "G7", 115.0)),
        S("RD-2", W("B1", "G1", 480, [(120, 97.3), (240, 86.4), (120, 102.8)]),
          W("B2", "G1", 600, [(1, 115.0), (599, 83.2)]),
          W("B3", "G2", 1440, [(1440, 81.5)])),
    ]
    fam["threshold"] = [
        S("TH-1", W("A1", "G1", 480, [(240, 80.0), (240, 90.0)]), W("A2", "G1", 480, [(240, 79.9), (240, 90.0)]),
          W("A3", "G2", 480, [(240, 80.1), (240, 90.0)])),
        S("TH-2", W("B1", "G1", 480, [(480, 80.0)]), W("B2", "G2", 600, [(100, 80.0), (100, 79.9), (400, 84.0)])),
    ]
    fam["sampled_time"] = [
        S("SA-1", W("A1", "G1", 480, [(200, 92.0), (200, 70.0)]), W("A2", "G1", 600, [(300, 90.0), (200, 60.0), (100, 40.0)])),
        S("SA-2", W("B1", "G1", 720, [(100, 95.0), (500, 79.9), (60, 55.5)]), W("B2", "G2", 480, [(479, 40.0), (1, 100.0)])),
    ]
    fam["paused_runs"] = [
        S("PA-1", W("A1", "G1", 480, [(200, 91.0), (60, 0.0), (170, 86.5), (45, 0.0)]),
          W("A2", "G1", 480, [(30, 0.0), (400, 93.0)])),
        S("PA-2", W("B1", "G1", 600, [(250, 88.0), (230, 90.5), (120, 0.0)]),
          W("B2", "G2", 1440, [(15, 0.0), (1200, 86.0), (15, 0.0)])),
    ]
    fam["partial_surveys"] = [
        S("PS-1", W("A1", "G1", 720, [(600, 90.0)]), W("A2", "G2", 600, [(599, 88.0)]), W("A3", "G3", 480, [(400, 89.0)])),
        S("PS-2", W("B1", "G1", 1440, [(1100, 86.0), (100, 92.0)]), W("B2", "G1", 360, [(300, 95.0)]),
          W("B3", "G2", 1000, [(760, 84.0)])),
    ]
    fam["whole_shift"] = [
        S("WS-1", W("A1", "G1", 360, [(420, 88.0)]), W("A2", "G1", 480, [(480, 88.0)]), W("A3", "G2", 60, [(480, 85.0)])),
        S("WS-2", W("B1", "G1", 1440, [(1440, 83.0), (1440, 86.0)]), W("B2", "G2", 600, [(700, 90.0)])),
    ]
    fam["three_quarters"] = [
        S("TQ-1", W("A1", "G1", 600, [(450, 90.0)]), W("A2", "G2", 480, [(360, 88.0)]), W("A3", "G3", 60, [(45, 95.0)])),
        S("TQ-2", W("B1", "G1", 1440, [(1080, 86.0)]), W("B2", "G2", 610, [(458, 90.0)])),
    ]
    fam["below_three_quarters"] = [
        S("BT-1", W("X1", "G1", 720, [(300, 90.0)]), W("X2", "G2", 1440, [(600, 88.0)]),
          W("X3", "G3", 360, [(120, 92.0), (60, 85.5)])),
        S("BT-2", W("Y1", "G1", 720, [(500, 85.0)]), W("Y2", "G2", 90, [(67, 85.0)]), W("Y3", "G3", 60, [(1, 99.0)]),
          W("Y4", "G4", 1440, [(479, 81.0)]), W("Y5", "G5", 610, [(457, 90.0)]), W("Y6", "G5", 600, [(300, 91.0)])),
        # Added after final_review F1; named after every other survey by seal.py so no earlier expectation moves.
        S("LATE", W("V1", "G1", 480, [(120, 88.0), (120, 70.0)]), W("V2", "G2", 720, [(200, 90.0), (100, 0.0), (100, 65.0)])),
    ]
    fam["measured_nothing"] = [
        S("MN-1", W("A1", "G1", 480, []), W("A2", "G1", 480, [(480, 90.0)]), W("A3", "G2", 600, [], [141.0])),
        S("MN-2", W("B1", "G1", 720, [(300, 0.0), (120, 0.0)]), W("B2", "G1", 720, [(600, 86.0)])),
    ]
    fam["above_ceiling"] = [
        S("AC-1", W("Y1", "G1", 480, [(400, 90.0), (20, 118.5)]), W("Y2", "G2", 480, [(470, 84.0), (10, 131.2)])),
        S("AC-2", W("Z1", "G1", 1440, [(1, 140.0), (1439, 82.0)]), W("Z2", "G1", 600, [(300, 115.1), (300, 86.0)])),
        # Added after v11 panel finding 2: groups with a ceiling-flagged member whose own TWA is "action" and "below".
        S("LATE", W("K1", "G1", 60, [(1, 115.1), (59, 40.0)]), W("K2", "G1", 60, [(60, 40.0)]),
          W("K3", "G1", 60, [(60, 40.0)]), W("K4", "G2", 480, [(1, 116.0), (479, 40.0)]),
          *[W(f"K{n}", "G2", 480, [(480, 40.0)]) for n in range(5, 9)]),
    ]
    fam["ceiling_level"] = [
        S("CL-1", W("A1", "G1", 480, [(1, 115.0), (479, 70.0)]), W("A2", "G2", 480, [(480, 115.0)])),
    ]
    fam["impulse"] = [
        S("IM-1", steady("A1", "G1", 81.0, peaks=[139.9]), steady("A2", "G1", 81.0, peaks=[139.9, 140.0]),
          steady("A3", "G2", 70.0, peaks=[170.0, 60.0]), steady("A4", "G2", 75.0)),
        # Added after v11 panel finding 1: the only impulse comes after a hundred quieter peaks.
        S("LATE", steady("P1", "G1", 70.0, peaks=[60.0] * 100 + [140.0]),
          steady("P2", "G1", 81.0, peaks=[round(60.0 + k / 10.0, 1) for k in range(799)][::2] + [139.9, 140.0])),
    ]
    fam["twa"] = [
        S("TW-1", steady("A1", "G1", 88.0), steady("A2", "G1", 76.0), W("A3", "G2", 480, [(1, 80.0), (479, 60.0)]),
          W("A4", "G3", 1440, [(1440, 97.0)])),
    ]
    rounding = []
    for k, (lo, hi) in enumerate([(84.05, 84.09), (84.01, 84.049), (86.55, 86.6), (86.5, 86.549), (79.95, 79.99)]):
        rounding.append(W(f"R{k}", f"G{k}", 480, log_for_twa(lo, hi, rng)))
    fam["rounding"] = [S("RO-1", *rounding)]
    status = [steady("S1", "G1", 81.9), steady("S2", "G2", 82.0), steady("S3", "G3", 85.0), steady("S4", "G4", 85.1)]
    for k, (lo, hi) in enumerate([(81.95, 81.999), (85.001, 85.049), (85.051, 85.09), (81.9, 81.949)]):
        status.append(W(f"T{k}", f"H{k}", 480, log_for_twa(lo, hi, rng)))
    status.append(steady("U1", "H9", 81.0, peaks=[140.0]))
    fam["status"] = [S("ST-1", *status)]
    fam["groups"] = [
        S("GR-1", steady("A1", "G1", 95.0), steady("A2", "G1", 83.0), steady("A3", "G1", 84.0),
          steady("B1", "G2", 86.0), W("B2", "G2", 600, [(500, 88.0)]), steady("C1", "G3", 89.2)),
    ]
    fam["quiet_members"] = [
        S("QM-1", steady("A1", "G1", 90.0), W("Q1", "G1", 480, [(300, 64.0), (180, 71.5)])),
        S("QM-2", W("Q2", "G1", 480, [(480, 79.9)]), W("Q3", "G1", 600, [(600, 45.0)]), steady("A2", "G1", 88.0),
          steady("A3", "G2", 60.0)),
    ]
    fam["report_order"] = [
        S("RO-2", steady("Z-9", "ZZ", 86.0), steady("A-1", "0", 84.0), steady("M-12345678AB", "A1B2C3D4", 83.0),
          steady("0", "9A", 88.0), steady("B-B", "A", 81.0), steady("C", "0", 89.0), steady("K", "AB", 82.5)),
    ]
    fam["limits_workers"] = [limits_workers(rng)]
    fam["limits_logs"] = [limits_logs(rng)]
    fam["generated"] = [generated(rng, k) for k in range(5)]
    return fam


# Families that carry an input the manual leaves to today's code (or a governed input kept out of the broad
# families): the predicate in seal.py checks every other family carries none of these.
TRAP_INPUTS = {
    "paused_runs": {"paused"},
    "below_three_quarters": {"below_three_quarters", "paused"},
    "measured_nothing": {"below_three_quarters", "paused"},
    "above_ceiling": {"above_ceiling"},
}

# Shipped-differential pairs: surveys a and b differ in one field the kept step does not use, so the
# shipped package gives each worker the same dose in both; the candidate must too.
def differential_pairs():
    pairs = {"below_three_quarters": [], "above_ceiling": [], "measured_nothing": []}
    for shift_a, shift_b, log in [(720, 1440, [(300, 90.0)]), (360, 600, [(120, 92.0), (60, 85.5)]),
                                  (1440, 1000, [(479, 81.0)]), (90, 120, [(67, 85.0)]), (720, 1400, [(500, 85.0)])]:
        pairs["below_three_quarters"].append([S("HC4-7001", W("X1", "G1", shift_a, log)), S("HC4-7002", W("X1", "G1", shift_b, log))])
    for level, rest in [(118.5, [(400, 90.0)]), (131.2, [(470, 84.0)]), (140.0, [(479, 82.0)]), (115.1, [(300, 86.0)])]:
        loud = [(10, level)] + rest
        flat = [(10, 115.0)] + rest
        shift = sum(m for m, _ in loud)
        pairs["above_ceiling"].append([S("HC4-7003", W("Y1", "G1", shift, loud)), S("HC4-7004", W("Y1", "G1", shift, flat))])
    for shift_a, shift_b, log in [(480, 1440, []), (720, 60, [(300, 0.0), (120, 0.0)])]:
        pairs["measured_nothing"].append([S("HC4-7005", W("N1", "G1", shift_a, log)), S("HC4-7006", W("N1", "G1", shift_b, log))])
    return pairs


def full_log(rng, shift, lo=40.0, hi=112.0, n=None):
    """A log whose readings cover at least three quarters of the shift, levels 40.0 to 112.0 dBA, no run at 0.0."""
    total = min(2880, rng.randint(-(-3 * shift // 4), min(2880, shift + shift // 2)))
    n = n or rng.randint(1, 12)
    runs, left = [], total
    for k in range(n):
        m = left if k == n - 1 else max(1, min(left - (n - k - 1), rng.randint(1, max(1, 2 * total // n))))
        if m <= 0:
            break
        m = min(m, 1440)
        runs.append((m, round(rng.uniform(lo, hi), 1)))
        left -= m
    while left > 0:
        m = min(left, 1440)
        runs.append((m, round(rng.uniform(lo, hi), 1)))
        left -= m
    return runs


def rand_code(rng, width=None):
    return "".join(rng.choice(CODE_CHARS) for _ in range(width or rng.randint(1, 8)))


def generated(rng, k):
    codes = sorted({rand_code(rng) for _ in range(rng.randint(1, 6))})
    workers, ids = [], set()
    for n in range(rng.randint(1, 12)):
        while True:
            wid = "".join(rng.choice(ID_CHARS) for _ in range(rng.randint(1, 12)))
            if wid not in ids:
                ids.add(wid)
                break
        shift = rng.choice([60, 360, 480, 600, 720, 1440, rng.randint(60, 1440)])
        peaks = [round(rng.uniform(60.0, 170.0), 1) for _ in range(rng.choice([0, 0, 1, 3, 8]))]
        workers.append(W(wid, rng.choice(codes), shift, full_log(rng, shift), peaks))
    return S(f"GEN-{k}", *workers)


def limits_workers(rng):
    codes = ["ABCDEFGH"] + [c for c in CODE_CHARS[:26]] + [f"Z{d}" for d in range(10)] + ["Q9", "X7", "Y0"]
    assert len(set(codes)) == 40
    workers = []
    for k in range(300):
        shift = [60, 1440, 480][k % 3]
        workers.append(W(f"L{k:03d}-" + "X" * (7 if k == 0 else 0), codes[k % 40], shift,
                         [(shift, round(rng.uniform(70.0, 100.0), 1))]))
    return S("LIM-WORKERS", *workers)


def limits_logs(rng):
    long_log = [(1 + (k % 2), round(rng.uniform(40.0, 115.0), 1)) for k in range(1500)]
    long_log[0] = (1, 40.0)
    long_log[1] = (1, 115.0)
    two_days = [(1440, 88.0), (1440, 81.0)]
    return S("LIM-LOGS",
             W("L-1500", "G1", 1440, long_log),
             W("L-2880", "G1", 1440, two_days),
             W("L-PEAKS", "G2", 60, [(1, 90.0), (59, 80.0)], [60.0] + [round(rng.uniform(60.0, 139.9), 1) for _ in range(498)] + [170.0]))
