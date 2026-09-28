"""Readings and the discharge series built from them."""

from dataclasses import dataclass

from gaugeflow.shifts import shift_at


@dataclass(frozen=True)
class Reading:
    time: int
    stage: float


def discharge_series(record, table, curve):
    """One ``(time, discharge)`` point per reading, in record order."""
    return [(r.time, curve.discharge(r.stage + shift_at(table, r.time))) for r in record]
