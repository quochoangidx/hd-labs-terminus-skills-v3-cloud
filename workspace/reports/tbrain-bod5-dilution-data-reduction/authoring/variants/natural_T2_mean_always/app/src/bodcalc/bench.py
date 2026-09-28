"""Decoding of the bench sheet: every reading and volume becomes a float."""

BOTTLE_FIELDS = ("sample_ml", "seed_ml", "do_initial", "do_final")


def _bottle(raw, fields):
    bottle = dict(raw)
    for name in fields:
        if name in bottle:
            bottle[name] = float(bottle[name])
    return bottle


def decode(raw):
    """Return a copy of a batch with its numeric fields as floats."""
    batch = dict(raw)
    batch["seed_controls"] = [_bottle(c, BOTTLE_FIELDS) for c in raw["seed_controls"]]
    batch["blanks"] = [_bottle(b, BOTTLE_FIELDS) for b in raw["blanks"]]
    check = dict(raw["check"])
    check["bottles"] = [_bottle(b, BOTTLE_FIELDS) for b in raw["check"]["bottles"]]
    batch["check"] = check
    samples = []
    for raw_sample in raw["samples"]:
        sample = dict(raw_sample)
        sample.setdefault("duplicate_of", None)
        sample["bottles"] = [_bottle(b, BOTTLE_FIELDS) for b in raw_sample["bottles"]]
        samples.append(sample)
    batch["samples"] = samples
    return batch
