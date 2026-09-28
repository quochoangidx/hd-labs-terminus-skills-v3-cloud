"""Write every graded bulletin and its expected report into tests/expected/.

Run from the task folder: python3 solution/seal.py

Expectations come from solution/model.py (written from NPM-4, never importing the
package) and are stored to 7 decimals, within 5.1e-8 of the exact figures
(the verifier accepts 1.5e-6, the middle of the instruction's open band
between 1e-6 and 2e-6). Bulletins come from
solution/jobgen.py (fixed seed) and the hand-built solution/fixtures.py. Each
bulletin is checked against NPM-4 section 1 (including its two margins: no
amplitude within one part in a thousand of three times its noise, no hypocentral
distance within a metre of 10 or 600 km), checked again in exact decimal
arithmetic with room to spare, and against the trap classes its file may carry.
Nothing here runs at grading time; the verifier only reads the files and checks
their SHA-256.
"""

import hashlib
import json
import sys
from decimal import Decimal, getcontext
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import fixtures  # noqa: E402
import jobgen  # noqa: E402
import model  # noqa: E402

OUT = HERE.parent / "tests" / "expected"

FILES = {
    "gain.jsonl": [jobgen.family("plain_nodes")],
    "half.jsonl": [fixtures.half()],
    "readings.jsonl": [jobgen.family("readings"), fixtures.readings_near_line()],
    "hypocentral.jsonl": [jobgen.family("hypocentral"), fixtures.hypocentral()],
    "interpolation.jsonl": [jobgen.family("interpolation")],
    "table_ends.jsonl": [jobgen.family("table_ends")],
    "off_table.jsonl": [jobgen.family("off_table"), fixtures.off_table()],
    "correction.jsonl": [jobgen.family("correction")],
    "station_mean.jsonl": [jobgen.family("station_mean"), fixtures.channel_codes()],
    "shared_station.jsonl": [jobgen.family("shared_station"), fixtures.shared()],
    "median.jsonl": [jobgen.family("median")],
    "median_even.jsonl": [jobgen.family("median_even")],
    "fewer_than_three.jsonl": [jobgen.family("min_three"), fixtures.one_station()],
    "three.jsonl": [jobgen.family("three")],
    "combined.jsonl": [fixtures.together()],
    "limits.jsonl": [jobgen.family("limits")],
    "order.jsonl": [jobgen.family("order"), fixtures.labels()],
    "generated.jsonl": [jobgen.family("generated-1"), jobgen.family("generated-2")],
}
ALLOWED = {"readings.jsonl": {"sub_noise"}, "off_table.jsonl": {"off_table"},
           "shared_station.jsonl": {"shared_station"},
           "combined.jsonl": {"sub_noise", "off_table", "shared_station"}}


def _exact(x):
    # the decimal the file writes for this number
    return Decimal(repr(float(x)))


def numeric_discipline(bulletin):
    """Section 1's two margins hold in exact decimal arithmetic, at least half again over."""
    getcontext().prec = 60
    for event in bulletin["events"]:
        depth = _exact(event["depth_km"])
        for rec in event["recordings"]:
            for a in rec["amplitudes"]:
                amp, noise = _exact(a["amplitude_nm"]), _exact(a["noise_nm"])
                assert abs(amp - 3 * noise) > Decimal("0.0045") * noise, a
            r = (_exact(rec["epi_km"]) ** 2 + depth ** 2).sqrt()
            for end in (Decimal(10), Decimal(600)):
                assert abs(r - end) > Decimal("0.0015"), (rec, event["depth_km"])


def _stored(value):
    # 7 decimals: within 5.1e-8 of the exact figure (model error measured below 1e-12), far
    # inside the open band between 1e-6 and 2e-6 the instruction leaves, and small enough for
    # the review packet
    if isinstance(value, float):
        return round(value, 7)
    if isinstance(value, dict):
        return {k: _stored(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_stored(v) for v in value]
    return value


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("*"):
        old.unlink()
    roster = []
    for name, bulletins in FILES.items():
        lines = []
        for b in bulletins:
            jobgen.keeps_the_limits(b)
            assert jobgen.trap_inputs(b) <= ALLOWED.get(name, set()), (name, jobgen.trap_inputs(b))
            numeric_discipline(b)
            lines.append(json.dumps({"bulletin": b, "report": _stored(model.reduce_bulletin(b))},
                                    separators=(",", ":"), sort_keys=True))
        assert set().union(*(jobgen.trap_inputs(b) for b in bulletins)) == ALLOWED.get(name, set()), name
        data = ("\n".join(lines) + "\n").encode()
        (OUT / name).write_bytes(data)
        roster.append("%s %s %d" % (hashlib.sha256(data).hexdigest(), name, len(lines)))
    (OUT / "ROSTER").write_text("\n".join(roster) + "\n")


if __name__ == "__main__":
    main()
