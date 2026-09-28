"""Hand-built batches, one family per SOP rule.

Each family's standards lie exactly on a line whose slope, intercept and every
reading are exactly representable (is_counts 1024, counts a multiple of 1024 per
unit of response), so a value built to sit on a limit sits on it under any
ordinary least-squares form and any way of taking a mean. solution/seal.py checks
that in exact rational arithmetic before writing the expectations.
"""

IS = 1024.0

# analyte name -> (slope, intercept) of the exact line, response units per µg/L
LINES = {"Pb": (10.0, 100.0), "Cd": (4.0, 20.0), "As": (2.0, 8.0), "Tl": (16.0, 64.0)}


def analyte(name, mdl, loq):
    return {"name": name, "mdl": mdl, "loq": loq}


def standards(names, concs=(0.0, 10.0, 20.0, 40.0)):
    out = []
    for c in concs:
        counts = {n: (LINES[n][1] + LINES[n][0] * c) * IS for n in names}
        out.append({"conc": {n: c for n in names}, "counts": counts, "is_counts": IS})
    return out


def _counts(names, readings):
    return {n: (LINES[n][1] + LINES[n][0] * readings[n]) * IS for n in names}


def _r(names, value):
    return value if isinstance(value, dict) else {n: value for n in names}


def sample(names, rid, reading, dilution=1):
    return {"id": rid, "kind": "sample", "counts": _counts(names, _r(names, reading)), "is_counts": IS, "dilution": dilution}


def blank(names, rid, reading):
    return {"id": rid, "kind": "blank", "counts": _counts(names, _r(names, reading)), "is_counts": IS}


def ccv(names, rid, reading, true):
    return {"id": rid, "kind": "ccv", "counts": _counts(names, _r(names, reading)), "is_counts": IS, "true": _r(names, true)}


def spike(names, rid, parent, reading, added, dilution=1):
    return {
        "id": rid,
        "kind": "spike",
        "parent": parent,
        "added": _r(names, added),
        "counts": _counts(names, _r(names, reading)),
        "is_counts": IS,
        "dilution": dilution,
    }


def batch(analytes, runs, concs=(0.0, 10.0, 20.0, 40.0)):
    names = [a["name"] for a in analytes]
    return {"analytes": analytes, "standards": standards(names, concs), "runs": runs}


PB = [analyte("Pb", 1.0, 5.0)]
N = ["Pb"]


