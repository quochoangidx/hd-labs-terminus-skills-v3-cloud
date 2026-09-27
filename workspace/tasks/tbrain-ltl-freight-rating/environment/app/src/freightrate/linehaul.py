"""Line charges, weight breaks and deficit weight."""

from dataclasses import dataclass

from freightrate.density import class_for, density
from freightrate.money import cents


@dataclass(frozen=True)
class Line:
    weight: int
    volume: float

    @property
    def freight_class(self):
        return class_for(density(self.weight, self.volume))


def line_charge(line, tariff, index):
    """One line's charge at break ``index``."""
    return cents(line.weight * tariff.rate(line.freight_class, index), 100)


def gross_at(lines, tariff, index):
    """Total of the line charges at break ``index``."""
    return sum(line_charge(line, tariff, index) for line in lines)


def linehaul(lines, tariff):
    """``(gross, deficit_weight, break_index)`` for a shipment."""
    weight = sum(line.weight for line in lines)
    index = tariff.break_index(weight)
    gross = sum(line_charge(line, tariff, tariff.break_index(line.weight)) for line in lines)
    deficit = 0
    if index + 1 < len(tariff.breaks):
        following = index + 1
        deficit_weight = tariff.breaks[following] - weight
        top = max(tariff.rate(line.freight_class, following) for line in lines)
        alternative = gross_at(lines, tariff, following) + cents(deficit_weight * top, 100)
        if alternative <= gross:
            gross = alternative
            deficit = deficit_weight
            index = following
    return gross, deficit, index
