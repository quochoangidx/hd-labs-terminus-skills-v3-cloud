"""The bill run for one agreement file."""

from .fuel import fuel_charge
from .mileage import mileage_charge, miles
from .tax import tax
from .time_charge import days, time_charge


def bill(agreement):
    charges = {
        "time_charge": time_charge(agreement),
        "mileage_charge": mileage_charge(agreement),
        "fuel_charge": fuel_charge(agreement),
    }
    owed = tax(charges["time_charge"] + charges["mileage_charge"])
    return {
        "id": agreement["id"],
        "days": days(agreement),
        "miles": miles(agreement),
        **charges,
        "tax": owed,
        "total": sum(charges.values()) + owed,
    }


def bill_run(agreements):
    bills = [bill(a) for a in agreements["agreements"]]
    return {
        "branch": agreements["branch"],
        "bills": bills,
        "revenue": sum(b["total"] for b in bills),
        "tax": sum(b["tax"] for b in bills),
    }
