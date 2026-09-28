"""Independent expectation model for QA-SOP-311 (/app/docs/qa-sop-lot-disposition.md).

Re-derives every reported figure from the SOP, reading the job directory itself. It never
imports or runs the package under repair. Where the SOP gives no rule for a figure, the model
mirrors the step the shipped package takes and says so in a "Shipped step" comment.

    python3 solution/model.py JOB_DIR      prints the expected report as JSON
"""

import csv
import json
import math
import sys
from datetime import datetime
from pathlib import Path

LOGGED_MAX = 30  # SOP 2.4: a logged interval is 30 minutes or less
CHAIN_MAX = 2880  # SOP 2.9: a chained lot has no handover longer than this
SHIPPED_HOLD_CAP = 60  # attribution.HOLD_CAP_MINUTES in the shipped package (used only where the SOP is silent)
UNLOGGED_LIMIT = 120  # SOP 6.2
KELVIN = 273.15  # SOP 1.3


def _minute(stamp):
    moment = datetime.strptime(stamp.strip(), "%Y-%m-%dT%H:%M")
    return (moment - datetime(2020, 1, 1)).days * 1440 + moment.hour * 60 + moment.minute


def _export(path):
    with open(path, newline="", encoding="utf-8") as handle:
        rows = list(csv.reader(handle))
    assert rows[0] == ["timestamp", "temp_c"], rows[0]
    return [(_minute(stamp), float(temp)) for stamp, temp in rows[1:]]


def load(job_dir):
    job = Path(job_dir)
    record = json.loads((job / "stability.json").read_text(encoding="utf-8"))
    lots = json.loads((job / "lots.json").read_text(encoding="utf-8"))
    exports = {}
    for lot in lots:
        for name in lot["legs"]:
            if name not in exports:
                exports[name] = _export(job / "loggers" / f"{name}.csv")
    return record, lots, exports


class Table:
    """SOP 2.1 and 2.5: the labelled range and the bands on each side of it."""

    def __init__(self, record):
        self.low, self.high = (float(v) for v in record["labelled_range_c"])
        bands = [(b["band"], float(b["lower_c"]), float(b["upper_c"])) for b in record["bands"]]
        self.below = sorted((b for b in bands if b[2] <= self.low), key=lambda b: b[1])
        self.above = sorted((b for b in bands if b[1] >= self.high), key=lambda b: b[1])
        assert len(self.below) + len(self.above) == len(bands)

    def band(self, temp):
        if self.low <= temp <= self.high:  # 2.1: in range, both limits included
            return None
        for name, lower, upper in self.below:  # 2.5: from the lower end, up to but not including the upper
            if lower <= temp < upper:
                return name
        for name, lower, upper in self.above:  # 2.5: above the lower end, up to and including the upper
            if lower < temp <= upper:
                return name
        raise ValueError(f"reading {temp} lies outside the table's span (outside SOP 1.4)")


def hold(readings):
    """SOP 2.3, 2.4, 2.7: the hold of each reading of one leg's export."""
    held = []
    for index in range(len(readings)):
        if index + 1 == len(readings):
            held.append(0)  # 2.7: the last reading of an export holds nought
            continue
        span = readings[index + 1][0] - readings[index][0]
        if span <= LOGGED_MAX:
            held.append(span)  # 2.7: the length of the logged interval it opens
        else:
            # The reading opens a logger gap: the SOP gives its hold no value. Shipped step:
            # attribution.holds takes min(span, HOLD_CAP_MINUTES), the cap at 60.
            held.append(min(span, SHIPPED_HOLD_CAP))
    return held


def hours(minutes):
    """SOP 1.2: nearest hundredth of an hour, from exact integer arithmetic."""
    hundredths = (10 * minutes + 3) // 6  # floor(5m/3 + 1/2); 5m/3 is never a half
    return hundredths / 100


def mkt(temps, weights, ratio):
    """SOP 5.1 and 1.3, in degrees Celsius, unrounded."""
    total = math.fsum(weights)
    mean = math.fsum(w * math.exp(-ratio / (t + KELVIN)) for t, w in zip(temps, weights)) / total
    return ratio / -math.log(mean) - KELVIN


