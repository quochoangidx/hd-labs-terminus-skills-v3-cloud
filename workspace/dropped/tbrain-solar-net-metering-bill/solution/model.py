"""Independent model of tariff NM-4 (/app/docs/net-metering-tariff.md).

Worked out from the tariff alone; it never imports the package under repair. Where the tariff gives no rule for
a figure, the model mirrors the shipped package's step for it and says so ("Shipped step").
"""

OLD_RATE = {"HOME": 28, "FARM": 22, "SHOP": 31}


def bill(meter):
    tariff, kwh = meter["tariff"], meter["imported"] - meter["exported"]  # 2.1
    if kwh > 0:  # 2.2: a net consumer
        if tariff == "HOME":
            energy = 28 * min(kwh, 300) + 34 * max(kwh - 300, 0)
        else:
            energy = {"FARM": 22, "SHOP": 31}[tariff] * kwh
    else:
        # Shipped step (no energy charge is given for a meter that is not a net consumer): charges.energy() charges
        # its net at the tariff's rate, nought or a credit.
        energy = kwh * OLD_RATE[tariff]
    if tariff in ("HOME", "SHOP") and meter["imported"] >= 200:  # 3.1
        service = 950 if tariff == "HOME" else 1450
    else:
        # Shipped step (no service charge is given for a FARM meter, or for a meter that imported under 200 kWh):
        # charges.service() charges nothing under 50 kWh imported and 950 cents otherwise.
        service = 0 if meter["imported"] < 50 else 950
    return {"id": meter["id"], "net": kwh, "energy": energy, "service": service, "total": energy + service}


def statement(reads):
    bills = [bill(m) for m in reads["meters"]]
    return {"cycle": reads["cycle"], "bills": bills, "total": sum(b["total"] for b in bills)}


def silent(meter):
    """The figures the tariff leaves to today's code that this meter carries (used by seal.py)."""
    out = set()
    if meter["imported"] - meter["exported"] < 0:
        out.add("credit")  # an exporter: its energy charge is a credit (nought for a net of nought is left graded)
    if meter["tariff"] == "FARM" or meter["imported"] < 200:
        out.add("small")  # its service charge is today's step
    return out
