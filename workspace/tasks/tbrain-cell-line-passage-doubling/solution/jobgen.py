"""Seeded passage logs across the whole SOP CB-3 section 1 domain (authoring only).

`draw(rng, size, failed_counts=False, drain_banks=False)` returns one log. By default
every count is valid (viability 70.0 or more) and every bank keeps at least one vial in
stock, so a draw carries no input for which the SOP has no rule. The two flags let a
draw carry those inputs for the families that are about them.
"""

import math

import model

BANK_KINDS = ("MCB", "WCB-1", "WCB-2")


def _viability(rng, failed_counts):
    if failed_counts and rng.random() < 0.3:
        return rng.choice([69.9, 1.0, round(rng.uniform(1.0, 69.9), 1)])
    return rng.choice([70.0, 100.0, round(rng.uniform(70.0, 100.0), 1)])


def _count(rng):
    return int(round(10 ** rng.uniform(3, 9)))


def _harvest(rng, seeded):
    for _ in range(50):
        value = int(round(seeded * 2 ** rng.uniform(-3.0, 6.0)))
        if 1000 <= value <= 10**9:
            return value
    return max(1000, min(10**9, seeded))


def _lines(rng):
    lines = []
    for index in range(rng.randint(1, 4)):
        seed_pdl = rng.choice([0.0, 100.0, round(rng.uniform(0.0, 60.0), 2)])
        low = max(10.0, seed_pdl + 5.0)
        max_pdl = rng.choice([low, 300.0, round(rng.uniform(low, min(300.0, low + 60.0)), 2)])
        lines.append(
            {
                "name": f"L{rng.randint(1, 999):03d}-{index}",
                "seed_pdl": seed_pdl,
                "seed_passage": rng.randint(0, 50),
                "max_pdl": max_pdl,
            }
        )
    return lines


def _within_limits(log):
    """Executable form of SOP 1.5's lineage limits and margins."""
    tree = model.Lineage(log)
    for rec in log["records"]:
        if rec["kind"] != "culture":
            continue
        _, pdl, age, _ = tree.figures(rec["id"])
        if not -100.0 <= pdl <= 1000.0:
            return False
        top = tree.lines[tree.line_of(rec["id"])]["max_pdl"]
        if abs(age - top) <= 1e-6 or abs(age - (top - 3.0)) <= 1e-6:
            return False
    return True


def draw(rng, size, failed_counts=False, drain_banks=False):
    while True:
        log = _draw_once(rng, size, failed_counts, drain_banks)
        if _within_limits(log):
            return log


def _draw_once(rng, size, failed_counts, drain_banks):
    lines = _lines(rng)
    names = [line["name"] for line in lines]
    records = []
    suspensions = []  # (id, line)
    cultures = []  # (id, line)
    freezes = {}  # id -> [line, bank, vials, thawed]
    bank_left = {}
    counter = [0]

    def new_id(prefix):
        counter[0] += 1
        return f"{prefix}{rng.randint(0, 9)}{counter[0]:04d}"

    def thaw():
        options = [
            fid
            for fid, (_, bank, vials, used) in freezes.items()
            if used < vials and (drain_banks or bank_left[bank] > 1)
        ]
        if options and rng.random() < 0.6:
            fid = rng.choice(options)
            line, bank = freezes[fid][0], freezes[fid][1]
            freezes[fid][3] += 1
            bank_left[bank] -= 1
            vial = fid
        else:
            line, vial = rng.choice(names), None
        rid = new_id("T")
        records.append(
            {
                "id": rid,
                "kind": "thaw",
                "line": line,
                "vial": vial,
                "cells": _count(rng),
                "viability": _viability(rng, failed_counts),
            }
        )
        suspensions.append((rid, line))

    while len(records) < size:
        choice = rng.random()
        if not suspensions or choice < 0.12:
            thaw()
            continue
        if cultures and choice < 0.30:
            source, line = rng.choice(cultures)
            bank = f"{line} {rng.choice(BANK_KINDS)}"
            vials = rng.choice([1, 2, 500, rng.randint(1, 40)])
            rid = new_id("F")
            records.append({"id": rid, "kind": "freeze", "source": source, "bank": bank, "vials": vials})
            freezes[rid] = [line, bank, vials, 0]
            bank_left[bank] = bank_left.get(bank, 0) + vials
            continue
        source, line = rng.choice(suspensions[-6:] if rng.random() < 0.7 else suspensions)
        seeded = _count(rng)
        rid = new_id("C")
        records.append(
            {
                "id": rid,
                "kind": "culture",
                "source": source,
                "seeded": seeded,
                "harvested": _harvest(rng, seeded),
                "viability": _viability(rng, failed_counts),
            }
        )
        suspensions.append((rid, line))
        cultures.append((rid, line))

    if drain_banks:
        # thaw the rest of some banks so they end with no vial in stock
        for bank in sorted(bank_left):
            if rng.random() < 0.5:
                continue
            for fid, entry in freezes.items():
                while entry[1] == bank and entry[3] < entry[2] and len(records) < 400:
                    entry[3] += 1
                    bank_left[bank] -= 1
                    rid = new_id("T")
                    records.append(
                        {
                            "id": rid,
                            "kind": "thaw",
                            "line": entry[0],
                            "vial": fid,
                            "cells": _count(rng),
                            "viability": _viability(rng, failed_counts),
                        }
                    )
    return {"lines": lines, "records": records}


def has_failed_count(log):
    return any(rec.get("viability", 100.0) < 70.0 for rec in log["records"])


def has_drained_bank(log):
    report = model.build_report(log)
    return any(bank["vials_left"] == 0 for bank in report["banks"])


def doubling_is_finite(log):
    return all(math.isfinite(c["doublings"]) for c in model.build_report(log)["cultures"])
