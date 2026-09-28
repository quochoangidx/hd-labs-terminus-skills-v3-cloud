"""Stage-discharge rating."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Segment:
    lower: float
    coefficient: float
    offset: float
    exponent: float


class RatingCurve:
    """A rating made of segments in increasing order of lower stage."""

    def __init__(self, segments):
        self.segments = list(segments)

    def segment_for(self, stage):
        segment = self.segments[0]
        for candidate in self.segments[1:]:
            if candidate.lower <= stage:
                segment = candidate
            else:
                break
        return segment

    def discharge(self, stage):
        segment = self.segment_for(stage)
        if stage < segment.lower:
            return 0.0
        depth = stage - segment.offset
        if depth > 0:
            return segment.coefficient * depth ** segment.exponent
        if segment.exponent > 0:
            return 0.0
        if depth < 0:
            return 0.0
        return segment.coefficient * depth ** segment.exponent
