"""Bulletin reduction: from a parsed bulletin file to the magnitude report."""

from .distance import station_distance_km
from .network import contributes, network_magnitude
from .station import station_magnitude


def _corrections(stations):
    """Station code to magnitude correction, from the bulletin's station table."""
    return {entry["code"]: float(entry["correction"]) for entry in stations}


def _stations_of_event(event, depth_km):
    """The event's stations, in first-recording order.

    A station sends one recording for each sensor processed separately, and both
    give the same epicentral distance (manual, rule 1.2), so a station has one
    distance and one set of channels for the event.
    """
    stations = {}
    for recording in event["recordings"]:
        code = recording["code"]
        entry = stations.get(code)
        if entry is None:
            entry = {
                "distance_km": station_distance_km(recording["epi_km"], depth_km),
                "amplitudes": [],
            }
            stations[code] = entry
        entry["amplitudes"].extend(recording["amplitudes"])
    return stations


def reduce_event(event, corrections):
    """Report object for one event."""
    depth_km = float(event["depth_km"])
    stations = _stations_of_event(event, depth_km)
    for code, entry in stations.items():
        entry["ml"] = station_magnitude(
            entry["amplitudes"], entry["distance_km"], corrections[code]
        )
        entry["contributes"] = contributes(entry["distance_km"])

    rows = []
    for recording in event["recordings"]:
        entry = stations[recording["code"]]
        rows.append({
            "code": recording["code"],
            "distance_km": entry["distance_km"],
            "ml": entry["ml"],
            "contributes": entry["contributes"],
        })

    counted = [entry["ml"] for entry in stations.values() if entry["contributes"]]
    return {"id": event["id"], "ml": network_magnitude(counted), "stations": rows}


def reduce_bulletin(bulletin):
    """Magnitude report for a parsed bulletin file (see the manual, section 6)."""
    corrections = _corrections(bulletin["stations"])
    return {"events": [reduce_event(event, corrections) for event in bulletin["events"]]}
