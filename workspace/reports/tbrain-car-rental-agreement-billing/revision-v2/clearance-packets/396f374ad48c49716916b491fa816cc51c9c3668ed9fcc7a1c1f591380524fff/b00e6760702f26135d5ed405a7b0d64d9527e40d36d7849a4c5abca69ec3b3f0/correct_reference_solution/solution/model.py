"""Independent model of manual RC-3 (/app/docs/rental-charges-manual.md).

Worked out from the manual alone; it never imports the package under repair. Where the manual gives no
rule for a figure, the model mirrors the shipped package's step for it and says so ("Shipped step"),
feeding that step the figures the manual does define.
"""

from datetime import datetime
from fractions import Fraction
import math

DAY = 1440
GRACE = 59  # 2.3
ALLOWANCE = 150  # 3.2
REFUEL_FEE = 1500  # 3.3
TAX = Fraction(825, 10000)  # 4.1
TURNOVER = 1_000_000  # 2.5


def length(a):
    """2.1: minutes from out to in."""
    fmt = "%Y-%m-%dT%H:%M"
    return int((datetime.strptime(a["in"], fmt) - datetime.strptime(a["out"], fmt)).total_seconds() // 60)


def days(a):
    n = length(a)
    if n >= DAY:  # 2.2 day rental; 2.3 charged days
        return n // DAY + (1 if n % DAY > GRACE else 0)
    # Shipped step (no rule for a rental under a day): time_charge.days() charges every day begun.
    return -(-n // DAY)


def miles(a):
    """2.4, the odometer turning over."""
    d = a["odometer_in"] - a["odometer_out"]
    return d + TURNOVER if a["odometer_in"] < a["odometer_out"] else d


def allowance(a):
    """3.2: 150 miles for each day the rental is charged for."""
    return ALLOWANCE * days(a)


def fuel_charge(a):
    if a["fuel_in"] < a["fuel_out"]:  # 2.5 refuelling rental, 3.3
        return (a["fuel_out"] - a["fuel_in"]) * a["fuel_rate"] + REFUEL_FEE
    # Shipped step (no rule for a car back with its tank as full or fuller): fuel.fuel_charge() charges
    # the fuel rate on the difference, which is nought or a credit.
    return (a["fuel_out"] - a["fuel_in"]) * a["fuel_rate"]


def bill(a):
    time_charge = days(a) * a["day_rate"]
    mileage_charge = max(0, miles(a) - allowance(a)) * a["mile_rate"]
    fuel = fuel_charge(a)
    tax = math.floor((time_charge + mileage_charge) * TAX + Fraction(1, 2))  # 4.1, 1.2
    return {"id": a["id"], "days": days(a), "miles": miles(a), "time_charge": time_charge, "mileage_charge": mileage_charge,
            "fuel_charge": fuel, "tax": tax, "total": time_charge + mileage_charge + fuel + tax}


def report(agreements):
    bills = [bill(a) for a in agreements["agreements"]]
    return {"branch": agreements["branch"], "bills": bills, "revenue": sum(b["total"] for b in bills), "tax": sum(b["tax"] for b in bills)}
