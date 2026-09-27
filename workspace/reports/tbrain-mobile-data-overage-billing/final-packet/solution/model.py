"""Independent model of tariff MD-2 (/app/docs/data-usage-tariff.md).

Worked out from the tariff alone; it never imports the package under repair. Where the tariff gives no rule for
a figure, the model mirrors the shipped package's step for it and says so ("Shipped step").
"""

ALLOWANCE = {"BASIC": 2048, "PLUS": 10240}  # 2.2


def line(entry):
    used = sum(-(-kb // 1024) for kb in entry["sessions"])  # 2.1
    # Shipped step (no allowance is given for a FLEX line): usage.allowance() gives 5,120.
    included = ALLOWANCE.get(entry["plan"], 5120)
    over = used - included
    if over > 0:  # 2.3, 3.1
        pay = min(over, 1024) * entry["rate"] + max(over - 1024, 0)
    else:
        # Shipped step (no overage or charge is given for a line not over its allowance): charges.overage() gives
        # usage less allowance and charges.charge() that many megabytes at the rate, nought or a credit.
        pay = over * entry["rate"]
    return {"id": entry["id"], "used": used, "allowance": included, "over": over, "charge": pay}


def statement(usage):
    lines = [line(x) for x in usage["lines"]]
    return {"account": usage["account"], "lines": lines, "total": sum(x["charge"] for x in lines)}


def silent(entry):
    """The figures the tariff leaves to today's code that this line carries (used by seal.py)."""
    out = set()
    if entry["plan"] not in ALLOWANCE:
        out.add("flex")
    if sum(-(-kb // 1024) for kb in entry["sessions"]) <= ALLOWANCE.get(entry["plan"], 5120):
        out.add("idle")
    return out
