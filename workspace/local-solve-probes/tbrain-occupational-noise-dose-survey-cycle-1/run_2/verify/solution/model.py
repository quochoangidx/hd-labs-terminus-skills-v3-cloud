"""Expectation model for noise survey manual HC-4.

Written from /app/docs/noise-survey-manual.md alone: it never imports or runs
the noisedose package. ``report(survey)`` returns the report the manual
gives for a decoded survey, in the layout the README describes. Each step
cites the manual rule it comes from.
"""

from decimal import ROUND_HALF_UP, Decimal
import math

READING_FLOOR_DBA = 40.0  # 2.2
THRESHOLD_DBA = 80.0  # 2.3
CRITERION_DBA = 85.0  # 3.1
EXCHANGE_DB = 3.0  # 3.1
CEILING_DBA = 115.0  # 5.1
IMPULSE_DBC = 140.0  # 2.6
ACTION_DB = 82.0  # 5.3
LIMIT_DB = 85.0  # 5.3


def reference_duration(level):
    """3.1: minutes at ``level`` that make a 100 per cent dose."""
    return 480.0 / 2.0 ** ((level - CRITERION_DBA) / EXCHANGE_DB)


def readings_of(log):
    """2.2: the runs logged at 40.0 dBA or more."""
    return [(minutes, level) for minutes, level in log if level >= READING_FLOOR_DBA]


def sampled_time(log):
    """2.4: total length of the readings."""
    return sum(minutes for minutes, _level in readings_of(log))


def measured_dose(log):
    """3.2: 100 x sum of length / reference duration over counted readings (2.3)."""
    total = 0.0
    for minutes, level in readings_of(log):
        if level >= THRESHOLD_DBA:
            total += minutes / reference_duration(level)
    return 100.0 * total


def is_full_shift(sampled, shift_minutes):
    """2.5: sampled time at least three quarters of the shift (exact in integers)."""
    return 4 * sampled >= 3 * shift_minutes


def shift_dose(log, shift_minutes):
    """3.3 for a full-shift survey. The manual gives no rule for any other survey's
    shift dose, so the shipped step stands there, applied to the sampled time and
    measured dose the manual defines (instruction: every other step follows the manual)."""
    sampled = sampled_time(log)
    measured = measured_dose(log)
    if is_full_shift(sampled, shift_minutes):
        if sampled < shift_minutes:
            return measured * shift_minutes / sampled
        return measured
    # Shipped step (the package's shift.py, left as it is): nought with nothing
    # sampled, otherwise scaled up to 480 minutes when fewer were sampled.
    if sampled == 0:
        return 0.0
    if sampled < 480:
        return measured * 480 / sampled
    return measured


def twa_unrounded(dose):
    """4.1: TWA of a dose above nought; None for a dose of nought."""
    if dose <= 0.0:
        return None
    return CRITERION_DBA + EXCHANGE_DB * math.log2(dose / 100.0)


def reported_tenth(value):
    """1.2: nearest tenth of a decibel, an exact half going up (exact on the float's value)."""
    if value is None:
        return None
    return float(Decimal(value).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))


def status(twa, flagged=False):
    """5.3: "over" for a flagged worker (5.1, 5.2); otherwise the bands on the reported TWA.
    6.1: a group is judged on its TWA alone (flagged=False)."""
    if flagged:
        return "over"
    if twa is None:
        return "below"
    if twa > LIMIT_DB:
        return "over"
    if twa >= ACTION_DB:
        return "action"
    return "below"


def mean(figures):
    """1.3: sum over count (a group always has a member)."""
    return sum(figures) / len(figures)


def worker_figures(worker):
    """Shift dose and the report row of one worker."""
    log = [(int(minutes), float(level)) for minutes, level in worker["log"]]
    dose = shift_dose(log, int(worker["shift_minutes"]))
    twa = reported_tenth(twa_unrounded(dose))
    ceiling = any(level > CEILING_DBA for _minutes, level in readings_of(log))  # 5.1
    impulse = any(float(peak) >= IMPULSE_DBC for peak in worker["peaks"])  # 5.2, 2.6
    row = {
        "id": worker["id"],
        "group": worker["group"],
        "dose": dose,
        "twa": twa,
        "status": status(twa, ceiling or impulse),
        "ceiling": ceiling,
        "impulse": impulse,
    }
    return dose, row


def report(survey):
    """The report of one decoded survey (README layout)."""
    workers = []
    doses_by_code = {}
    for worker in survey["workers"]:
        dose, row = worker_figures(worker)
        workers.append(row)
        doses_by_code.setdefault(worker["group"], []).append(dose)  # 6.1: every member's shift dose
    groups = []
    for code in sorted(doses_by_code):  # README: ascending character order
        dose = mean(doses_by_code[code])
        twa = reported_tenth(twa_unrounded(dose))
        groups.append({"group": code, "dose": dose, "twa": twa, "status": status(twa)})
    return {"survey": survey["survey"], "workers": workers, "groups": groups}


def near_rounding_edge(survey, margin=1e-6):
    """True when some unrounded TWA of the survey sits within ``margin`` tenths of a
    rounding half, where two correct evaluation orders could round apart."""
    values = []
    doses_by_code = {}
    for worker in survey["workers"]:
        dose, _row = worker_figures(worker)
        values.append(twa_unrounded(dose))
        doses_by_code.setdefault(worker["group"], []).append(dose)
    values.extend(twa_unrounded(mean(d)) for d in doses_by_code.values())
    for value in values:
        if value is None:
            continue
        frac = (value * 10.0) % 1.0
        if abs(frac - 0.5) < margin:
            return True
    return False


if __name__ == "__main__":
    import json
    import sys

    with open(sys.argv[1], encoding="utf-8") as handle:
        json.dump(report(json.load(handle)), sys.stdout)
    sys.stdout.write("\n")
