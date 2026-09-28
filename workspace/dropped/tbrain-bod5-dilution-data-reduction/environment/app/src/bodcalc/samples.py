"""Sample results: a measured value, or a bound when no bottle can be read."""

from .bottles import MIN_DEPLETION, bottle_bod, is_spent, is_usable, sample_fraction


def _mean(values):
    values = list(values)
    return sum(values) / len(values)


def sample_result(sample, seed_factor):
    """Return (relation, value) for one sample; value is not rounded."""
    bottles = sample["bottles"]
    usable = [b for b in bottles if is_usable(b)]
    if usable:
        return "=", _mean(bottle_bod(b, seed_factor) for b in usable)
    if all(is_spent(b) for b in bottles):
        least = min(bottles, key=lambda b: b["sample_ml"])
        return ">", bottle_bod(least, seed_factor)
    limiting = min(bottles, key=lambda b: b["sample_ml"])
    return "<", MIN_DEPLETION / sample_fraction(limiting)


def results(samples, seed_factor):
    """Map sample id to its (relation, value)."""
    return {s["id"]: sample_result(s, seed_factor) for s in samples}
