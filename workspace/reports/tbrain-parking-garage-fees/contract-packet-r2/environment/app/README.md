# parkfee

Works out the fees for the sessions that left a parking garage in one day. The
figures follow `docs/garage-tariff.md` (tariff GT-2).

## Running

    python3 /app/tools/parkfee_run.py SESSIONS.json

prints the statement for one day of exits as a single JSON object on standard
output. The package lives in `src/parkfee`; `examples/` holds a small file.

## Exits file

A JSON object:

- `garage`: the file's name, a string.
- `sessions`: a list with one object per parking session, each holding `id`
  (a ticket number, a string), `vehicle` (`"CAR"`, `"VAN"` or `"MOTO"`),
  `entry` and `exit` (minutes, integers) and `validated` (a boolean: the ticket
  was stamped by a shop in the centre).

## Statement

A JSON object:

- `garage`, as given.
- `sessions`: one object per session, in the order of the file, holding `id`,
  `hours` (the charged hours), `fee` (the parking fee in cents) and `due` (the
  amount the driver pays at the barrier, in cents), all integers except `id`.
- `total`: the sum of the amounts due in cents, an integer.
