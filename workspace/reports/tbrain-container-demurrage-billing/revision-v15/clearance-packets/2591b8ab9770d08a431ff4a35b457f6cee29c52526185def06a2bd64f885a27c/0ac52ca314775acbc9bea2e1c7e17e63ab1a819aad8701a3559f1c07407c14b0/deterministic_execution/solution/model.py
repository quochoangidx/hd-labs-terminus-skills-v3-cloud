"""Independent model of tariff DM-3 (/app/docs/demurrage-tariff.md).

Worked out from the tariff alone; it never imports the package under repair. Where the tariff gives no rule for
a figure, the model mirrors the shipped package's step for it and says so ("Shipped step").
"""

FREE = {"DRY": 5, "REEFER": 3}  # 2.2


def line(box):
    stood = box["picked_up"] - box["discharged"] + 1  # 2.1
    # Shipped step (no free time is given for a tank): dwell.free_days() gives 5.
    free = FREE.get(box["type"], 5)
    over = stood - free
    if over > 0:  # 2.3, 3.1: on demurrage
        pay = min(over, 4) * box["rate"] + max(over - 4, 0) * 2 * box["rate"]
    else:
        # Shipped step (no demurrage days or charge are given for a container not on demurrage): charges.days()
        # gives dwell less free days and charges.charge() that many days at the daily rate, nought or a credit.
        pay = over * box["rate"]
    return {"id": box["id"], "dwell": stood, "free": free, "days": over, "charge": pay}


def statement(releases):
    lines = [line(b) for b in releases["containers"]]
    return {"terminal": releases["terminal"], "containers": lines, "total": sum(x["charge"] for x in lines)}


def silent(box):
    """The figures the tariff leaves to today's code that this container carries (used by seal.py)."""
    out = set()
    if box["type"] not in FREE:
        out.add("tank")
    if box["picked_up"] - box["discharged"] + 1 <= FREE.get(box["type"], 5):
        out.add("idle")
    return out
