"""One side of the order book: price levels, each a queue in priority order."""

from collections import deque


class Resting:
    """An order on the book."""

    __slots__ = ("id", "owner", "side", "price", "remaining", "visible")

    def __init__(self, order_id, owner, side, price, remaining, visible):
        self.id = order_id
        self.owner = owner
        self.side = side
        self.price = price
        self.remaining = remaining
        self.visible = visible


class Side:
    """Price levels for bids (best = highest) or asks (best = lowest)."""

    def __init__(self, is_bid):
        self.is_bid = is_bid
        self.levels = {}

    def prices(self):
        return sorted(self.levels, reverse=self.is_bid)

    def best(self):
        """The best-ranked resting order, or None."""
        for price in self.prices():
            return self.levels[price][0]
        return None

    def add(self, order):
        self.levels.setdefault(order.price, deque()).append(order)

    def remove(self, order):
        level = self.levels[order.price]
        level.remove(order)
        if not level:
            del self.levels[order.price]

    def orders(self):
        for price in self.prices():
            yield from self.levels[price]

    def snapshot(self):
        return [
            [price, [[o.id, o.visible, o.remaining - o.visible] for o in self.levels[price]]]
            for price in self.prices()
        ]
