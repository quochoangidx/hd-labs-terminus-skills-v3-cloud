"""The matching engine.

Handles limit (gtc, ioc, fok, iceberg), market, stop and stop-limit orders
with self-trade prevention. See docs/matching-rules.md for the full rules.
"""

from matchbook.book import Resting, Side


class Engine:
    def __init__(self):
        self.bids = Side(is_bid=True)
        self.asks = Side(is_bid=False)
        self.by_id = {}
        self.held_orders = []  # held stop commands, earliest accepted first
        self.last_price = None

    # -- queries -------------------------------------------------------------

    def book(self):
        return {"bids": self.bids.snapshot(), "asks": self.asks.snapshot()}

    def held(self):
        return [c["id"] for c in self.held_orders]

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
        for i, held in enumerate(self.held_orders):
            if held["id"] == order_id:
                del self.held_orders[i]
                return [{"ev": "out", "id": order_id, "reason": "cancelled"}]
        return [{"ev": "reject", "id": order_id}]

    def _new(self, command):
        events = [{"ev": "accepted", "id": command["id"]}]
        kind = command["type"]
        if kind in ("stop", "stop_limit"):
            self.held_orders.append(dict(command))
        elif kind in ("limit", "market"):
            self._incoming(command, events)
        else:
            raise ValueError(f"unknown order type {kind!r}")
        self._check_stops(events)
        return events

    # -- stops ---------------------------------------------------------------

    def _condition(self, held):
        if self.last_price is None:
            return False
        if held["side"] == "buy":
            return self.last_price >= held["stop"]
        return self.last_price <= held["stop"]

    def _check_stops(self, events):
        while True:
            chosen = None
            for i, held in enumerate(self.held_orders):
                if self._condition(held):
                    chosen = i
                    break
            if chosen is None:
                return
            held = self.held_orders.pop(chosen)
            events.append({"ev": "trigger", "id": held["id"]})
            order = dict(held)
            order["type"] = "market" if held["type"] == "stop" else "limit"
            self._incoming(order, events)

    # -- matching ------------------------------------------------------------

    def _side(self, side):
        return self.bids if side == "buy" else self.asks

    def _acceptable(self, command, price):
        if command["type"] == "market":
            return True
        if command["side"] == "buy":
            return price <= command["price"]
        return price >= command["price"]

    def _fok_reachable(self, command, opposite):
        total = 0
        for price in opposite.prices():
            if not self._acceptable(command, price):
                break
            for o in opposite.levels[price]:
                if o.owner != command["owner"]:
                    total += o.remaining
        return total

    def _incoming(self, command, events):
        side = command["side"]
        opposite = self._side("sell" if side == "buy" else "buy")
        remaining = command["qty"]
        tif = command.get("tif") if command["type"] == "limit" else None
        if tif == "fok" and self._fok_reachable(command, opposite) < remaining:
            events.append({"ev": "out", "id": command["id"], "reason": "fok"})
            return
        while remaining > 0:
            resting = opposite.best()
            if resting is None or not self._acceptable(command, resting.price):
                break
            if resting.owner == command["owner"]:
                opposite.remove(resting)
                del self.by_id[resting.id]
                events.append({"ev": "out", "id": resting.id, "reason": "stp"})
                continue
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
            elif resting.visible == 0:
                opposite.remove(resting)
                resting.visible = min(resting.display, resting.remaining)
                opposite.add(resting)
                events.append({"ev": "rest", "id": resting.id, "price": resting.price,
                               "visible": resting.visible})
        if remaining == 0:
            events.append({"ev": "out", "id": command["id"], "reason": "filled"})
        elif command["type"] == "limit" and tif == "gtc":
            display = command.get("display") or 0
            visible = min(display, remaining) if display > 0 else remaining
            order = Resting(command["id"], command["owner"], side, command["price"],
                            remaining, visible, display)
            self._side(side).add(order)
            self.by_id[order.id] = order
            events.append({"ev": "rest", "id": order.id, "price": order.price, "visible": order.visible})
        else:
            events.append({"ev": "out", "id": command["id"], "reason": "unfilled"})
