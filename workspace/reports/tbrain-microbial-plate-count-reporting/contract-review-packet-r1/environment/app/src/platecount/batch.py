"""Decode a plate-reading batch file into samples and dilutions."""

from dataclasses import dataclass
from fractions import Fraction


@dataclass
class Dilution:
    step: int
    volume: Fraction
    plates: list  # one reading per plate; None when marked too numerous to count


@dataclass
class Sample:
    id: str
    unit: str
    dilutions: list


def volume_of(value):
    """Plated volume in millilitres, kept exact (1.0 -> 1, 0.1 -> 1/10)."""
    return Fraction(str(value))


def reading_of(value):
    return None if value is None else int(value)


def load(batch):
    """Return the batch name and its samples, in file order."""
    samples = []
    for raw in batch["samples"]:
        dilutions = [
            Dilution(int(d["step"]), volume_of(d["volume"]), [reading_of(v) for v in d["plates"]])
            for d in raw["dilutions"]
        ]
        samples.append(Sample(str(raw["id"]), str(raw["unit"]), dilutions))
    return str(batch["batch"]), samples
