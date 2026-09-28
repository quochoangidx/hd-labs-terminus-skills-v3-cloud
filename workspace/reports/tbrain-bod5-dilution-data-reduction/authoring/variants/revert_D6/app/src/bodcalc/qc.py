"""Batch quality checks: dilution-water blanks, the GGA check, duplicates."""

from .bottles import bottle_bod, depletion, is_usable

BLANK_LIMIT = 0.20
CHECK_LOW = 175.0
CHECK_HIGH = 225.0
RPD_LIMIT = 25.0


def blank_depletion(blanks):
    """Depletion that stands for the batch's dilution water."""
    return sum(depletion(b) for b in blanks) / len(blanks)


def check_value(check, seed_factor):
    """BOD of the glucose-glutamic acid check standard."""
    usable = [b for b in check["bottles"] if is_usable(b)]
    return sum(bottle_bod(b, seed_factor) for b in usable) / len(usable)


def qualifiers(blank, check):
    """Batch qualifiers as one string."""
    out = ""
    if blank > BLANK_LIMIT:
        out += "B"
    if check < CHECK_LOW or check > CHECK_HIGH:
        out += "G"
    return out


def duplicates(samples, found):
    """One entry per duplicate sample, in batch order."""
    out = []
    for sample in samples:
        parent = sample.get("duplicate_of")
        if parent is None:
            continue
        (rel_mine, mine), (rel_theirs, theirs) = found[sample["id"]], found[parent]
        if rel_mine == "=" and rel_theirs == "=":
            rpd = abs(mine - theirs) / ((mine + theirs) / 2.0) * 100.0
        else:
            rpd = abs(mine - theirs) / theirs * 100.0
        out.append({"id": sample["id"], "of": parent, "rpd": rpd, "pass": rpd <= RPD_LIMIT})
    return out
