# netbill

Works out the bills for one billing cycle of a small electricity retailer's
net-metered customers. The figures follow `docs/net-metering-tariff.md`
(tariff NM-4).

## Running

    python3 /app/tools/netbill_run.py METERS.json

prints the bills for one cycle as a single JSON object on standard output. The
package lives in `src/netbill`; `examples/` holds a small file.

## Meter reads file

A JSON object:

- `cycle`: the file's name, a string.
- `meters`: a list with one object per meter, each holding `id` (a string),
  `tariff` (`"HOME"`, `"FARM"` or `"SHOP"`), `imported` and `exported`
  (kilowatt-hours over the cycle, integers).

## Bills

A JSON object:

- `cycle`, as given.
- `bills`: one object per meter, in the order of the file, holding `id`,
  `net` (kilowatt-hours), `energy`, `service` and `total` (cents), all
  integers except `id`.
- `total`: the sum of the bill totals in cents, an integer.
