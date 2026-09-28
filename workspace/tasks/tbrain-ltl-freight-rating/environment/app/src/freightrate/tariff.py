"""A class tariff with weight breaks."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Tariff:
    """Break minimums (pounds, increasing), rates per class and break (cents
    per hundred pounds), and the minimum charge (cents)."""

    breaks: tuple
    rates: dict
    minimum_charge: int

    def break_index(self, weight):
        """Position of the break a weight rates at."""
        for index in range(len(self.breaks) - 1, -1, -1):
            if weight > self.breaks[index]:
                return index
        return len(self.breaks) - 1

    def rate(self, freight_class, index):
        return self.rates[freight_class][index]
