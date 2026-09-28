# Stand allocation rules

These rules decide whether a day's stand plan can be flown and what it costs.
They are the rules `tools/check_plan.py` applies.

## The day

Each file in `days/` is one operating day. Times are whole minutes from
midnight.

A stand has an `id`, a `pier` (`A`, `B` and `C` are contact piers, `R` is the
remote apron), a `position` along its pier, a `size` (the largest aircraft size
it takes: 1, 2 or 3), `international` (true when passengers can pass passport
control there) and `remote` (true for remote stands, where passengers are taken
to and from the aircraft by bus).

A turn is one aircraft visit: it has an `id`, an aircraft `size` (1, 2 or 3,
where 3 is a widebody), the minute it arrives on the stand (`arrive`) and the
minute it leaves (`depart`), `international`, and the number of passengers who
get off (`pax_in`) and get on (`pax_out`).

A transfer `{"from": X, "to": Y, "passengers": n}` says that `n` passengers who
arrive on turn `X` leave on turn `Y`.

`walk_metres[i][j]` is the walking distance, in metres, from the stand at
position `i` of the `stands` list to the stand at position `j`. The day also
gives `buffer_minutes` and `bus_cost_per_passenger`, and a list of
`wingtip_pairs`: pairs of neighbouring stands whose wingtips would touch if
both held a widebody.

## What a plan must do

Every turn of the day is on exactly one stand, and:

1. The turn's `size` is at most the stand's `size`.
2. An international turn is on a stand with `international` true. A turn that
   is not international may use any stand.
3. Two turns on the same stand keep apart by the buffer: one of them departs,
   plus `buffer_minutes`, no later than the other arrives. A turn occupies its
   stand from `arrive` to `depart`.
4. For each pair in `wingtip_pairs`, the two stands never hold size-3 turns at
   the same time: two such turns clash when each arrives before the other
   departs. No buffer applies here, and turns smaller than size 3 never clash
   this way.

## Cost

A plan costs the sum of:

- for every turn on a remote stand, `bus_cost_per_passenger` times its
  `pax_in` plus `pax_out`;
- for every transfer, its `passengers` times `walk_metres` from the stand of
  its `from` turn to the stand of its `to` turn.

The matrix entry is used as it stands in every case: a transfer between two
turns on the same stand is charged the diagonal entry (which is not zero), and a
transfer to or from a remote stand is charged its walking entry on top of any
bus charges for the two turns. Nothing else is charged. Costs are whole
numbers, and lower is better.

## File format

    {"stands": {"A01": ["T004", "T017", ...], "R02": [...], ...}}

Each key is a stand id; each list gives the ids of the turns
on that stand as JSON strings, exactly as in the day file, in any order. A stand
may be left out or given an empty list. Any other top-level key is ignored.