def families():
    fam = {}

    # SOP 2/3: the fitted intercept; readings far from every limit
    fam["calibration"] = [
        batch(PB, [sample(N, "W-11", 12.0), sample(N, "W-12", 30.5, 3), sample(N, "W-13", 7.25, 20)]),
        batch(
            [analyte("Cd", 0.5, 2.0), analyte("Pb", 1.0, 5.0)],
            [sample(["Cd", "Pb"], "W-21", {"Cd": 18.0, "Pb": 9.5}, 2)],
            concs=(0.0, 5.0, 25.0),
        ),
    ]

    # SOP 4: mean of every blank result wherever it sits in the run order
    fam["blank_mean"] = [
        batch(PB, [blank(N, "MB-1", 2.0), sample(N, "W-31", 13.0), blank(N, "MB-2", 3.0), sample(N, "W-32", 8.5, 2), blank(N, "MB-3", 4.0)]),
        batch(PB, [sample(N, "W-41", 20.0), blank(N, "MB-4", 1.5), blank(N, "MB-5", 2.5)]),
    ]

    # SOP 3/4: a blank below the mdl is not a result and stays out of the mean
    fam["blank_nondetects"] = [
        batch(PB, [blank(N, "MB-6", -1.5), sample(N, "W-51", 12.0), blank(N, "MB-7", 2.0), blank(N, "MB-8", 0.5), blank(N, "MB-9", 3.0)]),
        batch(PB, [blank(N, "MB-10", 1.0), blank(N, "MB-11", 0.75), blank(N, "MB-12", 3.0), sample(N, "W-52", 9.0, 5)]),
    ]

    # SOP 4 with a single result: the mean of one, even behind a non-detect blank
    fam["blank_single_result"] = [
        batch(PB, [blank(N, "MB-14", 0.5), sample(N, "W-63", 3.5, 10), blank(N, "MB-15", 3.0)]),
        batch(PB, [blank(N, "MB-16", 3.0), sample(N, "W-64", 9.0), blank(N, "MB-17", -2.0)]),
    ]

    # SOP silent (no blank result, so no mean): the shipped calculation stands
    fam["blank_no_results"] = [
        batch(PB, [sample(N, "W-61", 6.5, 2)]),
        batch(PB, [blank(N, "MB-13", -1.0), sample(N, "W-62", 0.5)]),
        batch(PB, [blank(N, "MB-18", 0.25), blank(N, "MB-19", -0.75), sample(N, "W-65", 2.25, 4)]),
        batch(PB, [sample(N, "W-66", 4.0, 3), blank(N, "MB-35", 0.5), blank(N, "MB-36", 0.75)]),
    ]

    # SOP 5: the blank level comes off before the dilution multiplies
    fam["dilution"] = [
        batch(
            PB,
            [blank(N, "MB-20", 1.5), blank(N, "MB-21", 2.5), sample(N, "W-71", 7.0), sample(N, "W-72", 7.0, 10), sample(N, "W-73", 7.0, 1000), sample(N, "W-74", 12.5, 37)],
        ),
    ]

    # SOP 5: flags judged on the corrected reading, not the amount
    fam["flag_basis"] = [
        batch(PB, [sample(N, "W-81", 0.5, 10), sample(N, "W-82", 3.0, 4), sample(N, "W-83", 6.0, 3)]),
        batch(PB, [blank(N, "MB-22", 2.0), blank(N, "MB-23", 2.0), sample(N, "W-84", 2.5, 100), sample(N, "W-85", 6.5, 2)]),
    ]

    # SOP 5: values exactly on the mdl and the loq, and an analyte with mdl = loq
    fam["flag_limits"] = [
        batch(
            PB,
            [blank(N, "MB-24", 2.0), blank(N, "MB-25", 3.0), sample(N, "W-91", 3.5, 10), sample(N, "W-92", 7.5), sample(N, "W-93", 3.25), sample(N, "W-94", 7.25, 2)],
        ),
        batch([analyte("Cd", 2.0, 2.0)], [sample(["Cd"], "W-95", 2.0, 3), sample(["Cd"], "W-96", 1.75)]),
    ]

    # SOP 3: readings below nought are never clamped
    fam["negative_readings"] = [
        batch(PB, [sample(N, "W-101", -3.0), sample(N, "W-102", -0.5, 50), blank(N, "MB-26", -1.0), sample(N, "W-103", 0.0, 2)]),
    ]

    # SOP 6: pass/fail on the recovery rounded to one decimal, inclusive at 90.0 and 110.0
    fam["ccv_limits"] = [
        batch(
            PB,
            [
                ccv(N, "CCV-1", 45.0, 50.0),
                ccv(N, "CCV-2", 88.0, 80.0),
                ccv(N, "CCV-3", 55.02, 50.0),
                ccv(N, "CCV-4", 55.03, 50.0),
                ccv(N, "CCV-5", 44.98, 50.0),
                ccv(N, "CCV-6", 44.97, 50.0),
                ccv(N, "CCV-7", 72.0, 80.0),
            ],
        ),
    ]

    # SOP 6: a sample with CCVs on both sides needs both to have passed
    fam["ccv_bracketing"] = [
        batch(
            PB,
            [
                ccv(N, "CCV-11", 50.0, 50.0),
                sample(N, "W-111", 12.0),
                ccv(N, "CCV-12", 60.0, 50.0),
                sample(N, "W-112", 12.0),
                spike(N, "W-112S", "W-112", 22.0, 10.0),
                ccv(N, "CCV-13", 51.0, 50.0),
                sample(N, "W-113", 12.0),
                ccv(N, "CCV-14", 49.0, 50.0),
            ],
        ),
    ]

    # SOP silent (no CCV on one side, or none at all): the shipped calculation stands
    fam["ccv_unbracketed"] = [
        batch(PB, [sample(N, "W-121", 12.0), ccv(N, "CCV-21", 40.0, 50.0), sample(N, "W-122", 12.0), ccv(N, "CCV-22", 50.0, 50.0), sample(N, "W-123", 12.0)]),
        batch(PB, [ccv(N, "CCV-23", 50.0, 50.0), sample(N, "W-124", 12.0), ccv(N, "CCV-24", 60.0, 50.0), sample(N, "W-125", 12.0), spike(N, "W-125S", "W-125", 22.0, 10.0)]),
        batch(PB, [sample(N, "W-126", 12.0), sample(N, "W-127", 30.0, 2)]),
        batch(PB, [sample(N, "W-128", 12.0), ccv(N, "CCV-25", 58.0, 50.0)]),
    ]

    # SOP 7: recovery of spikes whose spike and parent are both results
    fam["spike_recovery"] = [
        batch(
            PB,
            [
                sample(N, "W-131", 10.0, 2),
                spike(N, "W-131S", "W-131", 30.0, 40.0, 2),
                sample(N, "W-132", 2.0),
                spike(N, "W-132S", "W-132", 12.0, 10.0),
                spike(N, "W-131T", "W-131", 7.0, 15.0, 5),
            ],
        ),
        batch(PB, [blank(N, "MB-31", 1.5), blank(N, "MB-32", 2.5), sample(N, "W-133", 12.0, 4), spike(N, "W-133S", "W-133", 16.5, 20.0, 8)]),
    ]

    # SOP silent (spike or parent not a result): the shipped calculation stands
    fam["spike_nondetects"] = [
        batch(
            PB,
            [
                sample(N, "W-141", 0.5, 2),
                spike(N, "W-141S", "W-141", 20.0, 40.0, 2),
                sample(N, "W-142", 10.0, 2),
                spike(N, "W-142S", "W-142", 0.25, 40.0, 3),
                spike(N, "W-141T", "W-141", -0.5, 5.0, 4),
            ],
        ),
        batch(PB, [blank(N, "MB-33", 2.0), blank(N, "MB-34", 3.0), sample(N, "W-143", 3.0, 5), spike(N, "W-143S", "W-143", 13.5, 20.0, 5)]),
    ]

    # SOP 8: every list in run order, analytes in the batch's order, four analytes
    names = ["Tl", "As", "Pb", "Cd"]
    four = [analyte("Tl", 0.25, 1.0), analyte("As", 0.5, 2.0), analyte("Pb", 1.0, 5.0), analyte("Cd", 0.5, 1.5)]
    fam["report_order"] = [
        batch(
            four,
            [
                ccv(names, "Z-CCV", 50.0, 50.0),
                sample(names, "Z-9", {"Tl": 3.0, "As": 0.25, "Pb": 12.0, "Cd": 1.0}, 2),
                blank(names, "A-MB", {"Tl": 0.5, "As": 1.0, "Pb": 2.0, "Cd": 0.75}),
                blank(names, "M-MB", {"Tl": 0.75, "As": 0.5, "Pb": 3.0, "Cd": 0.25}),
                spike(names, "B-SPK", "Z-9", {"Tl": 8.0, "As": 5.0, "Pb": 20.0, "Cd": 6.0}, 10.0, 2),
                ccv(names, "A-CCV", {"Tl": 44.0, "As": 50.0, "Pb": 57.0, "Cd": 50.0}, 50.0),
                sample(names, "C-1", {"Tl": 40.0, "As": 30.0, "Pb": 0.5, "Cd": 9.0}, 25),
            ],
        ),
    ]
    return fam
