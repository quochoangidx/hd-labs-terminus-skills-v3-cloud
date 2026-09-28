"""Bulletin reduction: from a parsed bulletin file to the magnitude report."""

from .distance import station_distance_km
from .network import contributes, network_magnitude
from .station import station_magnitude


def _corrections(stations):
    """Station code to magnitude correction, from the bulletin's station table."""
    return {entry["code"]: float(entry["correction"]) for entry in stations}


def reduce_event(event, corrections):
    """Report object for one event."""
    depth_km = float(event["depth_km"])
    rows = []
    for recording in event["recordings"]:
        code = recording["code"]
        distance_km = station_distance_km(recording["epi_km"], depth_km)
        rows.append({
            "code": code,
            "distance_km": distance_km,
            "ml": station_magnitude(recording["amplitudes"], distance_km, corrections[code]),
            "contributes": contributes(distance_km),
        })
    counted = [row["ml"] for row in rows if row["contributes"]]
    return {"id": event["id"], "ml": network_magnitude(counted), "stations": rows}


def reduce_bulletin(bulletin):
    """Magnitude report for a parsed bulletin file (see the manual, section 6)."""
    corrections = _corrections(bulletin["stations"])
    return {"events": [reduce_event(event, corrections) for event in bulletin["events"]]}
