"""Expected engine behaviour, worked out from /app/docs/matching-rules.md.

A second, deliberately different reading of the note: the book is a flat table
of resting orders with explicit priority numbers, and every "best order" is a
fresh minimum over it. It never imports or runs the engine under test.
"""

from __future__ import annotations


class ModelEngine:
    def __init__(self) -> None:
        self.clock = 0
        self.resting: dict[str, dict] = {}
        self.stops: list[dict] = []
        self.last = None

    # 3.2: priority is taken when an order, or a new iceberg slice, rests.
    def _tick(self) -> int:
        self.clock += 1
        return self.clock

    # 3.1, 3.4
    def book(self) -> dict:
        def side(name: str) -> list:
            orders = [o for o in self.resting.values() if o["side"] == name]
            prices = sorted({o["price"] for o in orders}, reverse=(name == "buy"))
            levels = []
            for price in prices:
                here = sorted((o for o in orders if o["price"] == price), key=lambda o: o["prio"])
                levels.append([price, [[o["id"], o["visible"], o["remaining"] - o["visible"]] for o in here]])
            return levels

        return {"bids": side("buy"), "asks": side("sell")}

    def held(self) -> list:
        return [c["id"] for c in self.stops]

    def submit(self, command: dict) -> list:
        events: list[dict] = []
        if command["cmd"] == "cancel":
            order_id = command["id"]
            if order_id in self.resting:
                del self.resting[order_id]
                events.append({"ev": "out", "id": order_id, "reason": "cancelled"})  # 7.3
            elif any(c["id"] == order_id for c in self.stops):
                self.stops = [c for c in self.stops if c["id"] != order_id]
                events.append({"ev": "out", "id": order_id, "reason": "cancelled"})  # 7.3
            else:
                events.append({"ev": "reject", "id": order_id})  # 2
            return events  # 7.3: no stop check after a cancel
        events.append({"ev": "accepted", "id": command["id"]})  # 2
        if command["type"] in ("stop", "stop_limit"):
            self.stops.append(dict(command))  # 7.1
        else:
            self._incoming(dict(command), events)
        self._stop_check(events)  # 7.2
        return events

    def _condition(self, stop: dict) -> bool:
        if self.last is None:
            return False  # 7.1
        if stop["side"] == "buy":
            return self.last >= stop["stop"]
        return self.last <= stop["stop"]

    def _stop_check(self, events: list) -> None:
        while True:
            ready = [s for s in self.stops if self._condition(s)]
            if not ready:
                return
            stop = ready[0]  # self.stops is in acceptance order
            self.stops.remove(stop)
            events.append({"ev": "trigger", "id": stop["id"]})
            incoming = dict(stop)
            incoming["type"] = "market" if stop["type"] == "stop" else "limit"  # 1.2
            self._incoming(incoming, events)

    @staticmethod
    def _acceptable(incoming: dict, price: int) -> bool:
        if incoming["type"] == "market":
            return True
        if incoming["side"] == "buy":
            return price <= incoming["price"]
        return price >= incoming["price"]  # 4.1

    def _best(self, side: str):
        orders = [o for o in self.resting.values() if o["side"] == side]
        if not orders:
            return None
        if side == "sell":
            return min(orders, key=lambda o: (o["price"], o["prio"]))
        return min(orders, key=lambda o: (-o["price"], o["prio"]))

    def _incoming(self, incoming: dict, events: list) -> None:
        side = incoming["side"]
        opposite = "sell" if side == "buy" else "buy"
        left = incoming["qty"]
        tif = incoming["tif"] if incoming["type"] == "limit" else "ioc"  # 1.2: market is ioc
        if tif == "fok":
            reach = sum(
                o["remaining"]
                for o in self.resting.values()
                if o["side"] == opposite
                and o["owner"] != incoming["owner"]
                and self._acceptable(incoming, o["price"])
            )  # 6.1
            if reach < left:
                events.append({"ev": "out", "id": incoming["id"], "reason": "fok"})  # 6.2
                return
        while left > 0:
            resting = self._best(opposite)
            if resting is None or not self._acceptable(incoming, resting["price"]):
                break
            if resting["owner"] == incoming["owner"]:
                del self.resting[resting["id"]]
                events.append({"ev": "out", "id": resting["id"], "reason": "stp"})  # 5
                continue
            qty = min(left, resting["visible"])  # 4.2
            buyer, seller = (incoming["id"], resting["id"]) if side == "buy" else (resting["id"], incoming["id"])
            events.append({"ev": "trade", "price": resting["price"], "qty": qty,
                           "buy": buyer, "sell": seller, "aggressor": side})
            self.last = resting["price"]
            left -= qty
            resting["remaining"] -= qty
            resting["visible"] -= qty
            if resting["remaining"] == 0:
                del self.resting[resting["id"]]
                events.append({"ev": "out", "id": resting["id"], "reason": "filled"})  # 4.3
            elif resting["visible"] == 0:
                resting["visible"] = min(resting["display"], resting["remaining"])  # 3.3, 4.3
                resting["prio"] = self._tick()
                events.append({"ev": "rest", "id": resting["id"], "price": resting["price"],
                               "visible": resting["visible"]})
        if left == 0:
            events.append({"ev": "out", "id": incoming["id"], "reason": "filled"})  # 4.4
        elif incoming["type"] == "limit" and tif == "gtc":
            display = incoming.get("display") or 0  # 1.3
            visible = min(display, left) if display > 0 else left  # 3.3
            self.resting[incoming["id"]] = {
                "id": incoming["id"], "owner": incoming["owner"], "side": side,
                "price": incoming["price"], "remaining": left, "visible": visible,
                "display": display, "prio": self._tick(),
            }
            events.append({"ev": "rest", "id": incoming["id"], "price": incoming["price"], "visible": visible})
        else:
            events.append({"ev": "out", "id": incoming["id"], "reason": "unfilled"})  # 4.4


def run_session(commands: list[dict]) -> list[dict]:
    """After each command: its events, the book and the held ids."""
    engine = ModelEngine()
    return [{"events": engine.submit(c), "book": engine.book(), "held": engine.held()} for c in commands]
