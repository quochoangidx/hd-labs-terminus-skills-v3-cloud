# parcelbill

Works out the charges for one day's parcel manifest. The figures follow
`docs/parcel-billing-rules.md` (rules PB-4).

## Running

    python3 /app/tools/parcelbill_run.py MANIFEST.json

prints the invoice lines for one manifest as a single JSON object on standard
output. The package lives in `src/parcelbill`; `examples/` holds a small
manifest.

## Manifest

A JSON object:

- `manifest`: the manifest's name, a string.
- `parcels`: a list with one object per parcel, each holding `id` (a string),
  `sides` (a list of three integers, inches, in no particular order),
  `weight` (the actual weight in tenths of a pound, an integer), `service`
  (`"GROUND"` or `"EXPRESS"`), `zone` (an integer) and `residential` (a
  boolean).

## Invoice

A JSON object:

- `manifest`, as given.
- `parcels`: one object per parcel, in the order of the manifest, holding
  `id`, `billable` (the billable weight in whole pounds), `transport`,
  `residential`, `fuel` and `total` (cents), all integers.
- `total`: the manifest's total in cents, an integer.
