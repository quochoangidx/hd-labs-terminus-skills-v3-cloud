"""Stage record to discharge: shifts, rating, daily means, volumes and peaks."""

from gaugeflow.daily import daily_mean, daily_values
from gaugeflow.peaks import peaks
from gaugeflow.pieces import joined_pieces, span_totals
from gaugeflow.rating import RatingCurve, Segment
from gaugeflow.record import Reading, discharge_series
from gaugeflow.shifts import shift_at
from gaugeflow.volume import volume

__all__ = [
    "RatingCurve",
    "Reading",
    "Segment",
    "daily_mean",
    "daily_values",
    "discharge_series",
    "joined_pieces",
    "peaks",
    "shift_at",
    "span_totals",
    "volume",
]
