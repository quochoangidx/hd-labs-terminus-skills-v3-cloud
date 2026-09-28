"""Bulletin reduction: from a parsed bulletin file to the magnitude report."""

from .distance import station_distance_km
from .network import contributes, network_magnitude
from .station import mean_magnitude, reading_magnitudes


def _corrections(stations):
    """Station code to magnitude correction, from the bulletin's station table."""
    return {entry["code"]: float(entry["correction"]) for entry in stations}


def reduce_event(event, corrections):
    """Report object for one event."""
    depth_km = float(event["depth_km"])
    rows = []
    # A station may send one recording per sensor (rule 1.2); its magnitude is
    # the mean over the channel magnitudes of all of its readings (rule 4.3),
    # and it contributes once to the network magnitude (rules 5.1, 5.2).
    pooled = {}
    order = []
    for recording in event["recordings"]:
        code = recording["code"]
        distance_km = station_distance_km(recording["epi_km"], depth_km)
        if code not in pooled:
            pooled[code] = []
            order.append(code)
        pooled[code].extend(
            reading_magnitudes(recording["amplitudes"], distance_km, corrections[code])
        )
        rows.append({
            "code": code,
            "distance_km": distance_km,
            "ml": None,
            "contributes": contributes(distance_km),
        })
    magnitudes = {code: mean_magnitude(values) for code, values in pooled.items()}
    for row in rows:
        row["ml"] = magnitudes[row["code"]]
    counted = [
        magnitudes[code]
        for code in order
        if any(row["contributes"] for row in rows if row["code"] == code)
        and magnitudes[code] is not None
    ]
    return {"id": event["id"], "ml": network_magnitude(counted), "stations": rows}


def reduce_bulletin(bulletin):
    """Magnitude report for a parsed bulletin file (see the manual, section 6)."""
    corrections = _corrections(bulletin["stations"])
    return {"events": [reduce_event(event, corrections) for event in bulletin["events"]]}
