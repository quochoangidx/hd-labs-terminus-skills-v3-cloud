"""Bulletin generator for the sealed cases (authoring only; never run at grading).

Every bulletin keeps within NPM-4 section 1. Families are named for what they
exercise. Only the `readings` family carries an amplitude below three times its
noise, only the `off_table` family a hypocentral distance outside 10-600 km, and
only the `shared_station` family a station with two recordings in one event;
every other family is free of all three, and `trap_inputs()` says which a
bulletin carries.
"""

import math
import random

SEED = 20260926
NODES = (10, 20, 30, 50, 75, 100, 150, 200, 300, 400, 500, 600)
INNER_NODES = NODES[1:-1]  # section 1 keeps every station a metre clear of 10 and 600 km
_CODE_CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
_SENSORS = (("HHE", "HHN"), ("HNE", "HNN"), ("BHE", "BHN"), ("EH1", "EH2"))
EDGE_GAP = 1e-3  # section 1 keeps hypocentral distances more than this from 10 and 600 km


def _hypo(epi, depth):
    return math.sqrt(epi * epi + depth * depth)


def trap_inputs(bulletin):
    """Set of trap classes a bulletin carries: 'sub_noise', 'off_table', 'shared_station'."""
    found = set()
    for event in bulletin["events"]:
        codes = [rec["code"] for rec in event["recordings"]]
        if len(set(codes)) != len(codes):
            found.add("shared_station")
        for rec in event["recordings"]:
            r = _hypo(rec["epi_km"], event["depth_km"])
            if not (10.0 <= r <= 600.0):
                found.add("off_table")
            if any(a["amplitude_nm"] < 3 * a["noise_nm"] for a in rec["amplitudes"]):
                found.add("sub_noise")
    return found


def keeps_the_limits(b):
    """Executable form of NPM-4 section 1."""
    st = b["stations"]
    assert 1 <= len(st) <= 200
    codes = [s["code"] for s in st]
    assert len(set(codes)) == len(codes)
    for s in st:
        assert 1 <= len(s["code"]) <= 5 and all(c in _CODE_CHARS for c in s["code"])
        assert -1.0 <= s["correction"] <= 1.0
    ev = b["events"]
    assert 1 <= len(ev) <= 50
    assert len({e["id"] for e in ev}) == len(ev)
    for e in ev:
        assert 1 <= len(e["id"]) <= 20
        assert 0 <= e["depth_km"] <= 60
        assert 1 <= len(e["recordings"]) <= 40
        per_station = {}
        for rec in e["recordings"]:
            assert rec["code"] in codes
            per_station.setdefault(rec["code"], []).append(rec)
            assert 0 <= rec["epi_km"] <= 1000
            assert _hypo(rec["epi_km"], e["depth_km"]) >= 1.0
            assert all(abs(_hypo(rec["epi_km"], e["depth_km"]) - end) > 0.001 for end in (10.0, 600.0))
            amps = rec["amplitudes"]
            assert 1 <= len(amps) <= 2
            for a in amps:
                assert len(a["channel"]) == 3
                assert 0.1 <= a["amplitude_nm"] <= 1e8
                assert 0.01 <= a["noise_nm"] <= 1e7
                assert abs(a["amplitude_nm"] - 3 * a["noise_nm"]) > 0.003 * a["noise_nm"]
            assert any(a["amplitude_nm"] >= 3 * a["noise_nm"] for a in amps)
        for recs in per_station.values():
            assert len(recs) <= 2 and len({r["epi_km"] for r in recs}) == 1
            chans = [a["channel"] for r in recs for a in r["amplitudes"]]
            assert len(set(chans)) == len(chans)
    return True


