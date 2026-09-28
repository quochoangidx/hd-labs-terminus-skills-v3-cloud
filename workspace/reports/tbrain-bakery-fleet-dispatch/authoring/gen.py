"""Authoring: generate the four bakery mornings (integers only, deterministic)."""
import json, random

def make(seed, n, name):
    rng = random.Random(seed)
    depot = {"x": 0, "y": 0, "open": 4 * 3600, "close": 13 * 3600}
    centres = [(rng.randint(-120, 120), rng.randint(-120, 120)) for _ in range(rng.randint(4, 7))]
    customers = []
    for i in range(1, n + 1):
        if rng.random() < 0.75:
            cx, cy = rng.choice(centres)
            x, y = cx + int(rng.gauss(0, 14)), cy + int(rng.gauss(0, 14))
        else:
            x, y = rng.randint(-160, 160), rng.randint(-160, 160)
        kind = rng.choices(["cafe", "grocer", "hotel", "market"], [5, 3, 1, 1])[0]
        demand = {"cafe": rng.randint(2, 8), "grocer": rng.randint(6, 18), "hotel": rng.randint(10, 30), "market": rng.randint(20, 45)}[kind]
        start = rng.choice([5, 5.5, 6, 6, 6.5, 7, 7, 7.5, 8, 9]) * 3600
        width = rng.choice([45, 60, 60, 90, 120, 180]) * 60
        if kind == "market":
            start, width = 4.5 * 3600, 90 * 60
        customers.append({"id": i, "x": x, "y": y, "demand": demand, "ready": int(start), "due": int(start + width),
                          "service": 240 + 25 * demand, "kind": kind})
    fleet = [
        {"type": "bike", "count": max(3, n // 12), "capacity": 14, "fixed": 900, "per_unit": 2, "pace": 22, "shift": 5 * 3600, "range": 260},
        {"type": "van", "count": max(4, n // 8), "capacity": 60, "fixed": 4200, "per_unit": 11, "pace": 11, "shift": 7 * 3600, "range": None},
        {"type": "truck", "count": max(2, n // 20), "capacity": 150, "fixed": 9500, "per_unit": 19, "pace": 13, "shift": 8 * 3600, "range": None},
    ]
    return {"name": name, "depot": depot, "customers": customers, "fleet": fleet}

if __name__ == "__main__":
    for seed, n, name in [(11, 60, "harbour-lanes"), (23, 110, "old-town"), (37, 160, "riverside"), (41, 220, "north-ring")]:
        json.dump(make(seed, n, name), open(f"/tmp/regen-{name}.json", "w"), indent=1)
