"""Independent model of tariff GT-2 (/app/docs/garage-tariff.md).

Worked out from the tariff alone; it never imports the package under repair. Where the tariff gives no rule for a
figure, the model mirrors the shipped package's step for it and says so ("Shipped step").
"""

RATE = {"CAR": 300, "VAN": 450, "MOTO": 150}  # 3.1


def line(session):
    stay = session["exit"] - session["entry"]  # 2.1
    hours = -(-stay // 60)
    if stay <= 15 and session["vehicle"] in ("CAR", "VAN"):  # 2.2, 3.2
        fee = 0
    else:
        fee = hours * RATE[session["vehicle"]]
        if session["vehicle"] in ("CAR", "VAN"):  # 3.3
            fee = min(fee, 2400 * -(-stay // 1440))
        # Shipped step (no grace period and no maximum are given for a motorcycle): its fee stays charged hours at
        # the rate, a stay of 15 minutes or less included.
    # Shipped step (the tariff gives no rule for the amount due): fees.amounts() takes 200 cents off the parking fee
    # of a validated ticket, whatever the fee, and leaves any other ticket's amount due at its fee.
    due = fee - 200 if session["validated"] else fee
    return {"id": session["id"], "hours": hours, "fee": fee, "due": due}


def statement(sessions):
    lines = [line(x) for x in sessions["sessions"]]
    return {"garage": sessions["garage"], "sessions": lines, "total": sum(x["due"] for x in lines)}


def silent(session):
    """The figures the tariff leaves to today's code that this session carries (used by seal.py)."""
    out = set()
    stay = session["exit"] - session["entry"]
    fee = 0 if stay <= 15 and session["vehicle"] != "MOTO" else -(-stay // 60) * RATE[session["vehicle"]]
    if session["validated"] and fee < 200:
        out.add("credit")  # a validated ticket whose amount due goes below nought
    if session["vehicle"] == "MOTO" and (fee > 2400 * -(-stay // 1440) or 0 < stay <= 15):
        out.add("moto")  # a motorcycle past the car-and-van maximum, or inside the car-and-van grace period
    return out
