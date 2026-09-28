"""Write environment/app/examples/two-stations.json (authoring only)."""
import json
import random
import sys
sys.path.insert(0, '.')
import jobs

rng = random.Random(1177)


def station(sid, hour, base, spread, wet):
    entries = []
    for k in range(31):
        base = max(380, min(700, base + rng.randint(-35, 40)))
        hi = base + rng.randint(40, spread)
        lo = hi - rng.randint(120, 260)
        r = rng.random()
        p = "0.00" if r > wet else ("T" if r > wet * 0.7 else jobs.fmt_amt(rng.choice([rng.randint(1, 40), rng.randint(5, 90), rng.randint(20, 160)])))
        entries.append({"max": jobs.fmt_temp(hi), "min": jobs.fmt_temp(lo), "precip": p})
    return {"id": sid, "hour": hour, "days": entries[:30], "next": entries[30]}


a = station("CN-0412", 7, 520, 120, 0.4)
b = station("CN-1177", 17, 560, 140, 0.35)
a["days"][11]["max"] = "M"
b["days"][23]["precip"] = "M"
form = {"network": "Upper Basin Cooperative Network", "month": "2024-04", "stations": [a, b]}
jobs.model.within_limits(form)
assert not jobs.model.carries_incomplete_month(form) and not jobs.model.carries_accumulated_at_morning(form)
lines = ['{', f'  "network": {json.dumps(form["network"])},', f'  "month": "{form["month"]}",', '  "stations": [']
for si, s in enumerate(form["stations"]):
    lines += ['    {', f'      "id": "{s["id"]}",', f'      "hour": {s["hour"]},', '      "days": [']
    for k, e in enumerate(s["days"]):
        lines.append('        ' + json.dumps(e) + (',' if k < len(s["days"]) - 1 else ''))
    lines += ['      ],', '      "next": ' + json.dumps(s["next"]), '    }' + (',' if si == 0 else '')]
lines += ['  ]', '}']
text = "\n".join(lines) + "\n"
assert json.loads(text) == form
open(jobs.TASK / "environment/app/examples/two-stations.json", "w").write(text)
print(json.dumps(jobs.model.summarize(form)["stations"][0]))
