"""Reading a job directory: the stability record, the lot list and the logger exports."""

import csv
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

_EPOCH = datetime(2000, 1, 1)

CHAIN_LIMIT_MINUTES = 2880  # 2.9: a longer handover breaks the chain


@dataclass(frozen=True)
class Reading:
    minute: int  # minutes since 2000-01-01T00:00 UTC
    temp: float  # degrees Celsius


@dataclass(frozen=True)
class Band:
    name: str
    lower: float
    upper: float
    allowance_h: int


@dataclass
class Stability:
    product: str
    low: float
    high: float
    freeze_point: float
    ratio: float
    bands: list


@dataclass
class Leg:
    name: str
    readings: list


@dataclass
class Lot:
    lot: str
    legs: list
    prior_minutes: dict = field(default_factory=dict)

    def readings(self):
        """Every reading of the lot, leg after leg in travel order."""
        return [reading for leg in self.legs for reading in leg.readings]

    def handovers(self):
        """Minutes from the last reading of each leg to the first reading of the next (2.9)."""
        return [
            later.readings[0].minute - earlier.readings[-1].minute
            for earlier, later in zip(self.legs, self.legs[1:])
        ]

    def chained(self):
        """Whether no handover of the lot is longer than CHAIN_LIMIT_MINUTES (2.9)."""
        return all(handover <= CHAIN_LIMIT_MINUTES for handover in self.handovers())


def stamp_minutes(stamp):
    moment = datetime.strptime(stamp.strip(), "%Y-%m-%dT%H:%M")
    return int((moment - _EPOCH).total_seconds()) // 60


def read_export(path):
    with open(path, newline="", encoding="utf-8") as handle:
        return [Reading(stamp_minutes(row["timestamp"]), float(row["temp_c"])) for row in csv.DictReader(handle)]


def read_stability(path):
    record = json.loads(Path(path).read_text(encoding="utf-8"))
    low, high = record["labelled_range_c"]
    bands = [
        Band(entry["band"], float(entry["lower_c"]), float(entry["upper_c"]), int(entry["allowance_h"]))
        for entry in record["bands"]
    ]
    return Stability(
        product=record["product"],
        low=float(low),
        high=float(high),
        freeze_point=float(record["freeze_point_c"]),
        ratio=float(record["activation_ratio_k"]),
        bands=bands,
    )


def load_job(job_dir):
    """The stability record and the lots of a job directory, legs read once each."""
    job = Path(job_dir)
    stability = read_stability(job / "stability.json")
    exports = {}
    lots = []
    for entry in json.loads((job / "lots.json").read_text(encoding="utf-8")):
        legs = []
        for name in entry["legs"]:
            if name not in exports:
                exports[name] = Leg(name, read_export(job / "loggers" / f"{name}.csv"))
            legs.append(exports[name])
        prior = {band: int(minutes) for band, minutes in entry.get("prior_minutes", {}).items()}
        lots.append(Lot(entry["lot"], legs, prior))
    return stability, lots
