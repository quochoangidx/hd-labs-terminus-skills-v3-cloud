"""Bulletin reduction: from a parsed bulletin file to the magnitude report."""

from .distance import station_distance_km
from .network import contributes, network_magnitude
from .station import station_magnitude


def _corrections(stations):
    """Station code to magnitude correction, from the bulletin's station table."""
    return {entry["code"]: float(entry["correction"]) for entry in stations}


def _station_amplitudes(recordings):
    """Every amplitude of each station of an event, by station code.

    A site whose broadband and strong-motion sensors are processed separately
    sends one recording for each, and both are the one station's share of the
    event (rules 1.2 and 4.3).
    """
    pooled = {}
    for recording in recordings:
        pooled.setdefault(recording["code"], []).extend(recording["amplitudes"])
    return pooled


def reduce_event(event, corrections):
    """Report object for one event."""
    depth_km = float(event["depth_km"])
    pooled = _station_amplitudes(event["recordings"])
    magnitudes = {}
    rows = []
    for recording in event["recordings"]:
        code = recording["code"]
        distance_km = station_distance_km(recording["epi_km"], depth_km)
        if code not in magnitudes:
            magnitudes[code] = station_magnitude(pooled[code], distance_km, corrections[code])
        rows.append({
            "code": code,
            "distance_km": distance_km,
            "ml": magnitudes[code],
            "contributes": contributes(distance_km),
        })
    counted = []
    seen = set()
    for row in rows:
        if row["contributes"] and row["code"] not in seen:
            seen.add(row["code"])
            counted.append(row["ml"])
    return {"id": event["id"], "ml": network_magnitude(counted), "stations": rows}


def reduce_bulletin(bulletin):
    """Magnitude report for a parsed bulletin file (see the manual, section 6)."""
    corrections = _corrections(bulletin["stations"])
    return {"events": [reduce_event(event, corrections) for event in bulletin["events"]]}
