"""Generate the four bottling-site instances (deterministic)."""
import json, random, os, sys
out = sys.argv[1]
SITES = [("dorset", 3, 12, 20, 1), ("kent", 3, 16, 20, 2), ("fife", 4, 20, 20, 3), ("tyne", 4, 26, 20, 4)]
FAM = ["cola", "lemon", "orange", "water", "tonic", "ginger", "apple", "berry"]
for name, nl, np_, T, seed in SITES:
    rng = random.Random(1000 + seed)
    lines = []
    for i in range(nl):
        cap = rng.choice([900, 960, 1020])
        caps = [cap] * T
        for _ in range(rng.randint(1, 2)):          # maintenance days
            d = rng.randrange(T); caps[d] = rng.choice([0, cap // 2])
        for d in range(T):
            if d % 7 == 6: caps[d] = 0               # Sundays off
        lines.append({"id": f"L{i+1}", "capacity_minutes": caps})
    products = []
    for j in range(np_):
        fam = FAM[j % len(FAM)]
        base = rng.randint(2, 9)
        dem = []
        for d in range(T):
            if d % 7 == 6: dem.append(0); continue
            v = max(0, int(rng.gauss(base, base * 0.5)))
            if rng.random() < 0.12: v += rng.randint(4, 12)       # promotions
            dem.append(v)
        elig = rng.sample([l["id"] for l in lines], rng.randint(1, min(3, nl)))
        per = {}
        for lid in sorted(elig):
            per[lid] = {"minutes_per_batch": rng.choice([12, 15, 18, 20, 24, 30]),
                        "setup_minutes": rng.choice([30, 45, 60, 90, 120]),
                        "setup_cost": rng.choice([150, 200, 300, 400, 600])}
        products.append({"id": f"{fam[:3].upper()}{j+1:02d}", "family": fam, "initial_stock": rng.randint(0, base * 2),
                         "holding_cost": rng.choice([2, 3, 4, 5, 6]), "backlog_cost": rng.choice([40, 60, 80, 100]),
                         "demand": dem, "lines": per})
    # scale demand so the plant runs near capacity
    capsum = sum(sum(l["capacity_minutes"]) for l in lines)
    need = sum(sum(p["demand"]) * min(v["minutes_per_batch"] for v in p["lines"].values()) for p in products)
    f = 0.80 * capsum / need
    for p in products:
        p["demand"] = [int(round(x * f)) for x in p["demand"]]
    inst = {"name": name, "days": T, "lines": lines, "products": products}
    open(os.path.join(out, name + ".json"), "w").write(json.dumps(inst, indent=1) + "\n")
    print(name, nl, np_, sum(len(json.dumps(inst)) for _ in [0]), round(f, 2))
