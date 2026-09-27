"""The demurrage statement for one release file."""

from .charges import charge, days
from .dwell import dwell, free_days


def line(box):
    stood = dwell(box)
    free = free_days(box)
    chargeable = days(stood, free)
    return {"id": box["id"], "dwell": stood, "free": free, "days": chargeable, "charge": charge(box, chargeable)}


def statement(releases):
    lines = [line(b) for b in releases["containers"]]
    return {"terminal": releases["terminal"], "containers": lines, "total": sum(x["charge"] for x in lines)}
