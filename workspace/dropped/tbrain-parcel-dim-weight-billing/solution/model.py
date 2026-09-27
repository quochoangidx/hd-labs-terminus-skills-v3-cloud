"""Independent model of rules PB-4 (/app/docs/parcel-billing-rules.md).

Worked out from the rules alone; it never imports the package under repair. Where the rules give no rule for
a figure, the model mirrors the shipped package's step for it and says so ("Shipped step").
"""

from fractions import Fraction
import math

RATE = {2: 95, 3: 105, 4: 118, 5: 131, 6: 146, 7: 164, 8: 190}  # 3.1


def divisor(parcel):
    if min(parcel["sides"]) >= 2:  # 2.1 a box; 2.2
        return 139
    # Shipped step (no divisor is given for a parcel that is not a box): weight.dimensional() divides by 166.
    return 166


def billable(parcel):
    """2.2, 2.3: the larger of actual and dimensional weight, rounded up to a whole pound."""
    length, width, height = parcel["sides"]
    heavier = max(Fraction(parcel["weight"], 10), Fraction(length * width * height, divisor(parcel)))
    return math.ceil(heavier)


def residential(parcel):
    if not parcel["residential"]:
        return 0  # shipped and 3.2 agree: nothing for a business delivery
    if parcel["service"] == "GROUND":  # 3.2
        return 530
    # Shipped step (no rule for an express parcel going to a home): charges.residential() charges 450.
    return 450


def line(parcel):
    pounds = billable(parcel)
    moving = pounds * RATE[parcel["zone"]]
    home = residential(parcel)
    if parcel["service"] == "GROUND":  # 3.3
        fuel = math.floor(Fraction((moving + home) * 1425, 10000) + Fraction(1, 2))
    else:
        # Shipped step (no rule for the fuel surcharge of an express parcel): charges.fuel() takes 14.25 per cent
        # of the transport charge alone and drops the fraction of a cent.
        fuel = moving * 1425 // 10000
    return {"id": parcel["id"], "billable": pounds, "transport": moving, "residential": home, "fuel": fuel,
            "total": moving + home + fuel}


def invoice(manifest):
    lines = [line(p) for p in manifest["parcels"]]
    return {"manifest": manifest["manifest"], "parcels": lines, "total": sum(x["total"] for x in lines)}
