"""Independent model of rules FC-3 (/app/docs/folio-charges-rules.md).

Worked out from the rules alone; it never imports the package under repair. Where the rules give no rule for a
figure, the model mirrors the shipped package's step for it and says so ("Shipped step").
"""

from fractions import Fraction


def folio(stay):
    nights, rate = stay["nights"], stay["rate"]
    charge = (nights - nights // 7) * rate  # 2.1
    if rate >= 5000:  # 2.2
        city = 250 * min(nights, 14)
    else:
        # Shipped step (no city tax is given for a room under 5,000 cents a night): charges.city_tax() charges nothing
        # under 3,000 cents a night and 200 cents for every night otherwise, with no limit on the nights.
        city = 0 if rate < 3000 else 200 * nights
    tax = (charge * 135 + 500) // 1000  # 2.3: 13.5 per cent, a half cent up
    # Shipped step (no rate or rounding is given for the service fee, 2.4): charges.service_fee() takes 3.5 per cent
    # of the room charge and rounds it with Python's round(), an exact half cent going to the even cent.
    fee = round(Fraction(charge * 35, 1000))
    return {"id": stay["id"], "room": charge, "occupancy_tax": tax, "city_tax": city, "service_fee": fee,
            "total": charge + tax + city + fee}


def statement(stays):
    folios = [folio(x) for x in stays["stays"]]
    return {"audit": stays["audit"], "folios": folios, "total": sum(x["total"] for x in folios)}


def cheap(stay):
    """True when the stay's nightly rate is under 5,000 cents (used by seal.py)."""
    return stay["rate"] < 5000


def half_fee(stay):
    """True when this stay's service fee lands exactly on a half cent (used by seal.py)."""
    nights, rate = stay["nights"], stay["rate"]
    return ((nights - nights // 7) * rate * 35) % 1000 == 500