class Gen:
    def __init__(self, seed):
        self.rng = random.Random(seed)
        self.n_event = 0

    def code(self, used):
        while True:
            c = "".join(self.rng.choice(_CODE_CHARS) for _ in range(self.rng.randint(1, 5)))
            if c not in used:
                used.add(c)
                return c

    def station_table(self, n):
        used = set()
        table = []
        for _ in range(n):
            corr = self.rng.choice([0.0, round(self.rng.uniform(-1, 1), 2), -1.0, 1.0]
                                   if self.rng.random() < 0.15 else [round(self.rng.uniform(-1, 1), 2)])
            table.append({"code": self.code(used), "correction": corr})
        return table

    def event_id(self):
        self.n_event += 1
        return "ev%06d" % self.n_event

    def in_table_epi(self, depth):
        """An epicentral distance whose hypocentral distance is inside the table, clear of the ends."""
        while True:
            r = math.exp(self.rng.uniform(math.log(10.0), math.log(600.0)))
            if r * r - depth * depth <= 0:
                continue
            epi = round(math.sqrt(r * r - depth * depth), 1)
            h = _hypo(epi, depth)
            if 10.0 + EDGE_GAP <= h <= 600.0 - EDGE_GAP and epi <= 1000:
                return epi

    def reading(self, channel, lo_ratio=4.0):
        amp = round(math.exp(self.rng.uniform(math.log(1.0), math.log(1e7))), 1)
        noise = round(amp / math.exp(self.rng.uniform(math.log(lo_ratio), math.log(2000.0))), 2)
        noise = min(max(noise, 0.01), 1e7)
        if amp < lo_ratio * noise:
            noise = max(0.01, round(amp / (lo_ratio + 1), 2))
        return {"channel": channel, "amplitude_nm": amp, "noise_nm": noise}

    def recording(self, code, epi, n_amps=None, sensor=None):
        n = n_amps or self.rng.randint(1, 2)
        pair = sensor or self.rng.choice(_SENSORS)
        chans = self.rng.sample(pair, n)
        return {"code": code, "epi_km": epi, "amplitudes": [self.reading(c) for c in chans]}

    def event(self, table, n_rec, depth=None):
        depth = round(self.rng.uniform(0, 60), 1) if depth is None else depth
        picks = self.rng.sample(table, n_rec)
        return {"id": self.event_id(), "depth_km": depth,
                "recordings": [self.recording(s["code"], self.in_table_epi(depth)) for s in picks]}


def _with_outlier(g, event):
    """Make one recording read far above the rest (a large amplitude, same noise)."""
    rec = g.rng.choice(event["recordings"])
    for a in rec["amplitudes"]:
        a["amplitude_nm"] = min(1e8, round(a["amplitude_nm"] * 300, 1))
    return event


