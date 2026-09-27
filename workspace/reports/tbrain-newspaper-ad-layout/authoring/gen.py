"""Authoring tool: generate one edition for the ad make-up task.

Usage: python3 gen.py NAME SEED PAGES OUT.json
"""
import json
import random
import sys

from plan_edition import plan

SIZES = [(6, 42, 1), (6, 21, 2), (3, 42, 1), (3, 21, 4), (4, 28, 2), (2, 28, 3), (4, 14, 3),
         (3, 14, 4), (2, 14, 5), (2, 10, 5), (1, 21, 3), (1, 14, 4), (2, 6, 5), (1, 8, 5), (6, 6, 2), (6, 10, 2)]


def build(name, seed, pages):
    rng = random.Random(seed)
    cols, rows = 6, 42
    q = pages // 4
    sections = {"news": [1, 2 * q], "local": [2 * q + 1, 3 * q], "business": [3 * q + 1, 3 * q + q // 2],
                "sport": [3 * q + q // 2 + 1, pages]}
    premium = {"news": 14, "local": 10, "business": 12, "sport": 12}
    capacity = 6 * cols + (pages - 1) * (60 * rows * cols // 100)
    groups = ["cars", "grocers", "banks", "phones", "estate", "furniture", "travel"]
    ads = []
    area = 0
    k = 0
    while area < capacity * 1.18:
        w, d, _ = rng.choices(SIZES, weights=[s[2] for s in SIZES])[0]
        k += 1
        sec = rng.choice(list(sections)) if rng.random() < 0.7 else None
        prem = premium[sec] if sec else 10
        rate = int(w * d * prem * rng.uniform(0.8, 1.3))
        ads.append({"id": f"AD{k:03d}", "advertiser": f"client-{rng.randint(1, 400):03d}", "width": w, "depth": d,
                    "rate": rate, "booked": rng.random() < 0.35, "section": sec,
                    "right_hand": rng.random() < 0.2,
                    "competitor_group": rng.choice(groups) if rng.random() < 0.3 else None})
        area += w * d
    return {"name": name, "pages": pages, "columns": cols, "rows": rows, "front_page_ad_rows": 6,
            "max_ad_share_percent": 60, "wrong_section_percent": 30, "left_hand_percent": 15,
            "sections": sections, "ads": ads}


if __name__ == "__main__":
    name, seed, pages, out = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
    ed = build(name, seed, pages)
    plan(ed)
    with open(out, "w") as fh:
        json.dump(ed, fh, indent=1)
    print(name, pages, "pages", len(ed["ads"]), "ads")
