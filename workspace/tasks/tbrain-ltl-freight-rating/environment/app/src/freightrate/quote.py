"""The full rating of one shipment."""

from dataclasses import dataclass

from freightrate.fuel import fuel_percentage
from freightrate.linehaul import linehaul
from freightrate.money import cents


@dataclass(frozen=True)
class Quote:
    gross: int
    discount: int
    net: int
    fuel: int
    accessorials: int
    total: int
    deficit_weight: int
    break_index: int


def rate_shipment(lines, tariff, discount, fuel_table, diesel_price, accessorials):
    """Price ``lines`` against ``tariff``; ``discount`` in basis points."""
    gross, deficit, index = linehaul(lines, tariff)
    taken = cents(gross * discount, 10_000)
    net = max(gross, tariff.minimum_charge) - taken
    extras = sum(accessorials)
    fuel = cents((gross + extras) * fuel_percentage(fuel_table, diesel_price), 10_000)
    return Quote(gross, taken, net, fuel, extras, net + fuel + extras, deficit, index)
