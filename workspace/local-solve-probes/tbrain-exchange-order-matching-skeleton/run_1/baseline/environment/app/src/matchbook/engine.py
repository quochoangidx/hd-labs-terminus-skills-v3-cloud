"""The matching engine.

Handles plain limit orders (gtc and ioc) and market orders. See
docs/matching-rules.md for the full rules.
"""

from matchbook.book import Resting, Side


class Engine:
    def __init__(self):
        self.bids = Side(is_bid=True)
        self.asks = Side(is_bid=False)
        self.by_id = {}
        self.last_price = None

    # -- queries -------------------------------------------------------------

    def book(self):
        return {"bids": self.bids.snapshot(), "asks": self.asks.snapshot()}

    def held(self):
        return []

    # -- commands ------------------------------------------------------------

    def submit(self, command):
        if command["cmd"] == "cancel":
            return self._cancel(command["id"])
        if command["cmd"] == "new":
            return self._new(command)
        raise ValueError(f"unknown command {command['cmd']!r}")

    def _cancel(self, order_id):
        order = self.by_id.pop(order_id, None)
        if order is None:
            return [{"ev": "reject", "id": order_id}]
        self._side(order.side).remove(order)
        return [{"ev": "out", "id": order_id, "reason": "cancelled"}]

    def _new(self, command):
        events = [{"ev": "accepted", "id": command["id"]}]
        if command["type"] not in ("limit", "market"):
            raise NotImplementedError(f"{command['type']} orders")
        if command.get("tif") == "fok":
            raise NotImplementedError("fill-or-kill")
        self._incoming(command, events)
        return events

    # -- matching ------------------------------------------------------------

    def _side(self, side):
        return self.bids if side == "buy" else self.asks

    def _acceptable(self, command, price):
        if command["type"] == "market":
            return True
        if command["side"] == "buy":
            return price <= command["price"]
        return price >= command["price"]

    def _incoming(self, command, events):
        side = command["side"]
        opposite = self._side("sell" if side == "buy" else "buy")
        remaining = command["qty"]
        while remaining > 0:
            resting = opposite.best()
            if resting is None or not self._acceptable(command, resting.price):
                break
            qty = min(remaining, resting.visible)
            buy, sell = (command["id"], resting.id) if side == "buy" else (resting.id, command["id"])
            events.append({"ev": "trade", "price": resting.price, "qty": qty,
                           "buy": buy, "sell": sell, "aggressor": side})
            self.last_price = resting.price
            remaining -= qty
            resting.remaining -= qty
            resting.visible -= qty
            if resting.remaining == 0:
                opposite.remove(resting)
                del self.by_id[resting.id]
                events.append({"ev": "out", "id": resting.id, "reason": "filled"})
        if remaining == 0:
            events.append({"ev": "out", "id": command["id"], "reason": "filled"})
        elif command["type"] == "limit" and command["tif"] == "gtc":
            order = Resting(command["id"], command["owner"], side, command["price"], remaining, remaining)
            self._side(side).add(order)
            self.by_id[order.id] = order
            events.append({"ev": "rest", "id": order.id, "price": order.price, "visible": order.visible})
        else:
            events.append({"ev": "out", "id": command["id"], "reason": "unfilled"})
