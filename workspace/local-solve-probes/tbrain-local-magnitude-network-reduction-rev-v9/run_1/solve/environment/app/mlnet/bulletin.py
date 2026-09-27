"""Bulletin reduction: from a parsed bulletin file to the magnitude report."""

from .distance import station_distance_km
from .network import contributes, network_magnitude
from .station import station_magnitude


def _corrections(stations):
    """Station code to magnitude correction, from the bulletin's station table."""
    return {entry["code"]: float(entry["correction"]) for entry in stations}


def _stations_of(event):
    """The event's stations, in the order their first recording appears.

    A station whose broadband and strong-motion sensors are processed separately
    sends one recording for each (rule 1.2); both belong to the one station, so
    their readings are pooled into the one station magnitude (rule 4.3).  The
    two recordings give the same epicentral distance.
    """
    order = []
    pooled = {}
    depth_km = float(event["depth_km"])
    for recording in event["recordings"]:
        code = recording["code"]
        if code not in pooled:
            order.append(code)
            pooled[code] = {
                "distance_km": station_distance_km(recording["epi_km"], depth_km),
                "amplitudes": [],
            }
        pooled[code]["amplitudes"].extend(recording["amplitudes"])
    return order, pooled


def reduce_event(event, corrections):
    """Report object for one event (manual, section 6)."""
    order, pooled = _stations_of(event)
    reduced = {}
    for code in order:
        distance_km = pooled[code]["distance_km"]
        reduced[code] = {
            "distance_km": distance_km,
            "ml": station_magnitude(pooled[code]["amplitudes"], distance_km, corrections[code]),
            "contributes": contributes(distance_km),
        }
    rows = []
    for recording in event["recordings"]:
        station = reduced[recording["code"]]
        rows.append({
            "code": recording["code"],
            "distance_km": station["distance_km"],
            "ml": station["ml"],
            "contributes": station["contributes"],
        })
    counted = [reduced[code]["ml"] for code in order if reduced[code]["contributes"]]
    return {"id": event["id"], "ml": network_magnitude(counted), "stations": rows}


def reduce_bulletin(bulletin):
    """Magnitude report for a parsed bulletin file (see the manual, section 6)."""
    corrections = _corrections(bulletin["stations"])
    return {"events": [reduce_event(event, corrections) for event in bulletin["events"]]}
