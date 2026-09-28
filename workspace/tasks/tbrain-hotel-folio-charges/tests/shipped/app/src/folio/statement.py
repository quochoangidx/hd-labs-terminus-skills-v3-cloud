"""The folios for one night audit file."""

from .charges import city_tax, occupancy_tax, room, service_fee


def folio(stay):
    charge = room(stay)
    tax = occupancy_tax(charge)
    city = city_tax(stay)
    fee = service_fee(charge)
    return {"id": stay["id"], "room": charge, "occupancy_tax": tax, "city_tax": city, "service_fee": fee,
            "total": charge + tax + city + fee}


def statement(stays):
    folios = [folio(x) for x in stays["stays"]]
    return {"audit": stays["audit"], "folios": folios, "total": sum(x["total"] for x in folios)}
