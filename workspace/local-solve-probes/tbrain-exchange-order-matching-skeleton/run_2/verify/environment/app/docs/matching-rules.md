# Continuous matching rules for `matchbook`

This note is the authority for how the `matchbook` engine handles orders during
continuous trading on one instrument. `Engine.submit(command)` takes one command
and returns the list of events it caused, in the order they happened.
`Engine.book()` and `Engine.held()` describe the engine's state between commands.

## 1. Numbers and commands

1.1 Prices are whole ticks and quantities are whole units. Every quantity in a
command is above zero.

1.2 A `new` command is a dictionary with `cmd` = `"new"`, a unique `id`, an
`owner`, a `side` (`"buy"` or `"sell"`), a `type` and a `qty`:

- `"limit"`: also `price`, `tif` (`"gtc"`, `"ioc"` or `"fok"`) and an optional
  `display`.
- `"market"`: nothing more. A market order is always immediate-or-cancel.
- `"stop"`: also `stop`. When it triggers it becomes a market order.
- `"stop_limit"`: also `stop`, `price`, `tif` and an optional `display`. When
  it triggers it becomes a limit order with that price, `tif` and `display`.

1.3 A `display` above zero makes an iceberg order; a missing `display`, or a
`display` of zero, makes an ordinary order. Only a `gtc` order ever rests, so
`display` matters only for `gtc` orders.

1.4 A `cancel` command is `{"cmd": "cancel", "id": ...}`. Ids are never reused.

## 2. Events

Every event is a dictionary with an `ev` key:

- `{"ev": "accepted", "id"}`: the first event of every `new` command.
- `{"ev": "trade", "price", "qty", "buy", "sell", "aggressor"}`: `buy` and
  `sell` are the ids of the two orders, `aggressor` is the incoming order's side.
- `{"ev": "rest", "id", "price", "visible"}`: an order, or a new slice of an
  iceberg, takes its place on the book showing `visible` units.
- `{"ev": "trigger", "id"}`: a held stop order triggers.
- `{"ev": "out", "id", "reason"}`: an order leaves the engine. `reason` is
  `"filled"` (no quantity left), `"unfilled"` (the remainder of an order that
  may not rest), `"fok"` (a fill-or-kill order that could not be filled whole),
  `"stp"` (removed to prevent a self-trade) or `"cancelled"` (by a `cancel`).
- `{"ev": "reject", "id"}`: a `cancel` for an id that is neither resting nor
  held.

## 3. The book and priority

3.1 Resting orders sit on the book at their limit price. Bids are ranked from
the highest price down and asks from the lowest price up; at one price, orders
are ranked by priority, earliest first.

3.2 An order takes its priority at the moment it rests. An iceberg takes a new
priority each time it shows a new slice.

3.3 A resting ordinary order shows its whole remaining quantity. A resting
iceberg shows a slice of `min(display, remaining)`; the rest of its remaining
quantity is hidden.

3.4 `Engine.book()` returns `{"bids": [...], "asks": [...]}`. Each side lists
its price levels in rank order as `[price, [[id, visible, hidden], ...]]`, the
orders at a level in priority order, `hidden` being 0 for an ordinary order.
`Engine.held()` returns the ids of the held stop orders, earliest accepted first.

## 4. Matching an incoming order

4.1 An incoming order is a new limit or market order, or a stop order that has
just triggered. It matches against the opposite side of the book, best-ranked
resting order first, for as long as it has quantity left and the best resting
order's price is acceptable: any price for a market order, at or below the limit
for a buy limit, at or above the limit for a sell limit.

4.2 Each match is a trade at the resting order's price, for the smaller of the
incoming order's remaining quantity and the resting order's visible quantity.
An incoming order matches with its whole remaining quantity, even when it is an
iceberg.

4.3 After a trade, a resting order with nothing left leaves: `out` with
`"filled"`. A resting iceberg whose visible slice is used up but which has hidden
quantity shows its next slice at once: `rest` with the new `visible`, taking a
new priority behind the orders already at its price. Matching then continues.

4.4 When the incoming order has nothing left it leaves with `out` `"filled"`.
Otherwise, when no acceptable resting order remains: a `gtc` limit order rests
(`rest`, showing its slice if it is an iceberg), and any other order leaves with
`out` `"unfilled"`.

## 5. Self-trade prevention

Before a trade between two orders with the same `owner`, the resting order is
removed instead, whole, hidden quantity included: `out` with `"stp"`. Matching
then continues with the next resting order.

## 6. Fill or kill

6.1 Before a `fok` order matches, the engine adds up the quantity it could reach:
the whole remaining quantity, visible and hidden, of every resting order on the
opposite side at an acceptable price, leaving out orders with the same owner.

6.2 If that total is below the order's quantity, the order leaves with `out`
`"fok"` and nothing else happens: no trade, and no order is removed. Otherwise
it matches under sections 4 and 5.

## 7. Stop orders

7.1 A new stop or stop-limit order is held, not placed on the book. A buy stop's
condition holds when the last trade price is at or above its `stop`; a sell
stop's condition holds when the last trade price is at or below its `stop`.
There is no last trade price until the first trade, and no condition holds
before it.

7.2 After every `new` command has finished its own events (including a new
stop order that has just been held), the engine checks the held orders. While
any held order's condition holds for the current last trade price, the one
accepted earliest among them triggers: `trigger`, then it is matched as an
incoming order (section 4) until it rests or leaves. The check is then repeated
with the last trade price as it now stands.

7.3 A `cancel` removes a resting order or a held stop order: `out` with
`"cancelled"`. A `cancel` causes no stop check.
