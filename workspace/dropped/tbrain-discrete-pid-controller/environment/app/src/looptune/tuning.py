"""Controller settings."""

from dataclasses import dataclass, fields, replace


@dataclass(frozen=True)
class Tuning:
    """One loop's settings. Times are in seconds."""

    gain: float
    integral_time: float = 0.0
    derivative_time: float = 0.0
    filter_divisor: float = 10.0
    tracking_time: float = 0.0
    setpoint_weight: float = 1.0
    period: float = 0.1
    low: float = -1.0
    high: float = 1.0
    slew: float = 0.0

    def with_changes(self, **changes):
        known = {f.name for f in fields(self)}
        unknown = sorted(set(changes) - known)
        if unknown:
            raise TypeError("unknown setting(s): " + ", ".join(unknown))
        if "period" in changes:
            raise TypeError("the period is fixed when the controller is built")
        return replace(self, **{k: float(v) for k, v in changes.items()})
