"""Energy and service charges."""

RATE = {"HOME": 28, "FARM": 22, "SHOP": 31}
SERVICE_CHARGE = 950


def net(meter):
    """Kilowatt-hours taken from the grid less those sent back."""
    return meter["imported"] - meter["exported"]


def energy(meter, net_kwh):
    return net_kwh * RATE[meter["tariff"]]


def service(meter):
    return SERVICE_CHARGE
