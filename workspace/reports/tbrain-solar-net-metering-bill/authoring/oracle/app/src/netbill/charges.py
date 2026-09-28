"""Energy and service charges."""

RATE = {"HOME": 28, "FARM": 22, "SHOP": 31}
SERVICE_CHARGE = 950
SERVICE_FREE_BELOW_KWH = 50
TARIFF_SERVICE_FROM_KWH = 200
HOME_FIRST_KWH = 300
HOME_LATER_RATE = 34
TARIFF_SERVICE = {"HOME": 950, "SHOP": 1450}


def net(meter):
    """Kilowatt-hours taken from the grid less those sent back."""
    return meter["imported"] - meter["exported"]


def energy(meter, net_kwh):
    if net_kwh <= 0 or meter["tariff"] != "HOME":
        return net_kwh * RATE[meter["tariff"]]
    later = max(net_kwh - HOME_FIRST_KWH, 0)
    return (net_kwh - later) * RATE["HOME"] + later * HOME_LATER_RATE


def service(meter):
    if meter["tariff"] in TARIFF_SERVICE and meter["imported"] >= TARIFF_SERVICE_FROM_KWH:
        return TARIFF_SERVICE[meter["tariff"]]
    if meter["imported"] < SERVICE_FREE_BELOW_KWH:
        return 0
    return SERVICE_CHARGE