def family(name, seed=SEED):
    """One bulletin of the named family."""
    g = Gen((seed * 1000003 + sum(map(ord, name))) & 0xFFFFFFFF)
    rng = g.rng
    table = g.station_table(22 if name in ("median", "median_even") else 14 if name.startswith("generated") else rng.randint(8, 12))
    events = []
    if name == "plain_nodes":
        # depth 0, epicentre on a listed distance, one reading: isolates 2.2 and 4.2
        for _ in range(4):
            picks = rng.sample(table, rng.randint(3, 7))
            events.append({"id": g.event_id(), "depth_km": 0, "recordings": [
                {"code": s["code"], "epi_km": float(rng.choice(INNER_NODES)), "amplitudes": [g.reading("HHE")]}
                for s in picks]})
    elif name == "hypocentral":
        for _ in range(6):
            depth = round(rng.uniform(5, 60), 1)
            picks = rng.sample(table, rng.randint(3, 6))
            recs = []
            for s in picks:
                epi = round(rng.uniform(0, 30), 1) if rng.random() < 0.5 else g.in_table_epi(depth)
                if not 10 + EDGE_GAP <= _hypo(epi, depth) <= 600 - EDGE_GAP:
                    epi = g.in_table_epi(depth)
                recs.append(g.recording(s["code"], epi, 1))
            events.append({"id": g.event_id(), "depth_km": depth, "recordings": recs})
    elif name == "interpolation":
        for _ in range(6):
            picks = rng.sample(table, rng.randint(3, 6))
            recs = []
            for s in picks:
                i = rng.randrange(len(NODES) - 1)
                epi = round(rng.uniform(NODES[i] + 0.5, NODES[i + 1] - 0.5), 1)
                recs.append(g.recording(s["code"], epi, 1))
            events.append({"id": g.event_id(), "depth_km": 0, "recordings": recs})
    elif name == "station_mean":
        for _ in range(6):
            e = g.event(table, rng.randint(3, 6))
            for rec in e["recordings"]:
                rec["amplitudes"] = [g.reading(c) for c in rng.choice(_SENSORS)]
            events.append(e)
    elif name == "median":
        # odd numbers of contributors, one station reading well off the others
        for n in (3, 5, 11):
            events.append(_with_outlier(g, g.event(table, n)))
    elif name == "median_even":
        for n in (4, 6, 12):
            events.append(_with_outlier(g, g.event(table, n)))
    elif name == "min_three":
        for n in (1, 2, 1, 2):
            events.append(g.event(table, n))
    elif name == "three":
        for _ in range(4):
            events.append(g.event(table, 3))
    elif name == "correction":
        # depth 0, epicentre on a listed distance, one reading; corrections across the range
        fixed = [-1.0, -0.5, 0.0, 0.37, 1.0]
        for i, st in enumerate(table):
            st["correction"] = fixed[i % len(fixed)]
        for _ in range(4):
            picks = rng.sample(table, 5)
            events.append({"id": g.event_id(), "depth_km": 0, "recordings": [
                {"code": s["code"], "epi_km": float(rng.choice(INNER_NODES)), "amplitudes": [g.reading("HHE")]}
                for s in picks]})
    elif name == "order":
        # ids not in sorted order, recordings in no particular order
        for _ in range(4):
            e = g.event(table, rng.randint(3, 8))
            e["id"] = "".join(rng.choice("zyxwvu9876543210") for _ in range(rng.randint(1, 20)))
            events.append(e)
        rng.shuffle(table)
    elif name == "readings":
        # trap T1 inputs: an amplitude under three times its noise beside a reading,
        # larger and smaller than it; amplitudes just clear of three times their noise (1.51/0.5, 300.5/100)
        for k in range(5):
            e = g.event(table, rng.randint(3, 6))
            for j, rec in enumerate(e["recordings"]):
                c0, c1 = rng.choice(_SENSORS)
                good = g.reading(c0)
                if k == 0 and j == 0:
                    rec["amplitudes"] = [{"channel": c0, "amplitude_nm": 1.51, "noise_nm": 0.5},
                                         {"channel": c1, "amplitude_nm": 1.4, "noise_nm": 0.5}]
                elif k == 0 and j == 1:
                    rec["amplitudes"] = [{"channel": c0, "amplitude_nm": 300.5, "noise_nm": 100.0},
                                         {"channel": c1, "amplitude_nm": 2990.0, "noise_nm": 1000.0}]
                elif rng.random() < 0.7:
                    a = round(good["amplitude_nm"] * rng.choice([0.3, 0.7, 1.5, 4.0]), 1)
                    a = min(max(a, 0.1), 1e8)
                    noise = min(max(round(a / rng.uniform(1.05, 2.9), 2), 0.01), 1e7)
                    bad = {"channel": c1, "amplitude_nm": a, "noise_nm": noise}
                    rec["amplitudes"] = [good, bad] if rng.random() < 0.5 else [bad, good]
                else:
                    rec["amplitudes"] = [good, g.reading(c1)]
            events.append(e)
    elif name == "off_table":
        # trap T2 inputs: stations the table does not reach; each event keeps >= 3 contributors
        for k in range(6):
            depth = [0.0, 1.0, 4.0, 60.0, 7.5, 0.0][k]
            picks = rng.sample(table, 6)
            recs = [g.recording(s["code"], g.in_table_epi(depth), 1) for s in picks[:3]]
            for s in picks[3:]:
                if rng.random() < 0.5 and depth < 9:
                    epi = round(rng.uniform(0, math.sqrt(max(0.0, 9.9 ** 2 - depth ** 2))), 1)
                    if _hypo(epi, depth) < 1.0:
                        epi = 1.0
                else:
                    epi = round(rng.uniform(601, 1000), 1)
                recs.append(g.recording(s["code"], epi))
            if k == 5:
                recs[-1]["epi_km"] = 1000.0
            if k == 3:
                recs[-1]["epi_km"] = 1000.0
            events.append({"id": g.event_id(), "depth_km": depth, "recordings": recs})
        # R = 1 exactly, and an event no station of which the table reaches
        s1, s2 = rng.sample(table, 2)
        events.append({"id": g.event_id(), "depth_km": 1.0, "recordings": [
            {"code": s1["code"], "epi_km": 0.0, "amplitudes": [g.reading("HHN")]},
            {"code": s2["code"], "epi_km": 850.0, "amplitudes": [g.reading("HHE")]}]})
    elif name == "table_ends":
        for _ in range(4):
            picks = rng.sample(table, 5)
            # just inside either end of the table at the surface, the rest on listed distances
            ends = (10.01, 599.99)
            recs = [g.recording(s["code"], ends[j] if j < 2 else float(rng.choice(INNER_NODES)), 1)
                    for j, s in enumerate(picks)]
            events.append({"id": g.event_id(), "depth_km": 0.0, "recordings": recs})
        # epicentre 8 km at depth 6.1 km: hypocentral just over 10 km
        picks = rng.sample(table, 3)
        events.append({"id": g.event_id(), "depth_km": 6.1, "recordings": [
            g.recording(s["code"], 8.0, 1) for s in picks[:1]] + [g.recording(s["code"], g.in_table_epi(6.1), 2) for s in picks[1:]]})
    elif name == "limits":
        table = g.station_table(200)
        table[0]["correction"], table[1]["correction"], table[2]["correction"] = -1.0, 1.0, 0.0
        big = {"id": "L" * 20, "depth_km": 60.0, "recordings": []}
        for s in table[:40]:
            rec = g.recording(s["code"], g.in_table_epi(60.0), 1)
            big["recordings"].append(rec)
        big["recordings"][0]["amplitudes"][0]["amplitude_nm"] = 1e8
        big["recordings"][0]["amplitudes"][0]["noise_nm"] = 1e7
        big["recordings"][1]["amplitudes"][0]["amplitude_nm"] = 0.1
        big["recordings"][1]["amplitudes"][0]["noise_nm"] = 0.01
        events.append(big)
        events.append({"id": "Z", "depth_km": 0.0, "recordings": [
            {"code": table[0]["code"], "epi_km": 10.01, "amplitudes": [{"channel": "HHE", "amplitude_nm": 0.1, "noise_nm": 0.01}]},
            {"code": table[1]["code"], "epi_km": 599.99, "amplitudes": [{"channel": "HHE", "amplitude_nm": 1e8, "noise_nm": 1e7}]},
            {"code": table[2]["code"], "epi_km": 100.0, "amplitudes": [g.reading("HHN")]}]})
        while len(events) < 50:
            events.append(g.event(table, 1))
    elif name == "shared_station":
        # trap T3 inputs: a station whose two sensors arrive as separate recordings;
        # pooled readings, one vote in the median and in the count of three
        for k in range(6):
            depth = round(rng.uniform(0, 60), 1)
            n_st = [2, 3, 4, 5, 3, 4][k]
            picks = rng.sample(table, n_st)
            recs = []
            for j, s in enumerate(picks):
                epi = g.in_table_epi(depth)
                if j < (2 if k == 3 else 1):
                    bb, sm = rng.sample(_SENSORS, 2)
                    r1 = g.recording(s["code"], epi, rng.choice([1, 2]), bb)
                    r2 = g.recording(s["code"], epi, 2 if len(r1["amplitudes"]) == 1 else rng.choice([1, 2]), sm)
                    recs.extend([r1, r2])
                else:
                    recs.append(g.recording(s["code"], epi))
            rng.shuffle(recs)
            events.append({"id": g.event_id(), "depth_km": depth, "recordings": recs})
    elif name.startswith("generated"):
        for _ in range(rng.randint(4, 8)):
            events.append(g.event(table, rng.randint(1, 12)))
    else:
        raise KeyError(name)
    bulletin = {"stations": table, "events": events}
    keeps_the_limits(bulletin)
    return bulletin


FAMILIES = ("plain_nodes", "hypocentral", "interpolation", "station_mean", "median",
            "median_even", "min_three", "three", "correction", "order", "readings", "off_table", "shared_station", "table_ends", "limits",
            "generated-1", "generated-2", "generated-3")
TRAP_FAMILIES = {"readings": {"sub_noise"}, "off_table": {"off_table"}, "shared_station": {"shared_station"}}
