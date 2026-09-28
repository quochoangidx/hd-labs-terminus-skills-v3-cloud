"""Expectation model for SOP MIC-14 (aerobic plate count results).

Written from /app/docs/apc-sop.md alone: it never imports or runs the
platecount package. ``report(batch)`` returns the report the SOP gives for a
decoded batch file, in the layout the README describes. Each step cites the
SOP section it comes from.
"""

from fractions import Fraction

COUNTABLE_LOW = 20  # 2.4
COUNTABLE_HIGH = 300  # 2.4, 2.5, 4.4
UNITS = {"g": "CFU/g", "mL": "CFU/mL"}  # 1.1
KINDS = {"count": "", "estimate": "", "below": "<", "above": ">"}  # 4.3, 4.4, 5.1


def dilution(step):
    """2.1: the dilution at step k is 10^-k."""
    return Fraction(1, 10 ** step)


def plated_amount(dil):
    """2.2: volume plated times dilution (1.3: 1.0 or 0.1 mL)."""
    return Fraction(str(dil["volume"])) * dilution(dil["step"])


def colonies(reading):
    """2.3: a plate's colonies are its reading (None: too numerous, no reading)."""
    return reading


def is_countable(reading):
    """2.4."""
    return reading is not None and COUNTABLE_LOW <= reading <= COUNTABLE_HIGH


def is_crowded(reading):
    """2.5."""
    return reading is None or reading > COUNTABLE_HIGH


def is_sparse(reading):
    """2.6."""
    return reading is not None and reading < COUNTABLE_LOW


def counted_dilutions(dils):
    """2.7: the first dilution with a countable plate, plus the dilution a tenth of it
    (step + 1) when it was plated and holds a countable plate."""
    for i, dil in enumerate(dils):
        if any(is_countable(r) for r in dil["plates"]):
            chosen = [dil]
            for other in dils[i + 1:]:
                if other["step"] == dil["step"] + 1 and any(is_countable(r) for r in other["plates"]):
                    chosen.append(other)
            return chosen
    return []


def ratio(plates):
    """Colonies over the sum of plated amounts of (reading, amount) pairs."""
    return Fraction(sum(r for r, _a in plates)) / sum(a for _r, a in plates)


def result(sample):
    """(kind, exact value) for one sample."""
    dils = sample["dilutions"]
    counted = counted_dilutions(dils)
    if counted:  # 4.1 over the counted plates (2.8): plates of the counted dilutions not crowded
        plates = [(r, plated_amount(d)) for d in counted for r in d["plates"] if not is_crowded(r)]
        return "count", ratio(plates)
    crowded = [d for d in dils if any(is_crowded(r) for r in d["plates"])]
    if crowded:  # 4.4: last dilution holding a crowded plate
        return "above", COUNTABLE_HIGH / plated_amount(crowded[-1])
    # 2.6: neither countable nor crowded plate -> sparse sample
    for d in dils:
        if any(r > 0 for r in d["plates"]):  # 4.2
            return "estimate", ratio([(r, plated_amount(d)) for r in d["plates"]])
    return "below", 1 / plated_amount(dils[0])  # 4.3


def two_figures(value):
    """1.2: (digits 10..99, power) rounded to two significant figures, half up."""
    power = 0
    while value >= Fraction(10) ** (power + 1):
        power += 1
    while value < Fraction(10) ** power:
        power -= 1
    scaled = value / Fraction(10) ** (power - 1)  # in [10, 100)
    digits = int(scaled)
    if scaled - digits >= Fraction(1, 2):
        digits += 1
    if digits == 100:
        digits, power = 10, power + 1
    return digits, power


def written(value):
    """1.2: d.dEk."""
    digits, power = two_figures(value)
    return f"{digits // 10}.{digits % 10}E{power}"


def report(batch):
    rows = []
    for sample in batch["samples"]:
        kind, value = result(sample)
        rows.append({
            "id": sample["id"],
            "unit": UNITS[sample["unit"]],
            "kind": kind,
            "apc": KINDS[kind] + written(value),
        })
    return {"batch": batch["batch"], "samples": rows}


def within_limits(batch):
    """Section 1.3 limits; returns a list of violations (empty when the batch is inside)."""
    bad = []
    samples = batch.get("samples", [])
    if not 1 <= len(samples) <= 200:
        bad.append("sample count")
    ids = [s["id"] for s in samples]
    if len(set(ids)) != len(ids):
        bad.append("duplicate id")
    ok_chars = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-")
    for s in samples:
        if not (1 <= len(s["id"]) <= 12 and set(s["id"]) <= ok_chars):
            bad.append(f"id {s['id']!r}")
        if s["unit"] not in UNITS:
            bad.append("unit")
        dils = s["dilutions"]
        if not 1 <= len(dils) <= 8:
            bad.append(f"{s['id']}: dilution count")
        steps = [d["step"] for d in dils]
        if steps != sorted(set(steps)) or any(not (type(k) is int and 0 <= k <= 9) for k in steps):
            bad.append(f"{s['id']}: steps")
        for d in dils:
            if d["volume"] not in (1.0, 0.1) or type(d["volume"]) is not float:
                bad.append(f"{s['id']}: volume")
            if not 1 <= len(d["plates"]) <= 4:
                bad.append(f"{s['id']}: plate count")
            for r in d["plates"]:
                if r is not None and not (type(r) is int and 0 <= r <= 5000):
                    bad.append(f"{s['id']}: reading {r!r}")
    return bad
