"""Expected magnitude reports worked out from NPM-4, independently of the package.

This module never imports or runs `mlnet`. Every rule NPM-4 states is written
here from its own sentences (rule numbers in the comments). NPM-4 gives no
distance correction for a distance its table does not reach (below 10 km or
beyond 600 km; NPM-4 3.2 says so); the instruction keeps the calculation the shipped code makes for
that value, fed with the distance NPM-4 defines, so that one branch mirrors the
shipped expression and says so ("Shipped step").
"""

import math

# NPM-4 3.2: the network's 2019 calibration, (distance km, -log A0)
TABLE = (
    (10.0, 1.700), (20.0, 2.060), (30.0, 2.290), (50.0, 2.580),
    (75.0, 2.820), (100.0, 3.000), (150.0, 3.300), (200.0, 3.530),
    (300.0, 3.900), (400.0, 4.220), (500.0, 4.510), (600.0, 4.790),
)
NEAREST_KM = TABLE[0][0]
FARTHEST_KM = TABLE[-1][0]
MAGNIFICATION = 2080.0  # NPM-4 2.2


def record_amplitude_mm(amplitude_nm):
    # NPM-4 2.2: half the peak-to-peak value, in mm on a record of magnification 2080
    return amplitude_nm / 2.0 * MAGNIFICATION * 1.0e-6


def is_reading(amplitude):
    # NPM-4 2.3: at least three times the noise of its channel
    return amplitude["amplitude_nm"] >= 3.0 * amplitude["noise_nm"]


def distance_km(epi_km, depth_km):
    # NPM-4 3.1: hypocentral distance
    return math.sqrt(epi_km * epi_km + depth_km * depth_km)


def in_table(distance):
    # NPM-4 3.2 / 5.1: the table runs from 10 km to 600 km, both ends included
    return NEAREST_KM <= distance <= FARTHEST_KM


def _shipped_off_table_correction(distance):
    # Shipped step (mlnet/attenuation.py minus_log_a0): NPM-4 gives no correction
    # outside its table, so the shipped calculation stays: the end segment
    # (10-20 km below the table, 500-600 km beyond it) interpolated on log10 of
    # distance and carried past its end. It is fed with the hypocentral distance.
    if distance < NEAREST_KM:
        (d0, v0), (d1, v1) = TABLE[0], TABLE[1]
    else:
        (d0, v0), (d1, v1) = TABLE[-2], TABLE[-1]
    x, x0, x1 = math.log10(distance), math.log10(d0), math.log10(d1)
    return v0 + (v1 - v0) * (x - x0) / (x1 - x0)


def correction(distance):
    """-log A0 at a hypocentral distance."""
    if not in_table(distance):
        return _shipped_off_table_correction(distance)
    for (d0, v0), (d1, v1) in zip(TABLE, TABLE[1:]):
        if d0 <= distance <= d1:
            # NPM-4 3.3: listed value at a listed distance, linear in distance between
            return v0 + (v1 - v0) * (distance - d0) / (d1 - d0)
    raise AssertionError("unreachable")


def station_magnitude(amplitudes, distance, station_correction):
    # NPM-4 4.1: each reading gives log10(record amplitude) + correction + station correction
    # NPM-4 4.2: the station correction is added as it stands
    # NPM-4 4.3: the station magnitude is the mean of its readings' channel magnitudes
    mags = [
        math.log10(record_amplitude_mm(a["amplitude_nm"])) + correction(distance) + station_correction
        for a in amplitudes if is_reading(a)
    ]
    return sum(mags) / len(mags)


def network_magnitude(values):
    # NPM-4 5.3: fewer than three contributors -> no network magnitude
    if len(values) < 3:
        return None
    # NPM-4 5.2: median; mean of the two middle ones for an even number
    ordered = sorted(values)
    n = len(ordered)
    if n % 2:
        return ordered[n // 2]
    return (ordered[n // 2 - 1] + ordered[n // 2]) / 2.0


def reduce_bulletin(bulletin):
    """Expected report (NPM-4 section 6) for a bulletin inside section 1."""
    corrections = {s["code"]: float(s["correction"]) for s in bulletin["stations"]}
    events = []
    for event in bulletin["events"]:
        depth = float(event["depth_km"])
        # NPM-4 1.2 / 4.3: a station's readings are those of all its recordings in the event
        amplitudes = {}
        for rec in event["recordings"]:
            amplitudes.setdefault(rec["code"], []).extend(rec["amplitudes"])
        stations = {}
        for code, amps in amplitudes.items():
            epi = next(float(r["epi_km"]) for r in event["recordings"] if r["code"] == code)
            d = distance_km(epi, depth)
            stations[code] = (d, station_magnitude(amps, d, corrections[code]), in_table(d))
        rows = [{"code": rec["code"], "distance_km": stations[rec["code"]][0],
                 "ml": stations[rec["code"]][1], "contributes": stations[rec["code"]][2]}  # NPM-4 5.1, 6.1
                for rec in event["recordings"]]
        # NPM-4 5.2 / 5.3 speak of contributing stations: each station once
        ml = network_magnitude([m for (_, m, c) in stations.values() if c])
        events.append({"id": event["id"], "ml": ml, "stations": rows})
    return {"events": events}


if __name__ == "__main__":
    import json
    import sys

    with open(sys.argv[1], encoding="utf-8") as handle:
        json.dump(reduce_bulletin(json.load(handle)), sys.stdout)
    sys.stdout.write("\n")
