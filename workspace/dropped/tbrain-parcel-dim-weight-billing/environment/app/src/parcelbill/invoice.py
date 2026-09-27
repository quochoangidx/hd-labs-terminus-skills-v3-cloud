"""The invoice for one manifest."""

from .charges import fuel, residential, transport
from .weight import billable


def line(parcel):
    pounds = billable(parcel)
    moving = transport(parcel, pounds)
    home = residential(parcel)
    surcharge = fuel(moving, home)
    return {"id": parcel["id"], "billable": pounds, "transport": moving, "residential": home,
            "fuel": surcharge, "total": moving + home + surcharge}


def invoice(manifest):
    lines = [line(p) for p in manifest["parcels"]]
    return {"manifest": manifest["manifest"], "parcels": lines, "total": sum(x["total"] for x in lines)}
