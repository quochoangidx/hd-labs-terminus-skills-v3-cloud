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


def readings_near_line():
    """Amplitudes just clear of three times their noise, on either side of it."""
    return {"stations": _table(("LNA", 0.0), ("LNB", 0.25), ("LNC", -0.5), ("LND", 0.0)),
            "events": [{"id": "line-1", "depth_km": 0, "recordings": [
                _rec("LNA", 100.0, _amp("HHE", 1.51, 0.5), _amp("HHN", 1.49, 0.5)),
                _rec("LNB", 100.0, _amp("HHE", 300.5, 100.0), _amp("HHN", 2990.0, 1000.0)),
                _rec("LNC", 100.0, _amp("HNE", 6000.0, 0.01), _amp("HNN", 0.76, 0.25)),
                _rec("LND", 150.0, _amp("HHN", 40.0, 20.0), _amp("HHE", 12.0, 0.5))]}]}


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


def channel_codes():
    """Readings under channel codes of any three characters, alone and beside familiar ones."""
    return {"stations": _table(("CHA", 0.0), ("CHB", 0.2), ("CHC", -0.3), ("CHD", 0.0), ("CHE", 0.1)),
            "events": [
                {"id": "chan-1", "depth_km": 4.0, "recordings": [
                    _rec("CHA", 100.0, _amp("XYZ", 1000.0, 1.0)),
                    _rec("CHB", 60.0, _amp("HHZ", 800.0, 2.0), _amp("HHE", 90.0, 2.0)),
                    _rec("CHC", 220.0, _amp("123", 50.0, 1.0), _amp("a_b", 400.0, 1.0)),
                    _rec("CHD", 35.0, _amp("Z Z", 2500.0, 3.0))]},
                {"id": "chan-2", "depth_km": 20.0, "recordings": [
                    _rec("CHE", 140.0, _amp("?!.", 120.0, 1.0), _amp("LHN", 30.0, 1.0)),
                    _rec("CHA", 310.0, _amp("EHZ", 15.0, 0.5)),
                    _rec("CHD", 75.0, _amp("BH1", 700.0, 1.0), _amp("xx9", 150.0, 1.0))]}]}


def labels():
    """Event ids of odd characters and lengths, station codes at both ends of their length."""
    return {"stations": _table(("0", 0.1), ("99999", -0.2), ("A1B2C", 0.0), ("Q", 0.3)),
            "events": [
                {"id": "0", "depth_km": 2.0, "recordings": [
                    _rec("99999", 55.0, _amp("HHE", 400.0, 1.0)),
                    _rec("0", 120.0, _amp("HHN", 90.0, 1.0)),
                    _rec("A1B2C", 250.0, _amp("HHE", 30.0, 1.0))]},
                {"id": "ev 7 / late", "depth_km": 9.5, "recordings": [
                    _rec("Q", 80.0, _amp("HHE", 300.0, 1.0)),
                    _rec("A1B2C", 40.0, _amp("HNE", 900.0, 2.0), _amp("HNN", 700.0, 2.0)),
                    _rec("0", 160.0, _amp("BHN", 60.0, 1.0))]},
                {"id": "\"q\"-\u00e9v\u00e9nement#12", "depth_km": 0.0, "recordings": [
                    _rec("0", 30.0, _amp("EH1", 500.0, 1.0)),
                    _rec("99999", 45.0, _amp("EH2", 350.0, 1.0)),
                    _rec("Q", 500.0, _amp("HHN", 3.0, 0.2))]}]}


def together():
    """Sub-noise amplitudes at stations off the table and at two-sensor sites; a two-sensor site off the table."""
    return {"stations": _table(("TA", 0.0), ("TB", 0.2), ("TC", -0.3), ("TD", 0.1), ("TE", 0.0), ("TF", -0.1), ("TG", 0.4)),
            "events": [
                {"id": "tog-near", "depth_km": 3.0, "recordings": [
                    _rec("TA", 4.0, _amp("AAA", 100.0, 1.0), _amp("BBB", 1000.0, 400.0)),
                    _rec("TB", 50.0, _amp("HHE", 600.0, 1.0), _amp("HHN", 900.0, 400.0)),
                    _rec("TC", 80.0, _amp("HHE", 250.0, 1.0)),
                    _rec("TD", 140.0, _amp("HHN", 90.0, 1.0))]},
                {"id": "tog-far", "depth_km": 0.0, "recordings": [
                    _rec("TE", 750.0, _amp("HHE", 50.0, 1.0), _amp("HHN", 20.0, 10.0)),
                    _rec("TA", 60.0, _amp("HHE", 700.0, 1.0)),
                    _rec("TB", 90.0, _amp("HHE", 800.0, 1.0)),
                    _rec("TE", 750.0, _amp("HNE", 30.0, 1.0)),
                    _rec("TB", 90.0, _amp("HNE", 5.0, 2.0), _amp("HNN", 400.0, 1.0)),
                    _rec("TC", 120.0, _amp("HHN", 150.0, 1.0))]},
                {"id": "tog-shared", "depth_km": 10.0, "recordings": [
                    _rec("TF", 40.0, _amp("HHE", 300.0, 1.0), _amp("HHN", 100.0, 50.0)),
                    _rec("TG", 200.0, _amp("HHE", 60.0, 1.0)),
                    _rec("TF", 40.0, _amp("HNE", 90.0, 40.0), _amp("HNN", 250.0, 1.0)),
                    _rec("TG", 200.0, _amp("HNE", 10.0, 5.0), _amp("HNN", 40.0, 1.0)),
                    _rec("TD", 30.0, _amp("HHE", 400.0, 1.0))]},
                {"id": "tog-near-pair", "depth_km": 8.0, "recordings": [
                    _rec("TC", 5.0, _amp("HHE", 500.0, 1.0), _amp("HHN", 100.0, 40.0)),
                    _rec("TA", 20.0, _amp("HHE", 350.0, 1.0)),
                    _rec("TC", 5.0, _amp("HNE", 700.0, 2.0)),
                    _rec("TB", 25.0, _amp("HHN", 450.0, 1.0))]}]}
