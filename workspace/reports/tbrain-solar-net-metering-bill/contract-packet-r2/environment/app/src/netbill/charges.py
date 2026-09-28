"""Energy and service charges."""

RATE = {"HOME": 28, "FARM": 22, "SHOP": 31}
SERVICE_CHARGE = 950
SERVICE_FREE_BELOW_KWH = 50


def net(meter):
    """Kilowatt-hours taken from the grid less those sent back."""
    return meter["imported"] - meter["exported"]


def energy(meter, net_kwh):
    return net_kwh * RATE[meter["tariff"]]


def service(meter):
    if meter["imported"] < SERVICE_FREE_BELOW_KWH:
        return 0
    return SERVICE_CHARGE
