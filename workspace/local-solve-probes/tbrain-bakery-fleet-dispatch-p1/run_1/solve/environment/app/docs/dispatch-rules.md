# Morning dispatch rules

These rules decide whether a delivery plan can be run and what it costs. They
are the rules `tools/check_plan.py` applies.

## Orders

Each file in `orders/` is one morning. It lists the bakery (`depot`), the
customers to deliver to, and the vehicles available (`fleet`). Positions are
integer grid coordinates in units of 100 m; times are seconds after midnight.

A customer has an `id`, a position, a `demand` in crates, a delivery window
`ready`..`due`, and a `service` time in seconds for unloading.

A fleet entry is one kind of vehicle: `count` vehicles of it are available,
each carrying up to `capacity` crates. It travels at `pace` seconds per unit of
distance, costs `fixed` for being used at all and `per_unit` for every unit of
distance it drives, may be out for at most `shift` seconds from leaving the
bakery to getting back, and, where `range` is not null, may drive at most
`range` units of distance in the morning. Costs are in cents.

## Distance and time

The distance between two points is the Euclidean distance between them,
rounded up to a whole unit. A vehicle takes `distance * pace` seconds to drive
it.

## A route

A route is one vehicle's morning: it leaves the bakery at its departure time,
visits its customers in order, and comes back. Each vehicle runs at most one
route.

- The departure is a whole number of seconds, not before the bakery opens.
- At each customer the vehicle unloads from the later of its arrival and the
  customer's `ready` time, and that must not be after `due`. Unloading takes the
  customer's `service` time; the vehicle leaves as soon as it is done.
- The vehicle must be back at the bakery no later than it closes, and no more
  than `shift` seconds after its departure.
- The crates on the route (the sum of its customers' demands) must fit the
  vehicle's `capacity`, and the distance driven, bakery to bakery, must be
  within its `range` where it has one.

## A plan

A plan delivers to every customer of the morning exactly once, uses no more
vehicles of a kind than the fleet has, and costs the sum over its routes of the
vehicle's `fixed` cost plus `per_unit` times the route's distance.

It is written as JSON:

    {"routes": [{"type": "van", "depart": 18000, "stops": [12, 4, 31]}, ...]}

where `type` names a fleet entry, `depart` is the departure time and `stops`
lists customer ids in visiting order.