def dispose(record, lot, exports, table):
    names = [b["band"] for b in record["bands"]]
    per_leg = []
    unlogged = 0
    temps, weights = [], []
    for leg in lot["legs"]:
        readings = exports[leg]
        held = hold(readings)
        leg_time = {name: 0 for name in names}
        for (minute, temp), spent in zip(readings, held):  # 2.6, 3.1
            name = table.band(temp)
            if name is not None:
                leg_time[name] += spent
        per_leg.append(leg_time)
        unlogged += sum(  # 2.4, 3.2, 4.3
            b[0] - a[0] for a, b in zip(readings, readings[1:]) if b[0] - a[0] > LOGGED_MAX
        )
        temps += [temp for _, temp in readings]  # 5.1: each export on its own (2.3), no interval across a handover
        weights += held
    handovers = [exports[b][0][0] - exports[a][-1][0] for a, b in zip(lot["legs"], lot["legs"][1:])]  # 2.9
    if all(h <= CHAIN_MAX for h in handovers):
        band_time = {name: sum(leg[name] for leg in per_leg) for name in names}  # 4.1, chained lot
    else:
        # Not a chained lot: the SOP gives its time in a band no value. Shipped step:
        # disposition.lot_band_minutes takes the largest leg figure (each leg's figure per 3.1).
        band_time = {name: max(leg[name] for leg in per_leg) for name in names}
    prior = lot.get("prior_minutes", {})
    remaining = {  # 2.10, 4.2
        b["band"]: int(b["allowance_h"]) * 60 - int(prior.get(b["band"], 0)) - band_time[b["band"]]
        for b in record["bands"]
    }
    figure = mkt(temps, weights, float(record["activation_ratio_k"]))
    frozen = any(temp < float(record["freeze_point_c"]) for temp in temps)  # 2.7
    if frozen or any(left < 0 for left in remaining.values()):  # 6.1
        decision = "reject"
    elif figure > table.high or unlogged > UNLOGGED_LIMIT:  # 6.2, unrounded
        decision = "quarantine"
    else:
        decision = "release"  # 6.3
    margins = {
        "mkt_to_upper": abs(figure - table.high),
        "mkt_to_half_tenth": abs((figure * 10) - math.floor(figure * 10) - 0.5) / 10,
    }
    return {
        "lot": lot["lot"],
        "disposition": decision,
        "band_hours": {name: hours(band_time[name]) for name in names},
        "remaining_hours": {name: hours(remaining[name]) for name in names},
        "unlogged_hours": hours(unlogged),
        "mkt_c": round(figure, 1),
    }, margins


def limit_breaches(job_dir):
    """The SOP 1.4 limits this model relies on that a job breaks (empty for a legal job)."""
    record, lots, exports = load(job_dir)
    breaches = []
    lowest = min(float(b["lower_c"]) for b in record["bands"])
    highest = max(float(b["upper_c"]) for b in record["bands"])
    for name, readings in exports.items():
        spans = [b[0] - a[0] for a, b in zip(readings, readings[1:])]
        if not 2 <= len(readings) <= 20000 or not all(1 <= x <= 1440 for x in spans) or min(spans) > LOGGED_MAX:
            breaches.append(f"export {name}")
        if not all(lowest <= t <= highest and -40.0 <= t <= 60.0 for _, t in readings):
            breaches.append(f"span {name}")
    for lot in lots:
        for a, b in zip(lot["legs"], lot["legs"][1:]):
            if not 0 <= exports[b][0][0] - exports[a][-1][0] <= 10080:
                breaches.append(f"handover {lot['lot']}")
    return breaches


def expected_report(job_dir, with_margins=False):
    record, lots, exports = load(job_dir)
    table = Table(record)
    results = [dispose(record, lot, exports, table) for lot in lots]
    report = {"product": record["product"], "lots": [r for r, _ in results]}
    if with_margins:
        return report, [m for _, m in results]
    return report


if __name__ == "__main__":
    json.dump(expected_report(sys.argv[1]), sys.stdout)
    sys.stdout.write("\n")
