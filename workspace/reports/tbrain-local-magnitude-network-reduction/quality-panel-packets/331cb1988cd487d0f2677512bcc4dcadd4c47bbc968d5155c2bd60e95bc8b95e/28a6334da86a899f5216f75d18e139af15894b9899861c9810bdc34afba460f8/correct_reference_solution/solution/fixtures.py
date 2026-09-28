"""Hand-built bulletins for the named cases (authoring only; sealed by seal.py)."""


def _amp(channel, amplitude, noise):
    return {"channel": channel, "amplitude_nm": amplitude, "noise_nm": noise}


def _rec(code, epi, *amps):
    return {"code": code, "epi_km": epi, "amplitudes": list(amps)}


def _table(*pairs):
    return [{"code": c, "correction": v} for c, v in pairs]


def half():
    """Single readings at listed distances, depth 0, no correction: only 2.2 moves the value."""
    return {"stations": _table(("HALF", 0.0), ("PTP2", 0.0), ("WA", 0.0)),
            "events": [{"id": "half-1", "depth_km": 0, "recordings": [
                _rec("HALF", 100.0, _amp("HHE", 1000.0, 1.0)),
                _rec("PTP2", 200.0, _amp("HHN", 2.0, 0.5)),
                _rec("WA", 50.0, _amp("HHE", 20000000.0, 1000.0))]}]}


def readings_ties():
    """Binary-exact three-times ties next to amplitudes just under three times their noise."""
    return {"stations": _table(("TIEA", 0.0), ("TIEB", 0.25), ("TIEC", -0.5), ("TIED", 0.0)),
            "events": [{"id": "ties-1", "depth_km": 0, "recordings": [
                _rec("TIEA", 100.0, _amp("HHE", 1.5, 0.5), _amp("HHN", 1.4, 0.5)),
                _rec("TIEB", 100.0, _amp("HHE", 300.0, 100.0), _amp("HHN", 2990.0, 1000.0)),
                _rec("TIEC", 100.0, _amp("HNE", 6000.0, 0.01), _amp("HNN", 0.75, 0.25)),
                _rec("TIED", 150.0, _amp("HHN", 40.0, 20.0), _amp("HHE", 12.0, 0.5))]}]}


def hypocentral():
    """Depth that moves a station into the table, and stations under deep events."""
    return {"stations": _table(("NEAR", 0.0), ("OVER", 0.1), ("MID", -0.2), ("RIM", 0.0)),
            "events": [
                {"id": "hypo-12", "depth_km": 12.0, "recordings": [
                    _rec("NEAR", 6.0, _amp("HHE", 5000.0, 10.0)),
                    _rec("OVER", 0.0, _amp("HHN", 8000.0, 10.0)),
                    _rec("MID", 120.0, _amp("HHE", 300.0, 5.0)),
                    _rec("RIM", 599.0, _amp("HHE", 3.0, 0.1))]},
                {"id": "hypo-60", "depth_km": 60.0, "recordings": [
                    _rec("OVER", 0.0, _amp("HHE", 900.0, 3.0)),
                    _rec("NEAR", 45.0, _amp("HHN", 700.0, 3.0)),
                    _rec("MID", 300.0, _amp("HHE", 40.0, 1.0))]}]}


def off_table():
    """Stations the table does not reach, beside in-table contributors."""
    return {"stations": _table(("OFFA", 0.0), ("OFFB", 0.1), ("OFFC", -1.0), ("IN1", 0.0), ("IN2", 0.3), ("IN3", -0.3)),
            "events": [
                {"id": "off-near", "depth_km": 3.0, "recordings": [
                    _rec("OFFB", 4.0, _amp("HHE", 1000.0, 10.0)),
                    _rec("IN1", 50.0, _amp("HHE", 1000.0, 1.0)),
                    _rec("IN2", 80.0, _amp("HHN", 600.0, 1.0)),
                    _rec("IN3", 140.0, _amp("HHE", 250.0, 1.0))]},
                {"id": "off-far", "depth_km": 0.0, "recordings": [
                    _rec("OFFA", 1000.0, _amp("HHE", 10.0, 1.0)),
                    _rec("IN1", 50.0, _amp("HHE", 1000.0, 1.0)),
                    _rec("IN2", 80.0, _amp("HHN", 600.0, 1.0)),
                    _rec("IN3", 140.0, _amp("HHE", 250.0, 1.0))]},
                {"id": "off-deep", "depth_km": 60.0, "recordings": [
                    _rec("OFFA", 0.0, _amp("HHE", 1000.0, 1.0)),
                    _rec("OFFB", 600.0, _amp("HHE", 1000.0, 1.0)),
                    _rec("OFFC", 599.0, _amp("HHE", 1000.0, 1.0))]}]}


def shared():
    """Two sensors of one site: pooled readings, one vote in the median and in the count of three."""
    return {"stations": _table(("SITA", 0.0), ("SITB", 0.0), ("SITC", 0.0), ("SITD", 0.2)),
            "events": [
                {"id": "shared-null", "depth_km": 0.0, "recordings": [
                    _rec("SITA", 100.0, _amp("HHE", 1000.0, 1.0), _amp("HHN", 1000.0, 1.0)),
                    _rec("SITB", 100.0, _amp("HHE", 100.0, 1.0)),
                    _rec("SITA", 100.0, _amp("HNE", 10.0, 1.0))]},
                {"id": "shared-median", "depth_km": 0.0, "recordings": [
                    _rec("SITA", 100.0, _amp("HHE", 1000.0, 1.0), _amp("HHN", 1000.0, 1.0)),
                    _rec("SITB", 100.0, _amp("HHE", 100.0, 1.0)),
                    _rec("SITA", 100.0, _amp("HNE", 10.0, 1.0)),
                    _rec("SITC", 100.0, _amp("HHE", 300.0, 1.0))]},
                {"id": "shared-two", "depth_km": 8.0, "recordings": [
                    _rec("SITD", 40.0, _amp("HNN", 90.0, 2.0)),
                    _rec("SITC", 75.0, _amp("HHE", 500.0, 1.0), _amp("HHN", 400.0, 1.0)),
                    _rec("SITB", 30.0, _amp("HHE", 2000.0, 1.0)),
                    _rec("SITD", 40.0, _amp("HHE", 3000.0, 2.0), _amp("HHN", 2500.0, 2.0)),
                    _rec("SITC", 75.0, _amp("HNE", 20.0, 1.0))]}]}


def one_station():
    """The floor of section 1: a one-station table and a one-recording event (no network magnitude)."""
    return {"stations": _table(("SOLO", -0.1)),
            "events": [{"id": "solo", "depth_km": 5.0, "recordings": [
                _rec("SOLO", 42.0, _amp("HHE", 850.0, 4.0), _amp("HHN", 700.0, 4.0))]}]}
