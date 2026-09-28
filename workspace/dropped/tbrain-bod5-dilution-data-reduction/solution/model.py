"""Expectation model for SOP WQ-14 (five-day BOD batch reduction).

Written from /app/docs/sop-wq14-bod5.md alone; it never imports or runs the
bodcalc package. ``report(batch)`` returns the report the SOP gives for a batch,
in the layout of SOP section 8. Each step cites the rule it comes from. Where the
SOP defines no figure for a batch, the figure is worked out as the shipped
package works it out ("Shipped step"), from quantities the SOP defines.
"""

from decimal import ROUND_HALF_UP, Decimal

BOTTLE_ML = 300.0  # 1.1
USABLE_DEPLETION = 2.50  # 2.4
SPENT_BELOW = 1.20  # 2.3
BLANK_LIMIT = 0.20  # 7.1
CHECK_RANGE = (175.0, 225.0)  # 7.2
RPD_LIMIT = 25.0  # 6.2


def fl(x):
    return float(x)


def depletion(b):  # 2.1
    return fl(b["do_initial"]) - fl(b["do_final"])


def fraction(b):  # 2.2
    return fl(b["sample_ml"]) / BOTTLE_ML


def spent(b):  # 2.3
    return fl(b["do_final"]) < SPENT_BELOW


def usable(b):  # 2.4
    return (not spent(b)) and depletion(b) >= USABLE_DEPLETION


def seed_factor(controls):
    """2.5, 3.1-3.2: mean seed rate of the reference controls (the usable
    controls, or every control when none is usable)."""
    refs = [c for c in controls if usable(c)]
    if not refs:
        refs = list(controls)
    rates = [depletion(c) / fl(c["seed_ml"]) for c in refs]
    return sum(rates) / len(rates)


def bottle_bod(b, factor):  # 3.3, 4.1
    return (depletion(b) - factor * fl(b["seed_ml"])) / fraction(b)


def first_by(bottles, key, pick):  # 5.4: first listed on a tie
    best = bottles[0]
    for b in bottles[1:]:
        if pick(key(b), key(best)):
            best = b
    return best


def sample_result(sample, factor):
    """5.1-5.3: (relation, unrounded value, measured BOD or None)."""
    bottles = sample["bottles"]
    good = [b for b in bottles if usable(b)]
    if good:
        m = sum(bottle_bod(b, factor) for b in good) / len(good)
        return "=", m, m
    if all(spent(b) for b in bottles):
        least = first_by(bottles, lambda b: fl(b["sample_ml"]), lambda a, c: a < c)
        return ">", bottle_bod(least, factor), None
    most = first_by(bottles, lambda b: fl(b["sample_ml"]), lambda a, c: a > c)
    return "<", USABLE_DEPLETION / fraction(most), None


def rpd(mine, theirs):
    """6.1 when both samples have a measured BOD.

    Otherwise the SOP defines no RPD. Shipped step: the difference of the two
    samples' values without sign, as a percentage of the value of the sample
    duplicated, using the values of section 5 before rounding.
    """
    (_, v_mine, m_mine), (_, v_theirs, m_theirs) = mine, theirs
    if m_mine is not None and m_theirs is not None:
        return abs(m_mine - m_theirs) / ((m_mine + m_theirs) / 2.0) * 100.0
    return abs(v_mine - v_theirs) / v_theirs * 100.0


def three_sig(x):
    """1.2: three significant figures, half away from nought."""
    d = Decimal(repr(float(x)))
    if d == 0:
        return 0.0
    exp = d.adjusted() - 2
    q = Decimal(1).scaleb(exp)
    return float(d.quantize(q, rounding=ROUND_HALF_UP))


def report(batch):
    factor = seed_factor(batch["seed_controls"])
    blank = max(depletion(b) for b in batch["blanks"])  # 7.1
    good = [b for b in batch["check"]["bottles"] if usable(b)]
    check = sum(bottle_bod(b, factor) for b in good) / len(good)  # 7.2
    quals = ""
    if blank > BLANK_LIMIT:
        quals += "B"
    if check < CHECK_RANGE[0] or check > CHECK_RANGE[1]:
        quals += "G"
    found = {s["id"]: sample_result(s, factor) for s in batch["samples"]}
    dups = []
    for s in batch["samples"]:
        of = s.get("duplicate_of")
        if of is None:
            continue
        r = rpd(found[s["id"]], found[of])
        dups.append({"id": s["id"], "of": of, "rpd": r, "pass": r <= RPD_LIMIT})
    return {
        "batch": batch["batch"],
        "seed_factor": float(factor),
        "blank_depletion": float(blank),
        "check_value": three_sig(check),
        "qualifiers": quals,
        "samples": [
            {"id": s["id"], "relation": found[s["id"]][0], "value": three_sig(found[s["id"]][1])}
            for s in batch["samples"]
        ],
        "duplicates": dups,
    }


def limits_ok(batch):
    """Executable form of SOP 1.5 margins (on this model's own figures)."""
    alld = []
    for c in batch["seed_controls"]:
        alld.append(c)
    alld += batch["check"]["bottles"]
    for s in batch["samples"]:
        alld += s["bottles"]
    for b in alld:
        if abs(depletion(b) - 2.50) < 0.005 or abs(fl(b["do_final"]) - 1.20) < 0.005:
            return False
    for b in batch["blanks"]:
        if abs(depletion(b) - 0.20) < 0.005:
            return False
    if not any(usable(b) for b in batch["check"]["bottles"]):
        return False
    factor = seed_factor(batch["seed_controls"])
    good = [b for b in batch["check"]["bottles"] if usable(b)]
    check = sum(bottle_bod(b, factor) for b in good) / len(good)
    vals = [check]
    if abs(check - 175.0) < 1e-6 or abs(check - 225.0) < 1e-6:
        return False
    found = {s["id"]: sample_result(s, factor) for s in batch["samples"]}
    vals += [v for _, v, _ in found.values()]
    for s in batch["samples"]:
        if s.get("duplicate_of") is not None:
            if abs(rpd(found[s["id"]], found[s["duplicate_of"]]) - 25.0) < 1e-6:
                return False
    for v in vals:
        d = Decimal(repr(v))
        scaled = d.scaleb(-(d.adjusted() - 2))
        frac = scaled - scaled.to_integral_value(rounding="ROUND_FLOOR")
        if abs(frac - Decimal("0.5")) < Decimal("1e-9") * scaled:
            return False
    return True
