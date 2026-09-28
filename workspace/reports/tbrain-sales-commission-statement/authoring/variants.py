"""variants.py: build one-edit variants of the Oracle-patched package under authoring/variants/<name>/app
(each departure reverted alone, each trap's natural wrong repairs, and a contract-valid alternative)."""

import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
ORACLE = HERE / "oracle" / "app"
OUT = HERE / "variants"

EDITS = {
    # --- each departure reverted alone ---
    "rev-D1": [("commission.py",
                "    low, mid, top = bands(bookings, quota)\n    return (share_of(low, figure(\"band_rate\")) + share_of(mid, figure(\"above_quota_rate\"))\n            + share_of(top, figure(\"top_rate\")))\n",
                "    rate = figure(\"top_rate\") if bookings > 2 * quota else figure(\"above_quota_rate\") if bookings > quota else figure(\"band_rate\")\n    return share_of(bookings, rate)\n")],
    "rev-D2": [("bookings.py", "        total += rep_share(value, split)\n", "        total += value\n")],
    "rev-D3": [("commission.py",
                "    return (share_of(low, figure(\"band_rate\")) + share_of(mid, figure(\"above_quota_rate\"))\n            + share_of(top, figure(\"top_rate\")))\n",
                "    return (low * figure(\"band_rate\") // 10000 + mid * figure(\"above_quota_rate\") // 10000\n            + top * figure(\"top_rate\") // 10000)\n")],
    "rev-D4": [("clawback.py", "        limit = figure(\"reversal_age\") if amount >= REVERSAL_CENTS else figure(\"clawback_age\")\n",
                "        limit = figure(\"clawback_age\")\n")],
    "rev-D5": [("bonus.py", "        if value < NEW_LOGO_CENTS and credit < figure(\"bonus_floor\"):\n",
                "        if credit < figure(\"bonus_floor\"):\n")],
    "rev-D6": [("figures.py", "    \"minimum_payment\": \"payment_cents\",", "    \"minimum_payment\": \"small_cents\",")],
    "rev-D7": [("payout.py", "    recovered = min(owed, total - draw)\n", "    recovered = min(owed, total)\n")],
    # --- trap TA: credit notes below 50,000 cents (courtesy credits) ---
    # natural fix of 5.1: edit the shared window entry in place, no reversal branch
    "TA-inplace-window": [("figures.py", "    \"window_days\": 90,", "    \"window_days\": 120,"),
                          ("clawback.py", "        limit = figure(\"reversal_age\") if amount >= REVERSAL_CENTS else figure(\"clawback_age\")\n",
                           "        limit = figure(\"clawback_age\")\n")],
    # exclusion reading: only a reversal claws anything back
    "TA-exclusion": [("clawback.py", "        limit = figure(\"reversal_age\") if amount >= REVERSAL_CENTS else figure(\"clawback_age\")\n",
                      "        if amount < REVERSAL_CENTS:\n            lines.append(0)\n            continue\n        limit = figure(\"reversal_age\")\n")],
    # apply-everywhere: no age limit for credit notes that are not reversals
    "TA-window-removed": [("clawback.py", "        limit = figure(\"reversal_age\") if amount >= REVERSAL_CENTS else figure(\"clawback_age\")\n",
                           "        limit = figure(\"reversal_age\") if amount >= REVERSAL_CENTS else 10**9\n")],
    # --- trap TB: first orders below 250,000 cents (trial orders) ---
    # natural fix of 7.4: edit the shared small_cents entry in place
    "TB-inplace-small-cents": [("figures.py", "    \"small_cents\": 10000,", "    \"small_cents\": 25000,"),
                               ("figures.py", "    \"minimum_payment\": \"payment_cents\",", "    \"minimum_payment\": \"small_cents\",")],
    # exclusion reading: only a new-logo order earns a bonus
    "TB-exclusion": [("bonus.py", "        if value < NEW_LOGO_CENTS and credit < figure(\"bonus_floor\"):\n",
                      "        if value < NEW_LOGO_CENTS:\n")],
    # apply-everywhere: the floor removed for every first order
    "TB-floor-removed": [("bonus.py", "        if value < NEW_LOGO_CENTS and credit < figure(\"bonus_floor\"):\n",
                          "        if False:\n")],
    # --- contract-valid alternative: separate constants in the modules, no table change ---
    "alt-module-constants": [
        ("figures.py", "    \"minimum_payment\": \"payment_cents\",", "    \"minimum_payment\": \"small_cents\","),
        ("payout.py", "    if draw == 0 and due < figure(\"minimum_payment\"):\n", "    if draw == 0 and due < 25000:\n"),
        ("clawback.py", "        limit = figure(\"reversal_age\") if amount >= REVERSAL_CENTS else figure(\"clawback_age\")\n",
         "        limit = 120 if amount >= 50000 else figure(\"clawback_age\")\n"),
        ("bonus.py", "        if value < NEW_LOGO_CENTS and credit < figure(\"bonus_floor\"):\n            lines.append(0)\n        else:\n            lines.append(share_of(credit, figure(\"bonus_rate\")))\n",
         "        if value >= 250000:\n            lines.append(share_of(credit, 300))\n        elif credit < figure(\"bonus_floor\"):\n            lines.append(0)\n        else:\n            lines.append(share_of(credit, figure(\"bonus_rate\")))\n"),
    ],
}


def build():
    if OUT.exists():
        shutil.rmtree(OUT)
    for name, edits in EDITS.items():
        dest = OUT / name / "app"
        shutil.copytree(ORACLE, dest, ignore=shutil.ignore_patterns("__pycache__"))
        for fname, old, new in edits:
            p = dest / "src" / "commission" / fname
            s = p.read_text()
            assert s.count(old) == 1, (name, fname, old)
            p.write_text(s.replace(old, new))
    return list(EDITS)


if __name__ == "__main__":
    print("\n".join(build()))
