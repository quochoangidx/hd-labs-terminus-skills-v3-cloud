"""Round, write and assemble the batch report."""

from fractions import Fraction

from .batch import load
from .results import ABOVE, BELOW, sample_result

UNITS = {"g": "CFU/g", "mL": "CFU/mL"}
SIGNS = {BELOW: "<", ABOVE: ">"}


def decade(value):
    """The power of ten of a positive exact value's first significant digit."""
    power = 0
    while value >= 10 ** (power + 1):
        power += 1
    while value < Fraction(10) ** power:
        power -= 1
    return power


def two_figures(value):
    """(digits, power): value is about digits / 10 * 10 ** power, digits from 10 to 99."""
    power = decade(value)
    digits = round(value / Fraction(10) ** (power - 1))
    if digits == 100:
        digits, power = 10, power + 1
    return digits, power


def written(value):
    digits, power = two_figures(value)
    return f"{digits // 10}.{digits % 10}E{power}"


def build_report(batch):
    name, samples = load(batch)
    rows = []
    for sample in samples:
        kind, value = sample_result(sample)
        rows.append({
            "id": sample.id,
            "unit": UNITS[sample.unit],
            "kind": kind,
            "apc": SIGNS.get(kind, "") + written(value),
        })
    return {"batch": name, "samples": rows}
