"""The bills for one cycle of meter reads."""

from .charges import energy, net, service


def bill(meter):
    kwh = net(meter)
    energy_charge = energy(meter, kwh)
    service_charge = service(meter)
    return {"id": meter["id"], "net": kwh, "energy": energy_charge, "service": service_charge,
            "total": energy_charge + service_charge}


def statement(reads):
    bills = [bill(m) for m in reads["meters"]]
    return {"cycle": reads["cycle"], "bills": bills, "total": sum(b["total"] for b in bills)}
