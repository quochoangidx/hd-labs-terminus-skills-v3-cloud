"""The matching engine.

Handles limit (gtc, ioc, fok), market, iceberg, stop and stop-limit orders with
self-trade prevention. See docs/matching-rules.md for the full rules.
"""

from matchbook.book import Resting, Side


class Engine:
    def __init__(self):
        self.bids = Side(is_bid=True)
        self.asks = Side(is_bid=False)
        self.by_id = {}
        self.stops = {}  # id -> command, insertion order = acceptance order
        self.last_price = None

    # -- queries -------------------------------------------------------------

    def book(self):
        return {"bids": self.bids.snapshot(), "asks": self.asks.snapshot()}

    def held(self):
        return list(self.stops)

    # -- commands ------------------------------------------------------------

    def submit(self, command):
        if command["cmd"] == "cancel":
            return self._cancel(command["id"])
        if command["cmd"] == "new":
            return self._new(command)
        raise ValueError(f"unknown command {command['cmd']!r}")

    def _cancel(self, order_id):
        order = self.by_id.pop(order_id, None)
        if order is not None:
            self._side(order.side).remove(order)
            return [{"ev": "out", "id": order_id, "reason": "cancelled"}]
        if order_id in self.stops:
            del self.stops[order_id]
            return [{"ev": "out", "id": order_id, "reason": "cancelled"}]
        return [{"ev": "reject", "id": order_id}]

    def _new(self, command):
        events = [{"ev": "accepted", "id": command["id"]}]
        kind = command["type"]
        if kind in ("stop", "stop_limit"):
            self.stops[command["id"]] = command
        elif kind in ("limit", "market"):
            self._incoming(self._order(command), events)
        else:
            raise ValueError(f"unknown order type {kind!r}")
        self._check_stops(events)
        return events

    # -- stops ---------------------------------------------------------------

    def _condition(self, command):
        if self.last_price is None:
            return False
        if command["side"] == "buy":
            return self.last_price >= command["stop"]
        return self.last_price <= command["stop"]

    def _check_stops(self, events):
        while True:
            chosen = None
            for command in self.stops.values():
                if self._condition(command):
                    chosen = command
                    break
            if chosen is None:
                return
            del self.stops[chosen["id"]]
            events.append({"ev": "trigger", "id": chosen["id"]})
            self._incoming(self._order(chosen), events)

    # -- matching ------------------------------------------------------------

    @staticmethod
    def _order(command):
        """Normalise a command into an incoming order description."""
        kind = command["type"]
        if kind in ("market", "stop"):
            return {"id": command["id"], "owner": command["owner"], "side": command["side"],
                    "qty": command["qty"], "market": True, "price": None, "tif": "ioc",
                    "display": 0}
        return {"id": command["id"], "owner": command["owner"], "side": command["side"],
                "qty": command["qty"], "market": False, "price": command["price"],
                "tif": command["tif"], "display": command.get("display") or 0}

    def _side(self, side):
        return self.bids if side == "buy" else self.asks

    @staticmethod
    def _acceptable(order, price):
        if order["market"]:
            return True
        if order["side"] == "buy":
            return price <= order["price"]
        return price >= order["price"]

    def _fok_reachable(self, order, opposite):
        total = 0
        for resting in opposite.orders():
            if not self._acceptable(order, resting.price):
                break
            if resting.owner == order["owner"]:
                continue
            total += resting.remaining
            if total >= order["qty"]:
                break
        return total

    def _incoming(self, order, events):
        side = order["side"]
        opposite = self._side("sell" if side == "buy" else "buy")
        if order["tif"] == "fok" and self._fok_reachable(order, opposite) < order["qty"]:
            events.append({"ev": "out", "id": order["id"], "reason": "fok"})
            return
        remaining = order["qty"]
        while remaining > 0:
            resting = opposite.best()
            if resting is None or not self._acceptable(order, resting.price):
                break
            if resting.owner == order["owner"]:
                opposite.remove(resting)
                del self.by_id[resting.id]
                events.append({"ev": "out", "id": resting.id, "reason": "stp"})
                continue
            qty = min(remaining, resting.visible)
            buy, sell = (order["id"], resting.id) if side == "buy" else (resting.id, order["id"])
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
            elif resting.visible == 0:
                opposite.remove(resting)
                resting.visible = min(resting.display, resting.remaining)
                opposite.add(resting)
                events.append({"ev": "rest", "id": resting.id, "price": resting.price,
                               "visible": resting.visible})
        if remaining == 0:
            events.append({"ev": "out", "id": order["id"], "reason": "filled"})
        elif not order["market"] and order["tif"] == "gtc":
            display = order["display"]
            visible = min(display, remaining) if display > 0 else remaining
            resting = Resting(order["id"], order["owner"], side, order["price"], remaining,
                              visible, display)
            self._side(side).add(resting)
            self.by_id[resting.id] = resting
            events.append({"ev": "rest", "id": resting.id, "price": resting.price,
                           "visible": resting.visible})
        else:
            events.append({"ev": "out", "id": order["id"], "reason": "unfilled"})
