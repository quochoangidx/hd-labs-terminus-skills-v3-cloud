"""Assemble the batch report."""

import math

from . import qc
from .bench import decode
from .samples import results
from .seed import seed_factor


def reported(value):
    """A value as it goes on the report."""
    return round(value, 2 - math.floor(math.log10(abs(value)))) if value else 0.0


def reduce_batch(batch):
    """Reduce one batch to its report (a JSON-ready dict)."""
    batch = decode(batch)
    factor = seed_factor(batch["seed_controls"])
    blank = qc.blank_depletion(batch["blanks"])
    check = qc.check_value(batch["check"], factor)
    found = results(batch["samples"], factor)
    return {
        "batch": batch["batch"],
        "seed_factor": factor,
        "blank_depletion": blank,
        "check_value": reported(check),
        "qualifiers": qc.qualifiers(blank, check),
        "samples": [
            {"id": s["id"], "relation": found[s["id"]][0], "value": reported(found[s["id"]][1])}
            for s in batch["samples"]
        ],
        "duplicates": qc.duplicates(batch["samples"], found),
    }
