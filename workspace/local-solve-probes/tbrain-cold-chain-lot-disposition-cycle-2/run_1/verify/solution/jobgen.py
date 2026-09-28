"""Job-directory generator for QA-SOP-311 (authoring only; graded jobs are sealed files).

`write_job(path, rng, **shape)` draws one job within the SOP's section 1 limits. The shape
switches decide which kinds of input the job may carry, so that broad families can be drawn
free of the inputs the SOP gives no rule for:

- gaps: legs may hold spacings longer than 30 minutes (logger gaps);
- handover: the largest spacing between one leg's last reading and the next leg's first
  (0 keeps every handover at the same minute);
- transients: release-certificate entries may be shorter than 15 minutes;
- inside: the share of readings drawn inside the labelled range.
"""

import json
import random
from datetime import datetime, timedelta
from pathlib import Path

START = datetime(2020, 1, 1)
END = datetime(2039, 12, 31, 23, 59)


def tenth(value):
    return round(value * 10) / 10


def draw_record(rng):
    low = tenth(rng.uniform(-30.0, 20.0))
    high = tenth(low + rng.uniform(1.0, 25.0))
    bands = []
    # below the range: from 1 to 3 bands, adjoining, lowest end no colder than -40.0
    count = rng.randint(1, 3)
    inner = low
    for index in range(count):
        room = inner - (-40.0) - 0.5 * (count - index - 1)
        width = tenth(rng.uniform(0.5, min(40.0, room)))
        if index == count - 1 and rng.random() < 0.15:
            width = tenth(min(40.0, room))
        lower = tenth(inner - width)
        bands.append({"band": f"below-{index + 1}", "lower_c": lower, "upper_c": inner, "allowance_h": 0})
        inner = lower
    count = rng.randint(1, 3)
    inner = high
    for index in range(count):
        room = 60.0 - inner - 0.5 * (count - index - 1)
        width = tenth(rng.uniform(0.5, min(40.0, room)))
        upper = tenth(inner + width)
        bands.append({"band": f"above-{index + 1}", "lower_c": inner, "upper_c": upper, "allowance_h": 0})
        inner = upper
    names = rng.sample(["cold", "chill", "deep", "frost", "warm", "hot", "heat", "high", "dock", "b7", "x-1", "tier-3"], len(bands))
    for band, name in zip(bands, names):
        band["band"] = name
        band["allowance_h"] = rng.choice([0, 2, 8, 24, 72, 168, 500, 2000, rng.randint(0, 2000)])
    rng.shuffle(bands)
    lowest = min(b["lower_c"] for b in bands)
    freeze = lowest if rng.random() < 0.5 else tenth(rng.uniform(lowest, low))
    return {
        "product": rng.choice(["Ferivax 20 mg/mL", "Oltamab 150 mg", "Nevrocil drops", "Sarlidine 5 mg"]),
        "labelled_range_c": [low, high],
        "freeze_point_c": freeze,
        "activation_ratio_k": rng.choice([5000.0, 20000.0, 10000.0, round(rng.uniform(5000, 20000), 1)]),
        "bands": bands,
    }


def draw_temp(rng, record, inside=0.6):
    low, high = record["labelled_range_c"]
    lowest = min(b["lower_c"] for b in record["bands"])
    highest = max(b["upper_c"] for b in record["bands"])
    ends = sorted({low, high} | {b["lower_c"] for b in record["bands"]} | {b["upper_c"] for b in record["bands"]})
    pick = rng.random()
    if pick < inside:
        return tenth(rng.uniform(low, high))
    pick = inside + (pick - inside) * 0.4 / (1 - inside)
    if pick < 0.72:
        return rng.choice(ends)
    return tenth(rng.uniform(lowest, highest))


def draw_leg(rng, record, start, readings, gaps, inside):
    rows = []
    moment = start
    for index in range(readings):
        if index:
            if gaps and rng.random() < 0.25:
                step = rng.choice([31, 45, 60, 61, 90, 240, 1440, rng.randint(31, 1440)])
            else:
                step = rng.choice([1, 5, 10, 15, 29, 30, rng.randint(1, 30)])
            moment += timedelta(minutes=step)
        rows.append((moment, draw_temp(rng, record, inside)))
    return rows


def write_job(path, rng, lots=3, max_legs=4, max_readings=40, gaps=True, handover=2880, transients=True, inside=0.6):
    path = Path(path)
    (path / "loggers").mkdir(parents=True, exist_ok=True)
    record = draw_record(rng)
    lot_rows = []
    leg_count = 0
    for lot_index in range(lots):
        legs = []
        moment = START + timedelta(minutes=rng.randint(0, 9_000_000))
        for _ in range(rng.randint(1, max_legs)):
            leg_count += 1
            name = f"leg{leg_count:04d}-{rng.choice(['road', 'air', 'hub', 'van'])}"
            rows = draw_leg(rng, record, moment, rng.randint(2, max_readings), gaps, inside)
            assert rows[-1][0] <= END
            with open(path / "loggers" / f"{name}.csv", "w", encoding="utf-8", newline="") as handle:
                handle.write("timestamp,temp_c\n")
                for stamp, temp in rows:
                    handle.write(f"{stamp:%Y-%m-%dT%H:%M},{temp:.1f}\n")
            legs.append(name)
            moment = rows[-1][0] + timedelta(minutes=rng.choice([0, handover, rng.randint(0, handover)]))
        entry = {"lot": f"L{rng.randint(10, 99)}{lot_index:03d}", "legs": legs}
        if rng.random() < 0.6:
            chosen = rng.sample([b["band"] for b in record["bands"]], rng.randint(1, len(record["bands"])))
            low = 1 if transients else 15
            entry["certificate"] = {
                name: [rng.choice([low, 14 if transients else 15, 15, 45, 600, 10080, rng.randint(low, 3000)]) for _ in range(rng.choice([0, 1, 2, 5, 50]))]
                for name in chosen
            }
        lot_rows.append(entry)
    (path / "stability.json").write_text(json.dumps(record, indent=1) + "\n", encoding="utf-8")
    (path / "lots.json").write_text(json.dumps(lot_rows, indent=1) + "\n", encoding="utf-8")
    return path


if __name__ == "__main__":
    import sys

    write_job(sys.argv[1], random.Random(int(sys.argv[2]) if len(sys.argv) > 2 else 0))
