"""Authoring: generate stamping-plant weeks (integers only, deterministic). Times in minutes from Monday 06:00."""
import json, random

FAMILIES = ["A", "B", "C", "D", "E", "F"]

def make(seed, n_jobs, presses, name):
    rng = random.Random(seed)
    horizon = 5 * 24 * 60
    press_list = []
    for i, (tons, rate) in enumerate(presses, start=1):
        windows = []
        for _ in range(rng.randint(1, 2)):
            s = rng.randint(6 * 60, horizon - 12 * 60)
            windows.append([s, s + rng.choice([120, 240, 480])])
        windows.sort()
        merged = []
        for w in windows:
            if merged and w[0] <= merged[-1][1]:
                merged[-1][1] = max(merged[-1][1], w[1])
            else:
                merged.append(w)
        press_list.append({"id": f"P{i}", "tonnage": tons, "strokes_per_minute": rate,
                           "initial_family": rng.choice(FAMILIES), "maintenance": merged})
    setup = {}
    for a in FAMILIES:
        setup[a] = {}
        for b in FAMILIES:
            setup[a][b] = 10 if a == b else rng.choice([35, 45, 60, 75, 90, 120])
    jobs = []
    for j in range(1, n_jobs + 1):
        fam = rng.choice(FAMILIES)
        tons = rng.choice([200, 250, 400, 400, 600, 800])
        strokes = rng.choice([600, 1200, 1800, 2400, 3600, 4800, 7200])
        release = rng.choice([0, 0, 0, rng.randint(0, horizon // 2)])
        due = release + rng.randint(8 * 60, 3 * 24 * 60)
        jobs.append({"id": f"J{j:03d}", "family": fam, "tonnage": tons, "strokes": strokes,
                     "release": release, "due": due, "weight": rng.choice([1, 1, 2, 3, 5])})
    return {"name": name, "presses": press_list, "setup_minutes": setup, "setup_cost_per_minute": 40,
            "jobs": jobs}

if __name__ == "__main__":
    specs = [
        (101, 45, [(400, 30), (800, 18), (600, 22), (250, 40)], "week-36"),
        (202, 85, [(400, 30), (800, 18), (600, 22), (250, 40), (400, 26), (800, 16)], "week-37"),
        (303, 140, [(400, 30), (800, 18), (600, 22), (250, 40), (400, 26), (800, 16), (600, 24), (200, 44)], "week-38"),
    ]
    for seed, n, presses, name in specs:
        json.dump(make(seed, n, presses, name), open(f"{name}.json", "w"), indent=1)
    print("ok")
