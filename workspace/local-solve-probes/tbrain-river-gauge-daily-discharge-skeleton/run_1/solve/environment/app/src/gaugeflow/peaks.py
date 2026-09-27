"""Peaks over a threshold."""


def peaks(series, threshold, separation):
    """One ``(time, value)`` peak per event, in time order."""
    events = []
    current = None
    in_run = False
    for t, v in series:
        if v > threshold:
            if not in_run:
                if current is None or not (t - current["end"] < separation):
                    if current is not None:
                        events.append((current["time"], current["value"]))
                    current = {"start": t, "end": t, "time": t, "value": v}
                in_run = True
            if v > current["value"]:
                current["time"] = t
                current["value"] = v
            current["end"] = t
        else:
            in_run = False
    if current is not None:
        events.append((current["time"], current["value"]))
    return events
