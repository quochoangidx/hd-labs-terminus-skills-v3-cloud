"""Authoring tool: generate one operating day for the stand-allocation task.

Usage: python3 gen.py NAME SEED N_TURNS OUT.json
"""
import json
import random
import sys

from plan_day import plan


def build(name, seed, n_turns):
    rng = random.Random(seed)
    scale = n_turns / 200
    piers = [
        ("A", max(6, round(10 * scale)), False, [1, 1, 2]),
        ("B", max(6, round(10 * scale)), False, [2, 2, 3]),
        ("C", max(5, round(8 * scale)), True, [2, 3, 3]),
    ]
    stands = []
    for pier, count, intl, sizes in piers:
        for i in range(1, count + 1):
            stands.append({"id": f"{pier}{i:02d}", "pier": pier, "position": i,
                           "size": rng.choice(sizes), "international": intl, "remote": False})
    n_remote = max(4, round(7 * scale))
    for i in range(1, n_remote + 1):
        stands.append({"id": f"R{i:02d}", "pier": "R", "position": i, "size": 3,
                       "international": True, "remote": True})

    pier_gap = {("A", "B"): 260, ("A", "C"): 420, ("B", "C"): 310}

    def walk(s, t):
        if s["remote"] or t["remote"]:
            return 800 if (s["remote"] and t["remote"]) else 650
        if s["pier"] == t["pier"]:
            return 40 + 55 * abs(s["position"] - t["position"])
        key = tuple(sorted((s["pier"], t["pier"])))
        return 40 + 55 * s["position"] + pier_gap[key] + 55 * t["position"]

    matrix = [[walk(s, t) for t in stands] for s in stands]
    wing = []
    for a, b in zip(stands, stands[1:]):
        if a["pier"] == b["pier"] and not a["remote"] and a["size"] == 3 and b["size"] == 3:
            wing.append([a["id"], b["id"]])

    banks = [360, 540, 720, 900, 1080, 1260]
    turns = []
    for k in range(n_turns):
        size = rng.choices([1, 2, 3], weights=[3, 5, 2])[0]
        arrive = (rng.choice(banks) + rng.randint(-50, 50)) if rng.random() < 0.55 else rng.randint(330, 1320)
        ground = {1: rng.randint(35, 60), 2: rng.randint(45, 95), 3: rng.randint(90, 230)}[size]
        cap = {1: 80, 2: 180, 3: 320}[size]
        turns.append({"size": size, "arrive": arrive, "depart": arrive + ground,
                      "international": rng.random() < (0.2 if size < 3 else 0.6),
                      "pax_in": int(cap * rng.uniform(0.55, 0.95)),
                      "pax_out": int(cap * rng.uniform(0.55, 0.95))})
    turns.sort(key=lambda t: (t["arrive"], t["depart"]))
    for k, t in enumerate(turns, 1):
        t["id"] = f"T{k:03d}"
    turns = [{"id": t["id"], **{k: v for k, v in t.items() if k != "id"}} for t in turns]

    transfers = []
    for f in turns:
        cands = [g for g in turns if g is not f and f["arrive"] + 50 <= g["depart"] <= f["arrive"] + 240]
        rng.shuffle(cands)
        for g in cands[: rng.randint(2, 6)]:
            transfers.append({"from": f["id"], "to": g["id"], "passengers": rng.randint(3, 25)})

    day = {"name": name, "buffer_minutes": 15, "bus_cost_per_passenger": 300,
           "stands": stands, "walk_metres": matrix, "wingtip_pairs": wing,
           "turns": turns, "transfers": transfers}
    return day


if __name__ == "__main__":
    name, seed, n, out = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
    day = build(name, seed, n)
    try:
        plan(day)
    except SystemExit as exc:
        raise SystemExit(f"shipped planner cannot place every turn: {exc}")
    with open(out, "w") as fh:
        json.dump(day, fh, indent=1)
    print(name, len(day["turns"]), "turns", len(day["stands"]), "stands", len(day["transfers"]), "transfers")
