"""Write every graded bulletin and its expected report into tests/expected/.

Run from the task folder: python3 solution/seal.py

Expectations come from solution/model.py (written from NPM-4, never importing the
package). Bulletins come from solution/jobgen.py (fixed seed) and the hand-built
solution/fixtures.py. Each bulletin is checked against NPM-4 section 1, against
the trap classes its file may carry, and against two numeric rules: an amplitude
is either a binary-exact three-times tie or at least 1e-9 (relative) away from
one, and a hypocentral distance is either exactly 10 or 600 km in both the
sqrt and the hypot forms, or at least 1e-3 km away from both. Nothing here runs
at grading time; the verifier only reads the files and checks their SHA-256.
"""

import hashlib
import json
import math
import sys
from fractions import Fraction
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
    "readings.jsonl": [jobgen.family("readings"), fixtures.readings_ties()],
    "hypocentral.jsonl": [jobgen.family("hypocentral"), fixtures.hypocentral()],
    "interpolation.jsonl": [jobgen.family("interpolation")],
    "table_ends.jsonl": [jobgen.family("table_ends")],
    "off_table.jsonl": [jobgen.family("off_table"), fixtures.off_table()],
    "correction.jsonl": [jobgen.family("correction")],
    "station_mean.jsonl": [jobgen.family("station_mean")],
    "shared_station.jsonl": [jobgen.family("shared_station"), fixtures.shared()],
    "median.jsonl": [jobgen.family("median")],
    "median_even.jsonl": [jobgen.family("median_even")],
    "fewer_than_three.jsonl": [jobgen.family("min_three"), fixtures.one_station()],
    "three.jsonl": [jobgen.family("three")],
    "limits.jsonl": [jobgen.family("limits")],
    "order.jsonl": [jobgen.family("order")],
    "generated.jsonl": [jobgen.family("generated-1"), jobgen.family("generated-2")],
}
ALLOWED = {"readings.jsonl": {"sub_noise"}, "off_table.jsonl": {"off_table"},
           "shared_station.jsonl": {"shared_station"}}


def numeric_discipline(bulletin):
    for event in bulletin["events"]:
        for rec in event["recordings"]:
            for a in rec["amplitudes"]:
                amp, noise = a["amplitude_nm"], a["noise_nm"]
                if Fraction(amp) == 3 * Fraction(noise):
                    assert amp >= 3 * noise and amp / noise >= 3, a
                else:
                    assert abs(amp / (3 * noise) - 1) > 1e-9, a
            e, d = float(rec["epi_km"]), float(event["depth_km"])
            r1, r2 = math.sqrt(e * e + d * d), math.hypot(e, d)
            for end in (10.0, 600.0):
                if r1 == end or r2 == end:
                    assert r1 == r2 == end, (e, d)
                else:
                    assert abs(r1 - end) >= 1e-3, (e, d)


def _rounded(value):
    if isinstance(value, float):
        return round(value, 10)
    if isinstance(value, dict):
        return {k: _rounded(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_rounded(v) for v in value]
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
            lines.append(json.dumps({"bulletin": b, "report": _rounded(model.reduce_bulletin(b))},
                                    separators=(",", ":"), sort_keys=True))
        assert set().union(*(jobgen.trap_inputs(b) for b in bulletins)) == ALLOWED.get(name, set()), name
        data = ("\n".join(lines) + "\n").encode()
        (OUT / name).write_bytes(data)
        roster.append("%s %s %d" % (hashlib.sha256(data).hexdigest(), name, len(lines)))
    (OUT / "ROSTER").write_text("\n".join(roster) + "\n")


if __name__ == "__main__":
    main()
