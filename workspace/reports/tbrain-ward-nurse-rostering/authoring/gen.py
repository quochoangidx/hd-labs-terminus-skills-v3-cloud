"""Authoring tool: generate one ward for the rostering task.

Usage: python3 gen.py NAME SEED N_NURSES OUT.json
"""
import json
import random
import sys

from plan_ward import plan


def build(name, seed, n):
    rng = random.Random(seed)
    days = 28
    nurses = []
    n_senior = max(7, round(n * 0.25))
    n_rn = round(n * 0.43)
    grades = ["senior"] * n_senior + ["RN"] * n_rn + ["HCA"] * (n - n_senior - n_rn)
    rng.shuffle(grades)
    for k, g in enumerate(grades, 1):
        full = rng.random() < 0.7
        mn, mx = (144, 160) if full else rng.choice([(80, 96), (104, 120)])
        nights = rng.choice([0, 4, 6, 8, 8]) if g != "senior" else rng.choice([4, 6, 8])
        leave = []
        if rng.random() < 0.35:
            start = rng.randint(0, days - 5)
            leave = list(range(start, min(days, start + rng.randint(3, 7))))
        requests = []
        for _ in range(rng.randint(1, 4)):
            d = rng.randrange(days)
            if d in leave or any(r["day"] == d for r in requests):
                continue
            requests.append({"day": d, "off": rng.choice(["day", "day", "E", "L", "N"])})
        requests.sort(key=lambda r: r["day"])
        nurses.append({"id": f"{name[0].upper()}{k:02d}", "grade": g, "min_hours": mn, "max_hours": mx,
                       "max_nights": nights, "leave": leave, "requests": requests})
    f = n / 20
    cover = {
        "E": {"minimum": max(3, round(4 * f)), "registered": max(2, round(2 * f)), "preferred": max(4, round(5 * f))},
        "L": {"minimum": max(3, round(4 * f)), "registered": max(2, round(2 * f)), "preferred": max(4, round(5 * f))},
        "N": {"minimum": max(2, round(2 * f)), "registered": max(1, round(1 * f)), "preferred": max(2, round(3 * f))},
    }
    return {"name": name, "days": days, "shift_hours": {"E": 8, "L": 8, "N": 10},
            "rules": {"max_consecutive_days": 6, "rest_days_after_nights": 2, "max_weekends": 2},
            "weights": {"short_of_preferred": 30, "hour_under": 4, "hour_over": 6, "night_over": 20,
                        "split_weekend": 30, "weekend_over": 40, "lone_day": 15, "request": 25},
            "cover": cover, "nurses": nurses}


if __name__ == "__main__":
    name, seed, n, out = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
    ward = build(name, seed, n)
    plan(ward)
    with open(out, "w") as fh:
        json.dump(ward, fh, indent=1)
    print(name, n, "nurses")
